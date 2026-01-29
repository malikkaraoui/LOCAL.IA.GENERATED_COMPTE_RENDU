#!/usr/bin/env python3
"""
Script de démonstration du parsing RH-Pro
"""
import sys
import json
import argparse
from pathlib import Path
from typing import Optional

# Ajouter le projet au path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.rhpro.parse_bilan import parse_bilan_from_paths


def find_first_source_docx() -> Optional[Path]:
    """
    Cherche automatiquement le premier fichier source.docx dans data/samples/**/
    
    Returns:
        Path du premier source.docx trouvé, ou None
    """
    samples_dir = PROJECT_ROOT / 'data' / 'samples'
    if not samples_dir.exists():
        return None
    
    # Chercher tous les source.docx
    from src.utils.file_filters import is_ignored_filename
    source_files = [f for f in samples_dir.glob('**/source.docx') if not is_ignored_filename(f)]
    
    if source_files:
        # Trier pour avoir un ordre déterministe (client_01, client_02, etc.)
        source_files.sort()
        return source_files[0]
    
    return None


def main():
    """Démonstration du parsing"""
    
    # Parser les arguments CLI
    parser = argparse.ArgumentParser(
        description='Parser un document RH-Pro DOCX et générer un rapport',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Exemples:
  python demo_rhpro_parse.py
  python demo_rhpro_parse.py data/samples/client_01/source.docx
  python demo_rhpro_parse.py data/samples/client_01/source.docx --gate-profile stage
  python demo_rhpro_parse.py data/samples/client_01/source.docx --gate-profile placement_suivi
        '''
    )
    parser.add_argument(
        'docx_path',
        nargs='?',
        help='Chemin vers le fichier DOCX (optionnel, auto-découverte si non fourni)'
    )
    parser.add_argument(
        '--gate-profile',
        choices=['bilan_complet', 'placement_suivi', 'stage'],
        default=None,
        help='Force un profil de production gate spécifique (défaut: auto-détection)'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("RH-Pro DOCX Parser - Démo")
    print("=" * 60)
    
    # Chemins
    ruleset_path = PROJECT_ROOT / 'config' / 'rulesets' / 'rhpro_v1.yaml'
    
    # Vérifier si un DOCX est fourni en argument
    if args.docx_path:
        docx_path = Path(args.docx_path)
    else:
        # Auto-découverte : chercher data/samples/**/source.docx
        docx_path = find_first_source_docx()
        
        if docx_path:
            print(f"🔍 Auto-découverte: {docx_path.relative_to(PROJECT_ROOT)}")
        else:
            # Fallback sur l'ancien nom pour compatibilité
            fallback_path = PROJECT_ROOT / 'data' / 'samples' / 'bilan_rhpro_sample.docx'
            if fallback_path.exists():
                docx_path = fallback_path
                print(f"📌 Fallback: {docx_path.relative_to(PROJECT_ROOT)}")
            else:
                print("\n⚠️  Aucun fichier DOCX trouvé.")
                print("Usage: python demo_rhpro_parse.py <chemin_vers_bilan.docx>")
                print("\nOu placez un fichier dans: data/samples/client_XX/source.docx")
                sys.exit(1)
    
    if not docx_path.exists():
        print(f"❌ Fichier introuvable: {docx_path}")
        sys.exit(1)
    
    print(f"\n📄 Document: {docx_path.name}")
    print(f"📋 Ruleset: {ruleset_path.name}")
    
    # Afficher le profil (auto ou forcé)
    if args.gate_profile:
        print(f"🎯 Gate profile: {args.gate_profile} (forced)")
    else:
        print(f"🎯 Gate profile: auto-detection")
    
    print("\n⏳ Parsing en cours...\n")
    
    try:
        # Parsing
        result = parse_bilan_from_paths(
            str(docx_path),
            str(ruleset_path),
            gate_profile_override=args.gate_profile
        )
        
        # Afficher le rapport
        report = result['report']
        
        print("✅ Parsing terminé!")
        print("\n" + "=" * 60)
        print("RAPPORT")
        print("=" * 60)
        
        print(f"\n📊 Couverture: {report['coverage_ratio'] * 100:.1f}%")
        
        print(f"\n✓ Sections trouvées ({len(report['found_sections'])}):")
        for section in report['found_sections'][:10]:  # Limiter l'affichage
            conf = section['confidence']
            sid = section['section_id']
            title = section['title'][:50]
            print(f"  - [{conf:.2f}] {sid}: {title}")
        
        if len(report['found_sections']) > 10:
            print(f"  ... et {len(report['found_sections']) - 10} autres")
        
        if report['missing_required_sections']:
            print(f"\n⚠️  Sections requises manquantes ({len(report['missing_required_sections'])}):")
            for sid in report['missing_required_sections']:
                print(f"  - {sid}")
        
        if report['unknown_titles']:
            print(f"\n❓ Titres non mappés ({len(report['unknown_titles'])}):")
            for title in report['unknown_titles'][:5]:
                print(f"  - {title[:60]}")
            if len(report['unknown_titles']) > 5:
                print(f"  ... et {len(report['unknown_titles']) - 5} autres")
        
        if report['warnings']:
            print(f"\n⚠️  Warnings:")
            for warning in report['warnings']:
                print(f"  - {warning}")
        
        # Production Gate
        if 'production_gate' in report:
            gate = report['production_gate']
            status_icon = "✅" if gate['status'] == 'GO' else "🚫"
            print(f"\n{status_icon} Production Gate: {gate['status']}")
            print(f"   Profile: {gate.get('profile', 'N/A')}")
            
            # Afficher les signaux
            if gate.get('signals'):
                signals = gate['signals']
                if signals.get('forced'):
                    print(f"   Selection: forced via CLI override")
                else:
                    print(f"   Signals detected:")
                    if signals.get('has_stage'):
                        print(f"      • stage detected")
                    if signals.get('bilan_complet_sections_count', 0) >= 2:
                        print(f"      • bilan complet sections: {signals['bilan_complet_sections_count']} (tests/vocation/profil_emploi/ressources)")
                    if signals.get('has_lai15') or signals.get('has_lai18'):
                        lai_type = "LAI 15" if signals.get('has_lai15') else "LAI 18"
                        print(f"      • {lai_type} detected")
                    if signals.get('matched_titles'):
                        print(f"      • matched titles: {', '.join(signals['matched_titles'][:3])}")
        # Afficher les signaux de détection
        if gate.get('signals'):
            signals = gate['signals']
            print(f"\n   Signaux de détection:")
            print(f"      - has_stage: {signals.get('has_stage', False)}")
            print(f"      - has_tests: {signals.get('has_tests', False)}")
            print(f"      - has_vocation: {signals.get('has_vocation', False)}")
            print(f"      - has_profil_emploi: {signals.get('has_profil_emploi', False)}")
            print(f"      - has_lai15: {signals.get('has_lai15', False)}")
            print(f"      - has_lai18: {signals.get('has_lai18', False)}")
            print(f"      - bilan_complet_sections: {signals.get('bilan_complet_sections_count', 0)}")
            
            # Afficher les titres matchés (troncation)
            if signals.get('matched_titles'):
                print(f"      - matched_titles: {signals['matched_titles'][:3]}")
            
            # Afficher le scoring (nouveau)
            if 'scores' in signals:
                print(f"\n   Scores par profil:")
                for profile, score in signals['scores'].items():
                    print(f"      - {profile}: {score}")
                
                # Afficher la confidence
                if 'selection_confidence' in signals:
                    confidence = signals['selection_confidence']
                    print(f"\n   Confidence de sélection: {confidence} (delta entre top1 et top2)")
                
                # Afficher le ranking
                if 'profile_ranking' in signals:
                    print(f"   Ranking: {' > '.join(signals['profile_ranking'])}")
            
            # Afficher les critères
            if gate.get('criteria'):
                print(f"   Criteria:")
                for criterion, passed in gate['criteria'].items():
                    icon = "✓" if passed else "✗"
                    print(f"      {icon} {criterion}")
            
            # Afficher les métriques
            if gate.get('metrics'):
                print(f"   Metrics:")
                metrics = gate['metrics']
                print(f"      - required_coverage (global): {metrics.get('required_coverage_ratio', 0):.0%}")
                if 'required_coverage_ratio_effective' in metrics:
                    print(f"      - required_coverage (effective): {metrics['required_coverage_ratio_effective']:.0%}")
                print(f"      - unknown_titles: {metrics.get('unknown_titles_count', 0)}")
                print(f"      - placeholders: {metrics.get('placeholders_count', 0)}")
                print(f"      - missing_required (global): {metrics.get('missing_required_sections_count', 0)}")
                if 'missing_required_sections_count_effective' in metrics:
                    print(f"      - missing_required (effective): {metrics['missing_required_sections_count_effective']}")
            
            # Afficher les sections manquantes effectives
            if gate.get('missing_required_effective'):
                print(f"   Missing required (after profile filter): {', '.join(gate['missing_required_effective'][:5])}")
            
            # Afficher les raisons de NO-GO
            if gate.get('reasons'):
                print(f"   Reasons:")
                for reason in gate['reasons']:
                    print(f"      - {reason}")
        
        # Placeholders
        if 'placeholders' in report and report['placeholders']:
            print(f"\n🔍 Placeholders détectés ({len(report['placeholders'])}):")
            for ph in report['placeholders'][:3]:
                print(f"  - [{ph['pattern']}] @ {ph['path']}")
            if len(report['placeholders']) > 3:
                print(f"  ... et {len(report['placeholders']) - 3} autres")
        
        # Provenance (debug info)
        if 'provenance' in result:
            provenance_count = len(result['provenance'])
            print(f"\n📊 Provenance: {provenance_count} sections trackées (audit/debug)")
        
        # Option: sauvegarder le résultat
        output_path = docx_path.parent / f"{docx_path.stem}_normalized.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Résultat sauvegardé: {output_path}")
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"❌ Erreur lors du parsing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

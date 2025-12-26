#!/usr/bin/env python3
"""
Script de démonstration du parsing RH-Pro
"""
import sys
import json
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
    source_files = list(samples_dir.glob('**/source.docx'))
    
    if source_files:
        # Trier pour avoir un ordre déterministe (client_01, client_02, etc.)
        source_files.sort()
        return source_files[0]
    
    return None


def main():
    """Démonstration du parsing"""
    
    print("=" * 60)
    print("RH-Pro DOCX Parser - Démo")
    print("=" * 60)
    
    # Chemins
    ruleset_path = PROJECT_ROOT / 'config' / 'rulesets' / 'rhpro_v1.yaml'
    
    # Vérifier si un DOCX est fourni en argument
    if len(sys.argv) > 1:
        docx_path = Path(sys.argv[1])
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
    print("\n⏳ Parsing en cours...\n")
    
    try:
        # Parsing
        result = parse_bilan_from_paths(
            str(docx_path),
            str(ruleset_path)
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
            if gate.get('reasons'):
                for reason in gate['reasons']:
                    print(f"  - {reason}")
        
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

#!/usr/bin/env python3
"""
Utilitaire pour afficher la provenance d'un document parsé
Usage: python show_provenance.py data/samples/client_02/source_normalized.json [section_id]
"""
import sys
import json
from pathlib import Path


def show_all_provenance(provenance: dict):
    """Affiche toute la provenance"""
    print("\n" + "=" * 80)
    print("📋 PROVENANCE COMPLÈTE - AUDIT/DEBUG")
    print("=" * 80)
    
    print(f"\n✓ {len(provenance)} sections trackées\n")
    
    for section_id, info in provenance.items():
        print(f"{'─' * 80}")
        print(f"🔍 Section: {section_id}")
        print(f"   Titre source    : \"{info['source_title']}\"")
        print(f"   Titre normalisé : \"{info['normalized_title']}\"")
        print(f"   Confidence      : {info['confidence']} (level {info['level']})")
        print(f"   Paragraphes     : {info['paragraph_count']}")
        print(f"   Snippet         : \"{info['snippet'][:100]}\"")
        if len(info['snippet']) > 100:
            print(f"                     \"{info['snippet'][100:200]}...\"")


def show_section_provenance(provenance: dict, section_id: str):
    """Affiche la provenance d'une section spécifique"""
    if section_id not in provenance:
        print(f"\n❌ Section '{section_id}' non trouvée dans la provenance")
        print(f"\nSections disponibles:")
        for sid in provenance.keys():
            print(f"  - {sid}")
        return
    
    info = provenance[section_id]
    
    print("\n" + "=" * 80)
    print(f"🔍 PROVENANCE: {section_id}")
    print("=" * 80)
    
    print(f"\n📌 Informations de mapping:")
    print(f"   Titre source    : \"{info['source_title']}\"")
    print(f"   Titre normalisé : \"{info['normalized_title']}\"")
    print(f"   Confidence      : {info['confidence']}")
    print(f"   Level           : {info['level']}")
    
    print(f"\n📄 Contenu:")
    print(f"   Paragraphes     : {info['paragraph_count']}")
    print(f"\n   Snippet (200 chars):")
    print(f"   {info['snippet']}")
    
    print("\n💡 Utilité:")
    print("   - Vérifier pourquoi un champ est vide")
    print("   - Valider le mapping du titre")
    print("   - Itérer rapidement sur les anchors")
    print("   - Audit de qualité")
    
    print("\n" + "=" * 80)


def main():
    if len(sys.argv) < 2:
        print("Usage: python show_provenance.py <normalized.json> [section_id]")
        print("\nExemple:")
        print("  python show_provenance.py data/samples/client_02/source_normalized.json")
        print("  python show_provenance.py data/samples/client_02/source_normalized.json identity")
        sys.exit(1)
    
    json_path = Path(sys.argv[1])
    
    if not json_path.exists():
        print(f"❌ Fichier introuvable: {json_path}")
        sys.exit(1)
    
    # Charger le JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    provenance = data.get('provenance', {})
    
    if not provenance:
        print(f"❌ Pas de provenance dans le fichier")
        sys.exit(1)
    
    # Afficher section spécifique ou tout
    if len(sys.argv) >= 3:
        section_id = sys.argv[2]
        show_section_provenance(provenance, section_id)
    else:
        show_all_provenance(provenance)


if __name__ == '__main__':
    main()

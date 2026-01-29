#!/usr/bin/env python3
"""
Script de validation : Détecte les points de suspension "..." dans un document Word généré.

Usage:
    python validate_no_ellipsis.py <path_to_docx>

Exemples:
    python validate_no_ellipsis.py output/rapport_KARAOUI_Malik.docx
    python validate_no_ellipsis.py output/batch/*/rapport_*.docx
"""

import sys
from pathlib import Path
from docx import Document


def check_ellipsis_in_docx(docx_path: Path) -> dict:
    """
    Vérifie si un document DOCX contient des points de suspension "..." ou "…".
    
    Returns:
        Dict avec :
        - "has_ellipsis": bool (True si "..." trouvés)
        - "ellipsis_count": int (nombre d'occurrences)
        - "ellipsis_locations": list[dict] (paragraphes contenant des "...")
    """
    doc = Document(docx_path)
    ellipsis_locations = []
    ellipsis_count = 0
    
    for idx, para in enumerate(doc.paragraphs):
        text = para.text
        
        # Chercher "..." (3 points ASCII)
        if "..." in text:
            count_ascii = text.count("...")
            ellipsis_count += count_ascii
            ellipsis_locations.append({
                "paragraph_index": idx,
                "text_preview": text[:100] + ("..." if len(text) > 100 else ""),
                "ellipsis_type": "ASCII (...)",
                "count": count_ascii,
            })
        
        # Chercher "…" (caractère Unicode U+2026)
        if "…" in text:
            count_unicode = text.count("…")
            ellipsis_count += count_unicode
            ellipsis_locations.append({
                "paragraph_index": idx,
                "text_preview": text[:100] + ("..." if len(text) > 100 else ""),
                "ellipsis_type": "Unicode (…)",
                "count": count_unicode,
            })
    
    return {
        "has_ellipsis": ellipsis_count > 0,
        "ellipsis_count": ellipsis_count,
        "ellipsis_locations": ellipsis_locations,
    }


def main():
    if len(sys.argv) < 2:
        print("❌ Usage: python validate_no_ellipsis.py <path_to_docx>")
        sys.exit(1)
    
    docx_path = Path(sys.argv[1])
    
    if not docx_path.exists():
        print(f"❌ Fichier introuvable : {docx_path}")
        sys.exit(1)
    
    if not docx_path.suffix.lower() == ".docx":
        print(f"❌ Le fichier n'est pas un .docx : {docx_path}")
        sys.exit(1)
    
    print(f"🔍 Vérification de : {docx_path.name}")
    print()
    
    result = check_ellipsis_in_docx(docx_path)
    
    if result["has_ellipsis"]:
        print(f"❌ PROBLÈME DÉTECTÉ : {result['ellipsis_count']} occurrence(s) de '...' ou '…' trouvées !\n")
        
        for loc in result["ellipsis_locations"]:
            print(f"  📍 Paragraphe {loc['paragraph_index']}")
            print(f"     Type: {loc['ellipsis_type']} (x{loc['count']})")
            print(f"     Aperçu: {loc['text_preview']}")
            print()
        
        print("⚠️  Le correctif CORRECTIF_SUPPRESSION_ELLIPSIS.md n'a peut-être pas fonctionné.")
        print("   Vérifiez que le rapport a été généré APRÈS le commit 3dd574d.\n")
        sys.exit(1)
    else:
        print("✅ AUCUN point de suspension '...' ou '…' détecté dans le document !")
        print("   Le rapport est conforme aux nouvelles règles.\n")
        sys.exit(0)


if __name__ == "__main__":
    main()

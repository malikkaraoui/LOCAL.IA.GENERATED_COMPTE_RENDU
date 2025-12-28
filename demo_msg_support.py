#!/usr/bin/env python3
"""
Démo : Support des fichiers .msg (emails Outlook) dans la pipeline RAG.

Usage:
    # Installer la dépendance
    pip install extract-msg>=0.48.0
    
    # Exécuter la démo
    python demo_msg_support.py
"""
import sys
from pathlib import Path

# Ajouter le projet au path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def demo_msg_status():
    """Affiche le statut du support .msg."""
    print("=" * 80)
    print("DÉMO : Support .msg (emails Outlook)")
    print("=" * 80)
    print()
    
    # Vérifier si extract-msg est installé
    from core.extractors.msg_extractor import MSG_SUPPORT_AVAILABLE
    
    if MSG_SUPPORT_AVAILABLE:
        print("✅ extract-msg est installé")
        print("   → Les fichiers .msg seront extraits et indexés dans la pipeline RAG")
        print("   → Format : [EMAIL_MSG] Subject/From/To/Date + Body")
        print("   → Pièces jointes PDF/DOCX/DOC/TXT extraites automatiquement")
    else:
        print("⚠️  extract-msg n'est pas installé")
        print("   → Les fichiers .msg ne seront PAS indexés")
        print("   → Installation : pip install extract-msg>=0.48.0")
    print()


def demo_extract_sources_with_msg():
    """Teste extract_sources avec support .msg."""
    from core.extract import extract_sources, MSG_SUPPORT_AVAILABLE
    import tempfile
    
    print("=" * 80)
    print("DÉMO : extract_sources() avec .msg")
    print("=" * 80)
    print()
    
    # Créer un dossier de test
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Créer quelques fichiers de test
        (tmpdir_path / "test.txt").write_text("Contenu texte test")
        (tmpdir_path / "test.pdf").write_bytes(b"%PDF-1.4 fake pdf")
        (tmpdir_path / "test.msg").write_bytes(b"FAKE MSG CONTENT")
        
        print(f"📁 Dossier test : {tmpdir_path}")
        print(f"   - test.txt")
        print(f"   - test.pdf")
        print(f"   - test.msg")
        print()
        
        # Extraire sources
        print("🔍 Extraction en cours...")
        result = extract_sources(
            tmpdir_path,
            enable_msg=True,  # ✅ Support .msg activé
            include_extensions=[".txt", ".pdf", ".msg"]
        )
        
        print()
        print("📊 Résultat :")
        print(f"   - Total fichiers vus : {result['counts']['total_seen']}")
        print(f"   - Extractions OK : {result['counts']['ok']}")
        print(f"   - Erreurs : {result['counts']['errors']}")
        print(f"   - Skippés : {result['counts']['skipped']}")
        print(f"   - Support .msg activé : {result.get('enable_msg', False)}")
        print()
        
        # Détails par fichier
        print("📄 Détails :")
        for doc in result["documents"]:
            path = Path(doc["path"])
            status = "✅" if doc.get("error") is None else "❌"
            print(f"   {status} {path.name} ({doc['ext']}) - {doc['extractor']}")
            if doc.get("error"):
                print(f"      → Erreur : {doc['error'][:100]}")
        print()
        
        if not MSG_SUPPORT_AVAILABLE:
            print("⚠️  Note : extract-msg non installé, les .msg ne sont pas extraits")
            print("   Installation : pip install extract-msg>=0.48.0")
        print()


def demo_training_with_msg():
    """Montre comment .msg est géré dans le training."""
    from core.extractors.msg_extractor import MSG_SUPPORT_AVAILABLE
    
    print("=" * 80)
    print("DÉMO : Training avec .msg")
    print("=" * 80)
    print()
    
    print("🎓 Dans dataset_training.py :")
    print()
    print("1. Extensions exploitables :")
    print("   exploitable_extensions = {'.docx', '.pdf', '.txt', '.doc', '.msg'}")
    print("   → Les dossiers avec .msg seront détectés comme clients exploitables")
    print()
    
    print("2. Warnings :")
    if MSG_SUPPORT_AVAILABLE:
        print("   ✅ extract-msg installé")
        print("   → Pas de warning MSG_EXTRACTOR_MISSING")
        print("   → Les .msg seront comptés dans les sources indexées")
    else:
        print("   ⚠️  extract-msg non installé")
        print("   → Warning MSG_EXTRACTOR_MISSING généré")
        print("   → Message : 'Des fichiers .msg sont présents mais extract-msg n'est pas installé'")
    print()
    
    print("3. training_state.json :")
    print("   → Contient uniquement des stats agrégées (counts)")
    print("   → AUCUN contenu email (body/from/to) stocké")
    print("   → Respecte la contrainte 'pas de données nominatives'")
    print()


def demo_msg_extraction_format():
    """Montre le format d'extraction des .msg."""
    print("=" * 80)
    print("DÉMO : Format d'extraction .msg")
    print("=" * 80)
    print()
    
    print("📧 Format texte indexé :")
    print("-" * 80)
    print("""[EMAIL_MSG]
Subject: Candidature - Poste Développeur Senior
From: john.doe@example.com
To: rh@company.com
Cc: manager@company.com
Date: 2025-12-28 10:30:00
Attachments: CV_John_Doe.pdf; Lettre_Motivation.docx
---
Body:
Bonjour,

Je vous adresse ma candidature pour le poste de Développeur Senior.
Vous trouverez ci-joint mon CV et ma lettre de motivation.

Cordialement,
John Doe
""")
    print("-" * 80)
    print()
    
    print("🔍 Recherche RAG :")
    print("   → 'candidature développeur' → trouve le sujet")
    print("   → 'CV John Doe' → trouve les pièces jointes")
    print("   → 'lettre motivation' → trouve le body")
    print()
    
    print("📎 Pièces jointes extraites :")
    print("   → .pdf, .docx, .doc, .txt automatiquement extraits")
    print("   → Sauvegardés dans sandbox/extracted_msg_attachments/<hash>/")
    print("   → Ajoutés aux sources RAG (indexés comme documents normaux)")
    print()


def main():
    """Exécute toutes les démos."""
    demo_msg_status()
    demo_extract_sources_with_msg()
    demo_training_with_msg()
    demo_msg_extraction_format()
    
    print("=" * 80)
    print("✅ Démo terminée")
    print("=" * 80)
    print()
    
    from core.extractors.msg_extractor import MSG_SUPPORT_AVAILABLE
    
    if not MSG_SUPPORT_AVAILABLE:
        print("⚡ Pour activer le support .msg complet :")
        print("   pip install extract-msg>=0.48.0")
        print()


if __name__ == "__main__":
    main()

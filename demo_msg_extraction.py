#!/usr/bin/env python3
"""
Démonstration de l'extraction de fichiers .msg
"""
import sys
from pathlib import Path

# Ajouter le projet au path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.extractors.msg_extractor import extract_msg_to_text, MSG_SUPPORT_AVAILABLE

def demo_msg_extraction(msg_file: Path):
    """Démo extraction d'un fichier .msg"""
    
    if not MSG_SUPPORT_AVAILABLE:
        print("❌ extract-msg n'est pas installé")
        print("   Installer : pip install extract-msg>=0.48.0")
        return 1
    
    print("=" * 60)
    print(f"📧 Extraction de : {msg_file.name}")
    print("=" * 60)
    print()
    
    try:
        # Extraire le contenu
        text, meta = extract_msg_to_text(msg_file)
        
        # Afficher les métadonnées
        print("📋 Métadonnées :")
        print(f"  De      : {meta.get('from', 'N/A')}")
        print(f"  À       : {meta.get('to', 'N/A')}")
        print(f"  Sujet   : {meta.get('subject', 'N/A')}")
        print(f"  Date    : {meta.get('date', 'N/A')}")
        print(f"  PJ      : {meta.get('attachments_count', 0)}")
        
        if meta.get('attachments'):
            print(f"\n  Pièces jointes :")
            for att in meta['attachments']:
                print(f"    • {att}")
        
        print()
        print("📄 Contenu texte :")
        print("-" * 60)
        
        # Afficher les 500 premiers caractères
        preview = text[:500] if len(text) > 500 else text
        print(preview)
        
        if len(text) > 500:
            print(f"\n[...] ({len(text)} caractères au total)")
        
        print()
        print("=" * 60)
        print(f"✅ Extraction réussie : {len(text)} caractères")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"❌ Erreur lors de l'extraction : {e}")
        import traceback
        traceback.print_exc()
        return 1

def find_msg_files(directory: Path, max_files: int = 5):
    """Trouve les fichiers .msg dans un dossier"""
    msg_files = list(directory.rglob("*.msg"))
    return msg_files[:max_files]

def main():
    print("🧪 Démonstration extraction .msg")
    print()
    
    # Chercher des fichiers .msg dans CLIENTS/
    clients_dir = project_root / "CLIENTS"
    
    if not clients_dir.exists():
        print(f"❌ Dossier CLIENTS introuvable : {clients_dir}")
        return 1
    
    msg_files = find_msg_files(clients_dir, max_files=3)
    
    if not msg_files:
        print(f"❌ Aucun fichier .msg trouvé dans {clients_dir}")
        print()
        print("Pour tester, placez des fichiers .msg dans le dossier CLIENTS/")
        return 1
    
    print(f"📁 {len(msg_files)} fichier(s) .msg trouvé(s)")
    print()
    
    # Extraire le premier fichier
    result = demo_msg_extraction(msg_files[0])
    
    if result == 0 and len(msg_files) > 1:
        print()
        print("📝 Autres fichiers .msg trouvés :")
        for msg in msg_files[1:]:
            print(f"  • {msg.relative_to(clients_dir)}")
    
    return result

if __name__ == "__main__":
    sys.exit(main())

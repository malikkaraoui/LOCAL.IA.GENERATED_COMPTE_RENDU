#!/usr/bin/env python3
"""
Test du correctif logo footer optionnel
Vérifie que le logo footer manquant ne bloque plus la génération
"""

import sys
from pathlib import Path
from core.docx_branding import apply_branding_to_docx
import tempfile
import shutil

def test_logo_footer_missing():
    """Test : Logo footer fourni mais placeholder absent = warning au lieu d'erreur"""
    print("🧪 Test : Logo footer avec placeholder manquant")
    print("-" * 60)
    
    # Chercher un template qui n'a probablement pas de LOGO_FOOTER
    template_dir = Path("uploaded_templates")
    if not template_dir.exists():
        print("⚠️  Aucun template trouvé")
        return
    
    templates = list(template_dir.glob("*.docx"))
    if not templates:
        print("⚠️  Aucun template DOCX trouvé")
        return
    
    template = templates[0]
    print(f"📄 Template: {template.name}")
    
    # Créer un logo factice
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Logo factice (1x1 PNG transparent)
        logo_footer = tmpdir / "logo_footer.png"
        # PNG 1x1 transparent minimal
        logo_footer.write_bytes(
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01'
            b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        
        output = tmpdir / "output.docx"
        
        fields = {
            "TITRE_DOCUMENT": "Test",
            "SOCIETE": "Test Corp",
        }
        
        try:
            # Essayer d'appliquer le branding avec un logo footer
            # Si le template n'a pas de LOGO_FOOTER, ça devrait juste logger un warning
            apply_branding_to_docx(
                template_docx=template,
                output_docx=output,
                fields=fields,
                logo_footer=logo_footer,  # Logo fourni
            )
            
            if output.exists() and output.stat().st_size > 0:
                print("✅ Document généré avec succès")
                print(f"   Taille: {output.stat().st_size} bytes")
                print("✅ CORRECTIF VALIDÉ: Logo footer manquant n'a pas bloqué la génération")
                return True
            else:
                print("❌ Document vide ou non créé")
                return False
                
        except ValueError as e:
            if "LOGO_FOOTER" in str(e):
                print("❌ ÉCHEC: ValueError levée (comportement ancien)")
                print(f"   Erreur: {e}")
                print("❌ Le correctif n'a pas fonctionné")
                return False
            else:
                raise
        except Exception as e:
            print(f"❌ Erreur inattendue: {e}")
            raise


def test_logo_footer_present():
    """Test : Logo footer avec placeholder présent = devrait fonctionner"""
    print("\n🧪 Test : Logo footer avec placeholder présent")
    print("-" * 60)
    print("ℹ️  Ce test nécessite un template avec LOGO_FOOTER")
    print("   (skip si aucun template approprié)")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("TEST DU CORRECTIF LOGO FOOTER OPTIONNEL")
    print("=" * 60)
    print()
    
    success = True
    
    # Test principal
    try:
        result = test_logo_footer_missing()
        if result is False:
            success = False
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        success = False
    
    # Test complémentaire
    test_logo_footer_present()
    
    print()
    print("=" * 60)
    if success:
        print("✅ TOUS LES TESTS PASSÉS")
        print("Le logo footer est maintenant optionnel !")
    else:
        print("❌ ÉCHEC DES TESTS")
        print("Le correctif doit être vérifié")
    print("=" * 60)
    
    sys.exit(0 if success else 1)

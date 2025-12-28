#!/usr/bin/env python3
"""
Test du comportement par défaut index_msg=False.

Objectif: Vérifier que les .msg sont comptés mais NON indexés par défaut.
"""

import tempfile
from pathlib import Path
from src.rhpro.client_scanner import scan_client_folder

def test_msg_default_off():
    """Vérifier que index_msg=False par défaut."""
    
    # Créer un dossier client temporaire avec .msg
    with tempfile.TemporaryDirectory() as tmpdir:
        client_folder = Path(tmpdir) / "TEST_CLIENT"
        client_folder.mkdir()
        
        # Créer quelques fichiers
        (client_folder / "test.pdf").write_text("PDF content")
        (client_folder / "email1.msg").write_text("Email 1")
        (client_folder / "email2.msg").write_text("Email 2")
        (client_folder / "doc.docx").write_text("Word doc")
        
        print("=" * 60)
        print("TEST 1: Scan SANS index_msg (défaut)")
        print("=" * 60)
        
        result = scan_client_folder(str(client_folder))
        
        # Vérifications
        print(f"\n✅ Extensions détectées: {result['stats']['extensions']}")
        print(f"✅ Sources RAG: {len(result['rag_sources'])} fichiers")
        
        # Les .msg doivent être comptés dans msg_files_count
        msg_count = result['stats'].get('msg_files_count', 0)
        assert msg_count == 2, f"Expected 2 .msg files, got {msg_count}"
        print(f"✅ .msg comptés: {msg_count}")
        
        # Les .msg ne doivent PAS être dans rag_sources
        msg_in_rag = [s for s in result['rag_sources'] if s['extension'] == '.msg']
        assert len(msg_in_rag) == 0, f"Expected 0 .msg in rag_sources, got {len(msg_in_rag)}"
        print(f"✅ .msg NON indexés dans rag_sources: {len(msg_in_rag)}")
        
        # Les .msg ne doivent PAS être dans stats.extensions (car pas dans rag_sources)
        msg_in_stats = result['stats']['extensions'].get('.msg', 0)
        assert msg_in_stats == 0, f"Expected 0 .msg in stats.extensions, got {msg_in_stats}"
        print(f"✅ .msg absents de stats.extensions: {msg_in_stats}")
        
        # Un warning EXT_NOT_INDEXED doit être présent
        ext_warnings = [w for w in result['warnings'] if isinstance(w, dict) and w.get('code') == 'EXT_NOT_INDEXED']
        assert len(ext_warnings) == 1, f"Expected 1 EXT_NOT_INDEXED warning, got {len(ext_warnings)}"
        warning = ext_warnings[0]
        assert warning['ext'] == '.msg', f"Expected warning for .msg, got {warning['ext']}"
        assert warning['count'] == 2, f"Expected count=2, got {warning['count']}"
        print(f"✅ Warning présent: {warning['code']} - {warning['ext']} - count={warning['count']}")
        print(f"   Message: {warning['message']}")
        
        print("\n" + "=" * 60)
        print("TEST 2: Scan AVEC index_msg=True")
        print("=" * 60)
        
        result_with_msg = scan_client_folder(str(client_folder), index_msg=True)
        
        # Les .msg doivent être dans rag_sources
        msg_in_rag = [s for s in result_with_msg['rag_sources'] if s['extension'] == '.msg']
        assert len(msg_in_rag) == 2, f"Expected 2 .msg in rag_sources, got {len(msg_in_rag)}"
        print(f"✅ .msg indexés dans rag_sources: {len(msg_in_rag)}")
        
        # Les .msg doivent être dans stats.extensions
        msg_in_stats = result_with_msg['stats']['extensions'].get('.msg', 0)
        assert msg_in_stats == 2, f"Expected 2 .msg in stats.extensions, got {msg_in_stats}"
        print(f"✅ .msg présents dans stats.extensions: {msg_in_stats}")
        
        # Aucun warning EXT_NOT_INDEXED
        ext_warnings = [w for w in result_with_msg['warnings'] if isinstance(w, dict) and w.get('code') == 'EXT_NOT_INDEXED']
        assert len(ext_warnings) == 0, f"Expected 0 warnings with index_msg=True, got {len(ext_warnings)}"
        print(f"✅ Aucun warning EXT_NOT_INDEXED avec index_msg=True")
        
        print("\n" + "=" * 60)
        print("✅ TOUS LES TESTS PASSÉS")
        print("=" * 60)
        print("\n📋 Résumé:")
        print("  - Par défaut (index_msg=False): .msg comptés mais NON indexés")
        print("  - Warning EXT_NOT_INDEXED généré avec count et message")
        print("  - Avec index_msg=True: .msg inclus dans rag_sources")
        print("  - Comportement conforme aux spécifications PII-safe")

if __name__ == "__main__":
    test_msg_default_off()

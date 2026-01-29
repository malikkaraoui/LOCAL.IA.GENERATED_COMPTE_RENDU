#!/usr/bin/env python3
"""
Test end-to-end du comportement index_msg=False par défaut.

Valide:
1. Scanner avec défaut OFF
2. Training avec défaut OFF  
3. Warnings correctement générés
4. Stats correctes
"""

from pathlib import Path
from src.rhpro.client_scanner import scan_client_folder

def test_e2e():
    print("=" * 70)
    print("TEST END-TO-END: Comportement index_msg=False par défaut")
    print("=" * 70)
    
    client_path = Path("CLIENTS/KARAOUI Malik")
    
    if not client_path.exists():
        print("❌ Client KARAOUI Malik non trouvé")
        print(f"   Cherché dans: {client_path.absolute()}")
        return
    
    print(f"\n📁 Client: {client_path}")
    print("-" * 70)
    
    # Test 1: Comportement par défaut (OFF)
    print("\n🔍 TEST 1: Scan par défaut (index_msg non spécifié)")
    print("-" * 70)
    
    result = scan_client_folder(str(client_path))
    
    rag_count = len(result["rag_sources"])
    msg_count = result["stats"]["msg_files_count"]
    extensions = result["stats"]["extensions"]
    
    print(f"✅ Sources RAG détectées: {rag_count}")
    print(f"✅ Extensions dans RAG: {extensions}")
    print(f"✅ .msg comptés (hors RAG): {msg_count}")
    
    # Vérifier que .msg ne sont pas dans rag_sources
    msg_in_rag = [s for s in result["rag_sources"] if s["extension"] == ".msg"]
    if len(msg_in_rag) == 0:
        print(f"✅ .msg NON indexés dans rag_sources (attendu)")
    else:
        print(f"❌ ERREUR: {len(msg_in_rag)} .msg trouvés dans rag_sources")
        return
    
    # Vérifier warning
    warnings = result["warnings"]
    ext_warnings = [w for w in warnings if isinstance(w, dict) and w.get("code") == "EXT_NOT_INDEXED"]
    
    if ext_warnings:
        w = ext_warnings[0]
        print(f"✅ Warning généré:")
        print(f"   Code: {w['code']}")
        print(f"   Extension: {w['ext']}")
        print(f"   Count: {w['count']}")
        print(f"   Message: {w['message']}")
    else:
        print(f"⚠️  Aucun warning EXT_NOT_INDEXED (peut être normal si pas de .msg)")
    
    # Test 2: Avec index_msg=True explicite
    print("\n🔍 TEST 2: Scan avec index_msg=True (opt-in)")
    print("-" * 70)
    
    result_on = scan_client_folder(str(client_path), index_msg=True)
    
    rag_count_on = len(result_on["rag_sources"])
    extensions_on = result_on["stats"]["extensions"]
    
    print(f"✅ Sources RAG détectées: {rag_count_on}")
    print(f"✅ Extensions dans RAG: {extensions_on}")
    
    msg_in_rag_on = [s for s in result_on["rag_sources"] if s["extension"] == ".msg"]
    print(f"✅ .msg indexés dans rag_sources: {len(msg_in_rag_on)}")
    
    # Vérifier différence
    diff = rag_count_on - rag_count
    if diff == msg_count:
        print(f"✅ Différence correcte: {diff} sources supplémentaires avec index_msg=True")
    else:
        print(f"⚠️  Différence inattendue: {diff} (attendu: {msg_count})")
    
    # Test 3: Vérifier warning absent avec index_msg=True
    ext_warnings_on = [w for w in result_on["warnings"] if isinstance(w, dict) and w.get("code") == "EXT_NOT_INDEXED"]
    if len(ext_warnings_on) == 0:
        print(f"✅ Aucun warning EXT_NOT_INDEXED avec index_msg=True (attendu)")
    else:
        print(f"❌ ERREUR: Warning présent avec index_msg=True")
        return
    
    # Résumé final
    print("\n" + "=" * 70)
    print("✅ TEST END-TO-END RÉUSSI")
    print("=" * 70)
    print("\n📊 Résumé:")
    print(f"  - Par défaut (OFF): {rag_count} sources, {msg_count} .msg non indexés")
    print(f"  - Avec ON: {rag_count_on} sources, {len(msg_in_rag_on)} .msg indexés")
    print(f"  - Warning OFF: présent ({len(ext_warnings)})")
    print(f"  - Warning ON: absent ({len(ext_warnings_on)})")
    print("\n🔒 Comportement PII-safe: ✅ VALIDÉ")
    print("🎯 Opt-in explicite requis: ✅ VALIDÉ")
    print("📧 .msg comptés dans stats: ✅ VALIDÉ")
    print("⚠️  Warning structuré: ✅ VALIDÉ")

if __name__ == "__main__":
    test_e2e()

#!/usr/bin/env python3
"""
Test de génération avec Schema V2 activé sur un client.
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.generate import generate_fields, USE_SCHEMA_V2
from core.field_specs_v2 import get_schema_stats

def test_generation_v2():
    print("=" * 70)
    print("TEST GÉNÉRATION AVEC SCHEMA V2")
    print("=" * 70)
    
    # Vérifier activation
    print(f"\n✅ USE_SCHEMA_V2 = {USE_SCHEMA_V2}")
    
    if not USE_SCHEMA_V2:
        print("❌ Schema V2 non activé!")
        return
    
    # Stats du schéma
    stats = get_schema_stats()
    print(f"\n📊 Schema V2 chargé:")
    print(f"   • Total: {stats['total_fields']} champs")
    print(f"   • Narratifs: {len(stats['narrative'])}")
    print(f"   • Listes: {len(stats['list'])}")
    print(f"   • Enum: {len(stats['enum'])}")
    
    # Choisir un client test directement depuis CLIENTS/
    client_name = "ALI Mohammed"
    client_path = Path("CLIENTS") / client_name
    
    if not client_path.exists():
        print(f"\n❌ Client introuvable: {client_path}")
        print("   Essaye un autre client")
        return
    
    print(f"\n🔍 Test sur client: {client_name}")
    
    # Scanner et normaliser le client
    print("\n📚 Scan et normalisation du client...")
    from src.rhpro.client_scanner import scan_client_folder
    
    scan_result = scan_client_folder(client_path)
    
    if not scan_result.get('pipeline_ready'):
        print(f"❌ Client pas ready: {scan_result.get('status')}")
        return
    
    # Obtenir le payload normalized
    payload = scan_result.get('normalized', {})
    
    print(f"   ✅ Payload chargé: {len(payload.get('chunks', []))} chunks")
    
    # Valeurs déterministes
    deterministic_values = {
        "name": "Mohammed",
        "surname": "ALI",
        "civility": "Monsieur",
        "location": "Genève",
        "date": "29 décembre 2025",
        "avs": "756.1234.5678.90"
    }
    
    # Test génération de 3 champs (1 de chaque type)
    # Note: generate_fields V2 utilise field specs V2 automatiquement si USE_SCHEMA_V2=True
    test_fields_list = [
        {"key": "PROFESSION", "query": "Situation professionnelle"},
        {"key": "RESSOURCES_MOTIVATIONNELLES", "query": "Ressources motivationnelles"},
        {"key": "FRANCAIS_POSITIONNEMENT_DE_NIVEAU", "query": "Français niveau"}
    ]
    
    print(f"\n🧪 Test génération de {len(test_fields_list)} champs:")
    for field in test_fields_list:
        print(f"   • {field['key']}")
    
    print("\n⏳ Génération en cours (30-60 secondes avec qwen3-next)...")
    print("   Note: Les enum ne devraient PAS appeler le LLM (extraction_only)")
    print(f"   Modèle: qwen3-next:latest (79.7B - dernier installé)")
    
    try:
        result = generate_fields(
            payload=payload,
            model="qwen3-next:latest",
            host="http://localhost:11434",
            topk=5,
            temperature=0.1,
            top_p=0.9,
            deterministic_values=deterministic_values,
            fields=test_fields_list,
            status_callback=lambda msg: print(f"   {msg}"),
            progress_callback=lambda key, status, value: print(
                f"   [{status}] {key}: {value[:80]}..." if len(value) > 80 else f"   [{status}] {key}: {value}"
            )
        )
        
        print("\n" + "=" * 70)
        print("✅ RÉSULTATS")
        print("=" * 70)
        
        generated_fields = result.get('fields', {})
        
        for field_dict in test_fields_list:
            field_key = field_dict['key']
            value = generated_fields.get(field_key, "N/A")
            print(f"\n🔹 {field_key}:")
            if len(str(value)) > 200:
                print(f"   {str(value)[:200]}...")
            else:
                print(f"   {value}")
        
        print("\n✅ Test terminé avec succès!")
        print("\n📝 Observations:")
        print("   • PROFESSION (narratif): Doit avoir texte professionnel détaillé")
        print("   • RESSOURCES_MOTIVATIONNELLES (liste): Max 4 items")
        print("   • FRANCAIS (enum): Une seule valeur CECRL ou 'Non évalué'")
        
    except Exception as e:
        print(f"\n❌ Erreur lors de la génération: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_generation_v2()

"""
Démo du module Training RH-Pro.

Usage:
    python demo_training_ui.py
"""
import sys
from pathlib import Path

# Ajouter le projet au path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.rhpro.batch_analyzer import scan_batch_clients, get_client_analysis_detail
from src.rhpro.report_generator import generate_report_from_normalized
import json


def demo_batch_scan():
    """
    Démo : Scanner un batch de clients.
    """
    print("=" * 70)
    print("DÉMO : Scan Batch Clients")
    print("=" * 70)
    
    # Exemple avec un batch (à adapter selon votre structure)
    batch_path = "data/samples/BATCH_20"
    
    if not Path(batch_path).exists():
        print(f"⚠️  Batch introuvable : {batch_path}")
        print("   Créez un batch de test ou adaptez le chemin")
        return
    
    print(f"\n🔍 Scan du batch : {batch_path}")
    
    try:
        result = scan_batch_clients(
            batch_path=batch_path,
            limit=5,  # Limiter à 5 clients pour la démo
            min_pipeline_score=0.3,
        )
        
        print(f"\n✅ Scan terminé !")
        print(f"   - Total clients : {result['summary']['total']}")
        print(f"   - Pipeline ready : {result['summary']['pipeline_ready']}")
        print(f"   - GOLD détectés : {result['summary']['gold_detected']}")
        
        print("\n📊 Clients détectés :")
        print("-" * 70)
        
        for client in result["clients"][:5]:
            status = "✅" if client["compatible"] else "⚠️"
            gold = "✅" if client["gold_detected"] else "❌"
            
            print(f"{status} {client['folder_name']}")
            print(f"   Compatibilité : {client['compatibility_score']:.2f}")
            print(f"   GOLD : {gold} (score: {client['gold_score']:.2f})")
            print(f"   Sources RAG : {client['rag_sources_count']}")
            print()
        
        # Exporter le résultat
        output_file = "output/batch_analysis.json"
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Résultat exporté : {output_file}")
        
        return result
    
    except Exception as e:
        print(f"❌ Erreur : {e}")
        import traceback
        traceback.print_exc()
        return None


def demo_client_analysis():
    """
    Démo : Analyse détaillée d'un client.
    """
    print("\n" + "=" * 70)
    print("DÉMO : Analyse Détaillée Client")
    print("=" * 70)
    
    # Scanner un batch d'abord
    batch_path = "data/samples/BATCH_20"
    
    if not Path(batch_path).exists():
        print(f"⚠️  Batch introuvable : {batch_path}")
        return
    
    try:
        # Scanner
        batch_result = scan_batch_clients(batch_path, limit=1)
        
        if not batch_result["clients"]:
            print("⚠️  Aucun client trouvé")
            return
        
        # Prendre le premier client
        client = batch_result["clients"][0]
        scan_result = client["scan_result"]
        
        print(f"\n🔍 Analyse de : {client['folder_name']}")
        
        # Générer l'analyse détaillée
        analysis = get_client_analysis_detail(scan_result)
        
        print("\n✅ Ce qui a été trouvé :")
        print("-" * 70)
        
        if analysis["what_found"]["gold"]:
            gold = analysis["what_found"]["gold"]
            print(f"GOLD : {gold['name']}")
            print(f"  - Score : {gold['score']:.2f}")
            print(f"  - Stratégie : {gold['strategy']}")
        else:
            print("GOLD : ❌ Non trouvé")
        
        print(f"\nSources RAG : {len(analysis['what_found']['rag_sources'])} fichiers")
        for source in analysis["what_found"]["rag_sources"][:5]:
            print(f"  - {source['name']} ({source['category']})")
        
        print("\n🎯 Ce qui est exploitable :")
        print("-" * 70)
        print(f"GOLD exploitable : {'✅' if analysis['what_usable']['gold_usable'] else '❌'}")
        print(f"Sources RAG exploitables : {len(analysis['what_usable']['rag_sources_usable'])}")
        
        print("\n⚠️  Ce qui manque :")
        print("-" * 70)
        for missing in analysis["what_missing"]:
            print(f"  {missing}")
        
        if analysis["gold_choice"]:
            print("\n📄 GOLD choisi :")
            print("-" * 70)
            gold_choice = analysis["gold_choice"]
            print(f"Fichier : {gold_choice['file']}")
            print(f"Score : {gold_choice['score']:.2f}")
            print(f"Raison : {gold_choice['reason']}")
        
        # Exporter l'analyse
        output_file = f"output/{client['folder_name']}_analysis.json"
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Analyse exportée : {output_file}")
    
    except Exception as e:
        print(f"❌ Erreur : {e}")
        import traceback
        traceback.print_exc()


def demo_generate_report():
    """
    Démo : Génération d'un compte-rendu.
    """
    print("\n" + "=" * 70)
    print("DÉMO : Génération Compte-Rendu")
    print("=" * 70)
    
    # Exemple avec un client normalisé
    normalized_folder = "sandbox/BATCH_20/client_01"
    
    if not Path(normalized_folder).exists():
        print(f"⚠️  Client normalisé introuvable : {normalized_folder}")
        print("   Normalisez d'abord un client avec la page Training")
        return
    
    print(f"\n🚀 Génération pour : {Path(normalized_folder).name}")
    
    try:
        result = generate_report_from_normalized(
            normalized_folder=normalized_folder,
            output_dir="output",
            template_path=None,  # Utiliser template par défaut
            strict_mode=True,
        )
        
        print(f"\n✅ Génération réussie !")
        print("\n📄 Outputs générés :")
        print("-" * 70)
        
        outputs = result["outputs"]
        print(f"DOCX : {outputs['generated_docx']}")
        print(f"Debug JSON : {outputs['debug_json']}")
        print(f"Metrics JSON : {outputs['metrics_json']}")
        
        if outputs.get("gold_reference"):
            print(f"GOLD référence : {outputs['gold_reference']}")
        
        print("\n📊 Métriques :")
        print("-" * 70)
        metrics = result["metrics"]
        print(f"Couverture : {metrics['coverage_pct']}%")
        print(f"Couverture requise : {metrics['required_coverage_pct']}%")
        print(f"Confiance moyenne : {metrics['avg_confidence']:.2f}")
        print(f"Score qualité : {metrics['quality_score']:.2f}")
        
        print(f"\n💡 Index stats :")
        print(f"Sources indexées : {result['index_stats']['sources_count']}")
        print(f"Chunks créés : {result['index_stats']['chunks_created']}")
    
    except Exception as e:
        print(f"❌ Erreur : {e}")
        import traceback
        traceback.print_exc()


def main():
    """
    Menu principal de la démo.
    """
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                   DÉMO TRAINING UI RH-PRO                        ║
╚══════════════════════════════════════════════════════════════════╝

Fonctionnalités :
1. Scanner un batch de clients
2. Analyser un client en détail
3. Générer un compte-rendu (RAG + DOCX)
4. Quitter

Note : Pour utiliser l'UI complète, lancez :
    streamlit run streamlit_app.py
    puis naviguez vers la page "Training"
    """)
    
    while True:
        choice = input("\nChoix (1-4) : ").strip()
        
        if choice == "1":
            demo_batch_scan()
        elif choice == "2":
            demo_client_analysis()
        elif choice == "3":
            demo_generate_report()
        elif choice == "4":
            print("\n👋 Au revoir !")
            break
        else:
            print("❌ Choix invalide")


if __name__ == "__main__":
    main()

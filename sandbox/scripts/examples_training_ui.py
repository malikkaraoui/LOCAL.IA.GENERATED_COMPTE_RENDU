"""
Exemples d'utilisation des modules Training UI.

Ces exemples montrent comment utiliser les modules programmatiquement.
"""

# ============================================================================
# EXEMPLE 1 : Scanner un batch de clients
# ============================================================================

from src.rhpro.batch_analyzer import scan_batch_clients, export_batch_analysis
from pathlib import Path

# Scanner un batch
batch_result = scan_batch_clients(
    batch_path="data/samples/BATCH_20",
    limit=None,  # Tous les clients (ou mettre un nombre pour limiter)
    min_pipeline_score=0.3,
)

# Afficher statistiques
print(f"Total clients : {batch_result['summary']['total']}")
print(f"Pipeline ready : {batch_result['summary']['pipeline_ready']}")
print(f"GOLD détectés : {batch_result['summary']['gold_detected']}")

# Parcourir les clients
for client in batch_result["clients"]:
    print(f"\n{client['folder_name']}")
    print(f"  Compatibilité : {client['compatibility_score']:.2f}")
    print(f"  GOLD : {'✅' if client['gold_detected'] else '❌'}")
    print(f"  Sources RAG : {client['rag_sources_count']}")
    print(f"  Warnings : {client['warnings_count']}")

# Exporter le résultat
export_batch_analysis(batch_result, "output/batch_analysis.json")


# ============================================================================
# EXEMPLE 2 : Analyser un client en détail
# ============================================================================

from src.rhpro.client_scanner import scan_client_folder
from src.rhpro.batch_analyzer import get_client_analysis_detail

# Scanner un client
client_folder = "data/samples/BATCH_20/KARAOUI Malik"
scan_result = scan_client_folder(client_folder)

# Générer l'analyse détaillée
analysis = get_client_analysis_detail(scan_result)

# Afficher ce qui a été trouvé
print("\n=== Ce que j'ai trouvé ===")
if analysis["what_found"]["gold"]:
    gold = analysis["what_found"]["gold"]
    print(f"GOLD : {gold['name']} (score: {gold['score']:.2f})")
else:
    print("GOLD : Non trouvé")

print(f"\nSources RAG : {len(analysis['what_found']['rag_sources'])} fichiers")
for source in analysis["what_found"]["rag_sources"][:5]:
    print(f"  - {source['name']} ({source['category']})")

# Afficher ce qui est exploitable
print("\n=== Ce que je peux exploiter ===")
print(f"GOLD exploitable : {'✅' if analysis['what_usable']['gold_usable'] else '❌'}")
print(f"Sources RAG exploitables : {len(analysis['what_usable']['rag_sources_usable'])}")

# Afficher ce qui manque
print("\n=== Ce qui manque ===")
for missing in analysis["what_missing"]:
    print(f"  {missing}")


# ============================================================================
# EXEMPLE 3 : Générer un rapport avec RAG
# ============================================================================

from src.rhpro.rag_generator import RAGGenerator

# Initialiser le générateur RAG
rag = RAGGenerator(
    chunk_size=512,
    chunk_overlap=50,
    embedding_model="text-embedding-3-small",
    llm_model="gpt-4o-mini",
    temperature=0.1,
)

# Construire l'index depuis les sources
index_result = rag.build_index_from_sources(
    sources_folder="sandbox/BATCH_20/client_01/sources",
    file_extensions=[".docx", ".pdf", ".txt"],
)

print(f"\nIndex construit :")
print(f"  Sources : {index_result['sources_count']}")
print(f"  Chunks : {index_result['chunks_created']}")

# Champs à extraire
template_fields = [
    "nom",
    "prenom",
    "date_naissance",
    "situation_professionnelle",
    "objectifs_professionnels",
    "projet_formation",
]

# Générer le rapport
report_result = rag.generate_report(
    template_fields=template_fields,
    strict_mode=True,  # Interdiction d'inventer
    max_retries=2,
)

# Afficher les champs remplis
print("\n=== Champs extraits ===")
for field, value in report_result["fields"].items():
    confidence = report_result["debug"][field]["confidence"]
    citations_count = len(report_result["debug"][field]["citations"])
    print(f"\n{field}: {value}")
    print(f"  Confiance: {confidence:.2f}")
    print(f"  Citations: {citations_count}")

# Afficher métriques
print("\n=== Métriques ===")
metrics = report_result["metrics"]
print(f"Couverture : {metrics['coverage_pct']}%")
print(f"Couverture requise : {metrics['required_coverage_pct']}%")
print(f"Confiance moyenne : {metrics['avg_confidence']:.2f}")
print(f"Score qualité : {metrics['quality_score']:.2f}")


# ============================================================================
# EXEMPLE 4 : Générer un rapport complet (RAG + DOCX)
# ============================================================================

from src.rhpro.report_generator import RHProReportGenerator

# Initialiser le générateur
generator = RHProReportGenerator(
    template_path=None,  # Utiliser template par défaut (ou chemin vers .docx)
    template_fields=None,  # Utiliser champs par défaut
)

# Générer depuis un client normalisé
result = generator.generate_from_client(
    sources_folder="sandbox/BATCH_20/client_01/sources",
    gold_path="sandbox/BATCH_20/client_01/gold/rapport_final.docx",
    output_dir="output",
    client_name="client_01",
    strict_mode=True,
)

# Afficher les outputs générés
print("\n=== Outputs générés ===")
print(f"DOCX : {result['outputs']['generated_docx']}")
print(f"Debug JSON : {result['outputs']['debug_json']}")
print(f"Metrics JSON : {result['outputs']['metrics_json']}")

# Afficher métriques
print("\n=== Métriques ===")
metrics = result["metrics"]
print(f"Couverture : {metrics['coverage_pct']}%")
print(f"Confiance : {metrics['avg_confidence']:.2f}")
print(f"Qualité : {metrics['quality_score']:.2f}")


# ============================================================================
# EXEMPLE 5 : Générer depuis un dossier normalisé
# ============================================================================

from src.rhpro.report_generator import generate_report_from_normalized

# Générer depuis sandbox
result = generate_report_from_normalized(
    normalized_folder="sandbox/BATCH_20/client_01",
    output_dir="output",
    template_path=None,  # Optionnel
    strict_mode=True,
)

print("\n=== Rapport généré ===")
print(f"Client : {result['client_name']}")
print(f"Couverture : {result['metrics']['coverage_pct']}%")
print(f"Qualité : {result['metrics']['quality_score']:.2f}")


# ============================================================================
# EXEMPLE 6 : Aperçu des chunks RAG (debug)
# ============================================================================

from src.rhpro.rag_generator import get_chunks_preview

# Obtenir un aperçu des chunks
chunks = get_chunks_preview(
    sources_folder="sandbox/BATCH_20/client_01/sources",
    max_chunks=10,
    chunk_size=512,
)

print("\n=== Aperçu Chunks RAG ===")
for i, chunk in enumerate(chunks, 1):
    print(f"\nChunk {i}:")
    print(f"  Source : {chunk['source_file']}")
    print(f"  Longueur : {chunk['text_length']} chars")
    print(f"  Texte : {chunk['text'][:200]}...")


# ============================================================================
# EXEMPLE 7 : Calcul score de compatibilité
# ============================================================================

from src.rhpro.batch_analyzer import calculate_compatibility_score

# Exemple de scan result
scan_result = {
    "stats": {
        "gold_found": True,
        "gold_score": 0.8,
        "rag_sources_count": 5,
        "folders_detected": 5,
    },
    "pipeline_ready": True,
}

# Calculer le score
score = calculate_compatibility_score(scan_result)
print(f"\nScore de compatibilité : {score:.2f}")

# Interprétation
if score >= 0.8:
    print("  → Excellent (✅)")
elif score >= 0.6:
    print("  → Bon (✅)")
elif score >= 0.4:
    print("  → Moyen (⚠️)")
else:
    print("  → Faible (❌)")


# ============================================================================
# EXEMPLE 8 : Normaliser puis générer
# ============================================================================

from src.rhpro.client_scanner import scan_client_folder
from src.rhpro.client_normalizer import normalize_client_to_sandbox
from src.rhpro.report_generator import generate_report_from_normalized

# 1. Scanner le client
client_folder = "data/samples/BATCH_20/KARAOUI Malik"
scan_result = scan_client_folder(client_folder)

if not scan_result["pipeline_ready"]:
    print("❌ Client non prêt pour le pipeline")
    exit(1)

# 2. Normaliser en sandbox
norm_result = normalize_client_to_sandbox(
    scan_result=scan_result,
    batch_name="BATCH_20",
    sandbox_root="sandbox",
    create_normalized_alias=True,
)

print(f"\n✅ Client normalisé : {norm_result['normalized_path']}")

# 3. Générer le rapport
gen_result = generate_report_from_normalized(
    normalized_folder=norm_result["normalized_path"],
    output_dir="output",
    strict_mode=True,
)

print(f"\n✅ Rapport généré :")
print(f"  DOCX : {gen_result['outputs']['generated_docx']}")
print(f"  Couverture : {gen_result['metrics']['coverage_pct']}%")
print(f"  Qualité : {gen_result['metrics']['quality_score']:.2f}")


# ============================================================================
# EXEMPLE 9 : Traiter un batch complet (scan + normaliser + générer)
# ============================================================================

from src.rhpro.batch_analyzer import scan_batch_clients
from src.rhpro.client_normalizer import normalize_client_to_sandbox
from src.rhpro.report_generator import generate_report_from_normalized
import json

# 1. Scanner le batch
print("1️⃣ Scan du batch...")
batch_result = scan_batch_clients("data/samples/BATCH_20", limit=5)

# 2. Filtrer les clients pipeline-ready
ready_clients = [
    c for c in batch_result["clients"]
    if c["pipeline_ready"]
]

print(f"\n2️⃣ {len(ready_clients)} client(s) prêt(s)")

# 3. Traiter chaque client
results = []

for client in ready_clients:
    print(f"\n📍 Traitement : {client['folder_name']}")
    
    try:
        # Normaliser
        norm_result = normalize_client_to_sandbox(
            scan_result=client["scan_result"],
            batch_name="BATCH_20",
            sandbox_root="sandbox",
        )
        
        # Générer
        gen_result = generate_report_from_normalized(
            normalized_folder=norm_result["normalized_path"],
            output_dir="output",
            strict_mode=True,
        )
        
        results.append({
            "client": client["folder_name"],
            "success": True,
            "normalized_path": norm_result["normalized_path"],
            "outputs": gen_result["outputs"],
            "metrics": gen_result["metrics"],
        })
        
        print(f"  ✅ Succès (qualité: {gen_result['metrics']['quality_score']:.2f})")
    
    except Exception as e:
        results.append({
            "client": client["folder_name"],
            "success": False,
            "error": str(e),
        })
        print(f"  ❌ Erreur : {e}")

# 4. Résumé
print("\n" + "=" * 70)
print("RÉSUMÉ")
print("=" * 70)

success_count = sum(1 for r in results if r["success"])
print(f"Traités : {len(results)}")
print(f"Succès : {success_count}")
print(f"Erreurs : {len(results) - success_count}")

# Qualité moyenne
if success_count > 0:
    avg_quality = sum(
        r["metrics"]["quality_score"]
        for r in results if r["success"]
    ) / success_count
    print(f"Qualité moyenne : {avg_quality:.2f}")

# Exporter résultats
output_file = "output/batch_generation_results.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"\n💾 Résultats exportés : {output_file}")


# ============================================================================
# EXEMPLE 10 : Configuration personnalisée
# ============================================================================

from src.rhpro.rag_generator import RAGGenerator
from src.rhpro.report_generator import RHProReportGenerator

# RAG avec configuration personnalisée
rag = RAGGenerator(
    chunk_size=1024,  # Chunks plus grands
    chunk_overlap=100,  # Overlap plus important
    embedding_model="text-embedding-3-small",
    llm_model="gpt-4o",  # Modèle plus puissant
    temperature=0.0,  # Déterministe
)

# Champs personnalisés
custom_fields = [
    "nom_complet",
    "situation_actuelle",
    "projet_professionnel",
    "competences_cles",
    "freins_majeurs",
]

# Générateur avec template personnalisé
generator = RHProReportGenerator(
    template_path="data/templates/TEMPLATE_CUSTOM.docx",
    template_fields=custom_fields,
)

# Générer
result = generator.generate_from_client(
    sources_folder="sandbox/BATCH_20/client_01/sources",
    output_dir="output",
    client_name="client_01_custom",
    strict_mode=True,
)

print(f"\n✅ Rapport personnalisé généré")
print(f"  Template : TEMPLATE_CUSTOM.docx")
print(f"  Champs : {len(custom_fields)}")
print(f"  Qualité : {result['metrics']['quality_score']:.2f}")

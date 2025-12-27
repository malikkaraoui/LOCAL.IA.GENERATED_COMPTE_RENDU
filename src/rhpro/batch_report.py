"""
Batch Report Generator - Génère un rapport exploitable après un batch RH-Pro.

Produit batch_report.json + CSV pour analyse des résultats de validation.
"""
import json
import csv
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from .validation_profiles import ValidationResult


def generate_batch_report(
    validation_results: Dict[str, ValidationResult],
    output_dir: Path,
    batch_name: str = "batch",
    sandbox_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Génère un rapport de batch exploitable (JSON + CSV).
    
    Args:
        validation_results: Dict {client_name: ValidationResult}
        output_dir: Dossier de sortie des rapports
        batch_name: Nom du batch
        sandbox_dir: Dossier sandbox (pour récupérer meta.json)
        
    Returns:
        Dict avec statistiques et chemins des rapports générés
    
    Example:
        >>> from src.rhpro.validation_profiles import validate_batch
        >>> results = validate_batch(Path("output"), ValidationProfile.STRICT)
        >>> report = generate_batch_report(results, Path("output"), "batch_001")
        >>> print(f"GO: {report['summary']['go_count']}/{report['summary']['total']}")
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Collecter les données pour chaque client
    clients_data = []
    
    for client_name, result in validation_results.items():
        # Chemins vers les outputs
        generated_docx = output_dir / f"{client_name}_generated.docx"
        debug_json = output_dir / f"{client_name}_debug.json"
        metrics_json = output_dir / f"{client_name}_metrics.json"
        validation_json = output_dir / f"{client_name}_validation.json"
        
        # Détecter le GOLD
        gold_detected = False
        gold_path = None
        if sandbox_dir:
            for batch_dir in sandbox_dir.iterdir():
                if batch_dir.is_dir():
                    client_sandbox = batch_dir / client_name
                    if client_sandbox.exists():
                        meta_file = client_sandbox / "meta.json"
                        if meta_file.exists():
                            with open(meta_file, 'r', encoding='utf-8') as f:
                                meta = json.load(f)
                                gold_detected = meta.get("gold_score", 0) > 0.3
                                if gold_detected:
                                    gold_folder = client_sandbox / "gold"
                                    if gold_folder.exists():
                                        gold_files = list(gold_folder.glob("*.docx"))
                                        if gold_files:
                                            gold_path = str(gold_files[0])
        
        # Compter les sources par type
        sources_by_type = {}
        if debug_json.exists():
            with open(debug_json, 'r', encoding='utf-8') as f:
                debug_data = json.load(f)
                sources = debug_data.get("index", {}).get("sources", [])
                for source in sources:
                    ext = source.get("extension", "unknown")
                    sources_by_type[ext] = sources_by_type.get(ext, 0) + 1
        
        # Extraire missing_critical_fields depuis reasons
        missing_critical = []
        for reason in result.reasons:
            if "missing_fields:" in reason:
                fields_str = reason.split("missing_fields:")[-1].strip()
                missing_critical = [f.strip() for f in fields_str.split(",")]
                break
        
        client_data = {
            "client_name": client_name,
            "status": result.status,
            "profile": result.profile,
            "scores": result.scores,
            "missing_critical_fields": missing_critical,
            "gold_detected": gold_detected,
            "gold_path": gold_path,
            "sources_count": sum(sources_by_type.values()),
            "sources_by_type": sources_by_type,
            "reasons": result.reasons,
            "actions": result.actions,
            "outputs": {
                "generated_docx": str(generated_docx) if generated_docx.exists() else None,
                "debug_json": str(debug_json) if debug_json.exists() else None,
                "metrics_json": str(metrics_json) if metrics_json.exists() else None,
                "validation_json": str(validation_json) if validation_json.exists() else None,
            }
        }
        
        clients_data.append(client_data)
    
    # Calculer les statistiques globales
    total = len(clients_data)
    go_count = sum(1 for c in clients_data if c["status"] == "GO")
    no_go_count = sum(1 for c in clients_data if c["status"] == "NO_GO")
    draft_count = sum(1 for c in clients_data if c["status"] == "DRAFT")
    gold_detected_count = sum(1 for c in clients_data if c["gold_detected"])
    
    # Statistiques des raisons d'échec
    all_reasons = []
    for client in clients_data:
        all_reasons.extend(client["reasons"])
    
    reason_counts = {}
    for reason in all_reasons:
        reason_type = reason.split(":")[0] if ":" in reason else reason
        reason_counts[reason_type] = reason_counts.get(reason_type, 0) + 1
    
    top_reasons = sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Construire le rapport
    report = {
        "batch_name": batch_name,
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": total,
            "go_count": go_count,
            "no_go_count": no_go_count,
            "draft_count": draft_count,
            "go_rate": round(go_count / total * 100, 2) if total > 0 else 0,
            "gold_detected_count": gold_detected_count,
            "gold_rate": round(gold_detected_count / total * 100, 2) if total > 0 else 0,
            "top_failure_reasons": [{"reason": r, "count": c} for r, c in top_reasons],
        },
        "clients": clients_data,
    }
    
    # Exporter JSON
    json_path = output_dir / "batch_report.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # Exporter CSV
    csv_path = output_dir / "batch_report.csv"
    _export_batch_csv(clients_data, csv_path)
    
    return {
        "success": True,
        "report_json": str(json_path),
        "report_csv": str(csv_path),
        "summary": report["summary"],
    }


def _export_batch_csv(clients_data: List[Dict], output_path: Path) -> None:
    """
    Exporte les données du batch en CSV pour analyse Excel/Sheets.
    
    Args:
        clients_data: Données des clients
        output_path: Chemin du fichier CSV
    """
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow([
            "Client",
            "Status",
            "Profile",
            "Quality Score",
            "Required Coverage (%)",
            "Weighted Coverage (%)",
            "Avg Confidence",
            "Missing Critical Fields",
            "Gold Detected",
            "Sources Count",
            "Sources Types",
            "Reasons",
            "Actions",
            "Generated DOCX",
            "Debug JSON",
            "Metrics JSON",
        ])
        
        # Rows
        for client in clients_data:
            writer.writerow([
                client["client_name"],
                client["status"],
                client["profile"],
                f"{client['scores'].get('quality_score', 0):.2f}",
                f"{client['scores'].get('required_coverage', 0) * 100:.1f}",
                f"{client['scores'].get('weighted_coverage', 0) * 100:.1f}",
                f"{client['scores'].get('avg_confidence', 0):.2f}",
                ", ".join(client["missing_critical_fields"]),
                "Oui" if client["gold_detected"] else "Non",
                client["sources_count"],
                ", ".join(f"{k}:{v}" for k, v in client["sources_by_type"].items()),
                " | ".join(client["reasons"]),
                " | ".join(client["actions"]),
                client["outputs"].get("generated_docx", ""),
                client["outputs"].get("debug_json", ""),
                client["outputs"].get("metrics_json", ""),
            ])


def print_batch_summary(report: Dict[str, Any]) -> None:
    """
    Affiche un résumé lisible du rapport batch.
    
    Args:
        report: Rapport batch (retour de generate_batch_report)
    
    Example:
        >>> report = generate_batch_report(results, Path("output"), "batch_001")
        >>> print_batch_summary(report)
    """
    summary = report["summary"]
    
    print()
    print("=" * 80)
    print(f"  BATCH REPORT SUMMARY")
    print("=" * 80)
    print()
    print(f"📊 Total Clients    : {summary['total']}")
    print(f"✅ GO               : {summary['go_count']} ({summary['go_rate']:.1f}%)")
    print(f"❌ NO_GO            : {summary['no_go_count']}")
    print(f"📝 DRAFT            : {summary['draft_count']}")
    print(f"🏆 GOLD Detected    : {summary['gold_detected_count']} ({summary['gold_rate']:.1f}%)")
    print()
    
    if summary.get("top_failure_reasons"):
        print("🔍 Top Failure Reasons:")
        for i, reason_data in enumerate(summary["top_failure_reasons"][:5], 1):
            print(f"   {i}. {reason_data['reason']} ({reason_data['count']} clients)")
        print()
    
    print("=" * 80)
    print()


def load_batch_report(report_path: Path) -> Dict[str, Any]:
    """
    Charge un rapport batch depuis JSON.
    
    Args:
        report_path: Chemin vers batch_report.json
        
    Returns:
        Dict du rapport
    """
    with open(report_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def filter_batch_report(
    report: Dict[str, Any],
    status_filter: Optional[str] = None,
    gold_only: bool = False,
) -> List[Dict[str, Any]]:
    """
    Filtre les clients d'un rapport batch.
    
    Args:
        report: Rapport batch
        status_filter: Filtrer par status (GO, NO_GO, DRAFT)
        gold_only: Ne garder que les clients avec GOLD détecté
        
    Returns:
        Liste des clients filtrés
    
    Example:
        >>> report = load_batch_report(Path("output/batch_report.json"))
        >>> no_go_clients = filter_batch_report(report, status_filter="NO_GO")
        >>> print(f"{len(no_go_clients)} clients NO_GO")
    """
    clients = report.get("clients", [])
    
    if status_filter:
        clients = [c for c in clients if c["status"] == status_filter]
    
    if gold_only:
        clients = [c for c in clients if c["gold_detected"]]
    
    return clients


# ============================================================================
# CLI pour test rapide
# ============================================================================

def main():
    """Point d'entrée CLI pour générer un batch report depuis un dossier."""
    import sys
    from .validation_profiles import validate_batch, ValidationProfile
    
    if len(sys.argv) < 2:
        print("Usage: python -m src.rhpro.batch_report <output_dir> [profile]")
        print("Profiles: strict, standard, draft")
        sys.exit(1)
    
    output_dir = Path(sys.argv[1])
    profile_name = sys.argv[2] if len(sys.argv) > 2 else "strict"
    profile = ValidationProfile[profile_name.upper()]
    
    print(f"🔍 Validating batch in: {output_dir}")
    print(f"📋 Profile: {profile.value.upper()}")
    print()
    
    # Valider tous les rapports
    results = validate_batch(output_dir, profile)
    
    # Générer le batch report
    report_data = generate_batch_report(
        validation_results=results,
        output_dir=output_dir,
        batch_name=output_dir.name,
    )
    
    # Afficher le résumé
    print_batch_summary(report_data)
    
    print(f"✅ Batch report saved:")
    print(f"   JSON: {report_data['report_json']}")
    print(f"   CSV:  {report_data['report_csv']}")
    print()


if __name__ == "__main__":
    main()

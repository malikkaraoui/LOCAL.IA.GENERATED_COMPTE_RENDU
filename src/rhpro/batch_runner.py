"""
Batch Runner — Découverte et parsing de multiples dossiers clients
"""
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from .parse_bilan import parse_bilan_docx_to_normalized


def discover_sources(root_dir: str) -> List[Path]:
    """
    Scanne récursivement root_dir et retourne tous les dossiers contenant 'source.docx'
    
    Args:
        root_dir: Dossier racine à scanner
        
    Returns:
        Liste des dossiers (Path) contenant source.docx
        
    Example:
        >>> folders = discover_sources('data/samples')
        >>> print([f.name for f in folders])
        ['client_01', 'client_02', 'client_03', 'client_04', 'client_05']
    """
    root = Path(root_dir)
    if not root.exists():
        raise FileNotFoundError(f"Root directory not found: {root_dir}")
    
    discovered = []
    
    # Chercher tous les source.docx
    for docx_file in root.rglob("source.docx"):
        client_folder = docx_file.parent
        discovered.append(client_folder)
    
    return sorted(discovered)


def run_batch(
    root_dir: str,
    ruleset_path: str,
    output_dir: str = None,
    write_normalized_in_source: bool = False,
    gate_profile_override: str = None
) -> Dict[str, Any]:
    """
    Exécute la pipeline sur tous les dossiers découverts et agrège les résultats
    
    Args:
        root_dir: Dossier racine contenant les dossiers clients
        ruleset_path: Chemin vers le ruleset YAML
        output_dir: Dossier de sortie pour les rapports (ex: out/batch/)
        write_normalized_in_source: Si True, écrit source_normalized.json dans chaque dossier client
        gate_profile_override: Si fourni, force ce profil pour tous les documents
        
    Returns:
        dict avec:
        - 'timestamp': str ISO
        - 'root_dir': str
        - 'ruleset_path': str
        - 'discovered_count': int
        - 'results': list[dict] avec détails par client
        - 'summary': dict avec stats agrégées
        
    Example:
        >>> batch_result = run_batch(
        ...     'data/samples',
        ...     'config/rulesets/rhpro_v1.yaml',
        ...     'out/batch'
        ... )
        >>> print(f"Processed {len(batch_result['results'])} clients")
    """
    # Découverte
    discovered_folders = discover_sources(root_dir)
    
    if not discovered_folders:
        return {
            "timestamp": datetime.now().isoformat(),
            "root_dir": root_dir,
            "ruleset_path": ruleset_path,
            "discovered_count": 0,
            "results": [],
            "summary": {"error": "No source.docx files found"}
        }
    
    # Préparer le dossier de sortie si spécifié
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
    
    # Traitement batch
    results = []
    errors = []
    go_count = 0
    no_go_count = 0
    
    for client_folder in discovered_folders:
        client_name = client_folder.name
        docx_file = client_folder / "source.docx"
        
        result_entry = {
            "client_dir": str(client_folder),
            "client_name": client_name,
            "docx_file": str(docx_file)
        }
        
        try:
            # Exécuter la pipeline
            parsed = parse_bilan_docx_to_normalized(
                str(docx_file),
                ruleset_path,
                gate_profile_override=gate_profile_override
            )
            
            normalized = parsed["normalized"]
            report = parsed["report"]
            
            # Extraire les infos du production gate
            gate = report.get("production_gate", {})
            status = gate.get("status", "UNKNOWN")
            profile_id = gate.get("profile", "unknown")  # Utiliser 'profile' pas 'profile_id'
            signals = gate.get("signals", {})
            criteria = gate.get("criteria", {})
            reasons = gate.get("reasons", [])
            missing_required = gate.get("missing_required_effective", [])
            
            # Stats
            coverage = report.get("required_coverage_ratio", 0.0)
            unknown_titles = len(report.get("unknown_titles", []))
            placeholders = len(report.get("placeholders_detected", []))
            warnings = report.get("warnings", [])
            
            result_entry.update({
                "status": "success",
                "profile": profile_id,
                "gate_status": status,
                "required_coverage_ratio": round(coverage, 3),
                "missing_required_sections": missing_required,
                "unknown_titles_count": unknown_titles,
                "placeholders_count": placeholders,
                "reasons": reasons,
                "warnings": warnings,
                "signals": signals,
                "criteria": criteria
            })
            
            # Écrire source_normalized.json dans le dossier client si demandé
            if write_normalized_in_source:
                normalized_file = client_folder / "source_normalized.json"
                with open(normalized_file, "w", encoding="utf-8") as f:
                    json.dump(normalized, f, ensure_ascii=False, indent=2)
            
            # Écrire aussi dans output_dir si spécifié
            if output_dir:
                client_output = output_path / client_name
                client_output.mkdir(exist_ok=True)
                
                with open(client_output / "normalized.json", "w", encoding="utf-8") as f:
                    json.dump(normalized, f, ensure_ascii=False, indent=2)
                
                with open(client_output / "report.json", "w", encoding="utf-8") as f:
                    json.dump(report, f, ensure_ascii=False, indent=2)
            
            # Compter les statuts
            if status == "GO":
                go_count += 1
            elif status == "NO-GO":
                no_go_count += 1
                
        except Exception as e:
            result_entry.update({
                "status": "error",
                "error_type": type(e).__name__,
                "error_message": str(e)
            })
            errors.append({
                "client": client_name,
                "error": str(e)
            })
        
        results.append(result_entry)
    
    # Résumé agrégé
    summary = {
        "total_processed": len(results),
        "successful": len([r for r in results if r["status"] == "success"]),
        "errors": len(errors),
        "gate_go": go_count,
        "gate_no_go": no_go_count,
        "avg_coverage": round(
            sum(r.get("required_coverage_ratio", 0) for r in results if r["status"] == "success") / max(len(results), 1),
            3
        ),
        "error_details": errors
    }
    
    batch_result = {
        "timestamp": datetime.now().isoformat(),
        "root_dir": root_dir,
        "ruleset_path": ruleset_path,
        "discovered_count": len(discovered_folders),
        "gate_profile_override": gate_profile_override,
        "results": results,
        "summary": summary
    }
    
    # Écrire les rapports globaux dans output_dir
    if output_dir:
        with open(output_path / "batch_report.json", "w", encoding="utf-8") as f:
            json.dump(batch_result, f, ensure_ascii=False, indent=2)
        
        # Générer un rapport Markdown lisible
        markdown = generate_batch_report_markdown(batch_result)
        with open(output_path / "batch_report.md", "w", encoding="utf-8") as f:
            f.write(markdown)
    
    return batch_result


def generate_batch_report_markdown(batch_result: Dict[str, Any]) -> str:
    """
    Génère un rapport Markdown lisible à partir du batch_result
    
    Args:
        batch_result: Résultat de run_batch()
        
    Returns:
        str contenant le rapport formaté en Markdown
    """
    md_lines = []
    
    # Header
    md_lines.append("# Batch Parser Report\n")
    md_lines.append(f"**Timestamp**: {batch_result['timestamp']}\n")
    md_lines.append(f"**Root Directory**: `{batch_result['root_dir']}`\n")
    md_lines.append(f"**Ruleset**: `{batch_result['ruleset_path']}`\n")
    if batch_result.get("gate_profile_override"):
        md_lines.append(f"**Profile Override**: {batch_result['gate_profile_override']}\n")
    md_lines.append("\n---\n")
    
    # Summary
    summary = batch_result["summary"]
    md_lines.append("## Summary\n")
    md_lines.append(f"- **Total Processed**: {summary['total_processed']}\n")
    md_lines.append(f"- **Successful**: {summary['successful']}\n")
    md_lines.append(f"- **Errors**: {summary['errors']}\n")
    md_lines.append(f"- **Production Gate GO**: {summary['gate_go']}\n")
    md_lines.append(f"- **Production Gate NO-GO**: {summary['gate_no_go']}\n")
    md_lines.append(f"- **Average Coverage**: {summary['avg_coverage']:.1%}\n")
    md_lines.append("\n---\n")
    
    # Detailed results
    md_lines.append("## Detailed Results\n")
    
    for result in batch_result["results"]:
        client = result["client_name"]
        status = result["status"]
        
        if status == "success":
            profile = result.get("profile", "unknown")
            gate_status = result.get("gate_status", "UNKNOWN")
            coverage = result.get("required_coverage_ratio", 0.0)
            missing = result.get("missing_required_sections", [])
            unknown = result.get("unknown_titles_count", 0)
            placeholders = result.get("placeholders_count", 0)
            reasons = result.get("reasons", [])
            
            md_lines.append(f"### ✓ {client}\n")
            md_lines.append(f"- **Profile**: `{profile}`\n")
            md_lines.append(f"- **Gate Status**: **{gate_status}**\n")
            md_lines.append(f"- **Coverage**: {coverage:.1%}\n")
            md_lines.append(f"- **Missing Required**: {len(missing)}\n")
            if missing:
                for m in missing[:5]:  # Limit to 5
                    md_lines.append(f"  - `{m}`\n")
                if len(missing) > 5:
                    md_lines.append(f"  - ... et {len(missing) - 5} autres\n")
            md_lines.append(f"- **Unknown Titles**: {unknown}\n")
            md_lines.append(f"- **Placeholders**: {placeholders}\n")
            if reasons:
                md_lines.append("- **Reasons**:\n")
                for r in reasons[:3]:
                    md_lines.append(f"  - {r}\n")
            md_lines.append("\n")
        else:
            error_type = result.get("error_type", "Unknown")
            error_msg = result.get("error_message", "")
            md_lines.append(f"### ✗ {client}\n")
            md_lines.append(f"- **Status**: ERROR\n")
            md_lines.append(f"- **Error Type**: `{error_type}`\n")
            md_lines.append(f"- **Message**: {error_msg}\n")
            md_lines.append("\n")
    
    # Errors section
    if summary["error_details"]:
        md_lines.append("---\n")
        md_lines.append("## Errors\n")
        for err in summary["error_details"]:
            md_lines.append(f"- **{err['client']}**: {err['error']}\n")
    
    return "".join(md_lines)

"""
Couche de validation indépendante pour les rapports RH-Pro.

Prend metrics.json + debug.json + meta.json et retourne un statut GO/NO-GO
avec des actions recommandées.

Profils disponibles :
- STRICT : Production RH-Pro (exigences maximales)
- STANDARD : Acceptable (quelques tolérances)
- DRAFT : Brouillon (génération OK mais non validé)
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum


class ValidationStatus(str, Enum):
    """Statut de validation d'un rapport."""
    GO = "GO"
    NO_GO = "NO_GO"
    DRAFT = "DRAFT"


class ValidationProfile(str, Enum):
    """Profils de validation disponibles."""
    STRICT = "strict"
    STANDARD = "standard"
    DRAFT = "draft"


@dataclass
class ValidationResult:
    """Résultat de la validation d'un rapport."""
    status: str  # GO | NO_GO | DRAFT
    profile: str  # strict | standard | draft
    reasons: List[str]
    actions: List[str]
    scores: Dict[str, float]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convertit en JSON."""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


# ============================================================================
# CHAMPS CRITIQUES RH-PRO (Liste fixe, non négociable)
# ============================================================================
# Ces champs DOIVENT être présents pour une validation STRICT
# Règle : no-evidence = no-claim (chaque claim doit avoir des preuves)

CRITICAL_FIELDS = {
    # Identité (obligatoire)
    "identity": [
        "nom",           # Obligatoire
        "prenom",        # Obligatoire
        "civilite",      # Optionnel mais recommandé
    ],
    # AVS : si présent → extraire, sinon "Non renseigné / à confirmer"
    "avs": [
        "numero_avs",    # Si trouvé, doit être extrait
    ],
    # Profession / Formation : au moins l'un des deux DOIT être renseigné
    "professional": [
        "situation_professionnelle",
        "niveau_formation",
    ],
}

# Liste plate pour compatibilité
CRITICAL_FIELDS_FLAT = [
    "nom",
    "prenom",
    "numero_avs",
    "situation_professionnelle",
    "niveau_formation",
]

# Seuils de validation par profil
PROFILE_THRESHOLDS = {
    ValidationProfile.STRICT: {
        "missing_critical_fields_max": 0,    # Aucun champ critique manquant
        "required_coverage_min": 0.85,
        "quality_score_min": 0.75,
        "sources_count_min": 1,              # Au moins 1 source (sinon c'est du vide)
        "confidence_min": 0.7,
        "profession_or_formation_required": True,  # Au moins l'un des deux
    },
    ValidationProfile.STANDARD: {
        "missing_critical_fields_max": 1,
        "required_coverage_min": 0.75,
        "quality_score_min": 0.65,
        "sources_count_min": 2,
        "confidence_min": 0.6,
    },
    ValidationProfile.DRAFT: {
        "missing_critical_fields_max": 999,  # Pas de limite
        "required_coverage_min": 0.0,
        "quality_score_min": 0.0,
        "sources_count_min": 0,
        "confidence_min": 0.0,
    },
}


def validate_report(
    metrics_path: Path,
    debug_path: Optional[Path] = None,
    meta_path: Optional[Path] = None,
    profile: ValidationProfile = ValidationProfile.STANDARD,
) -> ValidationResult:
    """
    Valide un rapport selon un profil donné.
    
    Args:
        metrics_path: Chemin vers metrics.json
        debug_path: Chemin vers debug.json (optionnel)
        meta_path: Chemin vers meta.json (optionnel)
        profile: Profil de validation à utiliser
    
    Returns:
        ValidationResult avec status, reasons, actions
    
    Example:
        >>> result = validate_report(
        ...     Path("output/client_metrics.json"),
        ...     Path("output/client_debug.json"),
        ...     profile=ValidationProfile.STRICT
        ... )
        >>> print(result.status)  # GO ou NO_GO ou DRAFT
    """
    # Charger les données
    metrics = _load_json(metrics_path)
    debug = _load_json(debug_path) if debug_path else {}
    meta = _load_json(meta_path) if meta_path else {}
    
    # Extraire les scores
    scores = {
        "required_coverage": metrics.get("required_coverage", 0) / 100,  # Normaliser 0-1
        "weighted_coverage": metrics.get("weighted_coverage", 0) / 100,
        "quality_score": metrics.get("quality_score", 0),
        "avg_confidence": metrics.get("avg_confidence", 0),
    }
    
    # Compter les sources RAG
    sources_count = 0
    if debug.get("index"):
        sources_count = debug["index"].get("sources_count", 0)
    elif meta.get("sources_rag"):
        sources_count = len(meta["sources_rag"])
    
    # Identifier les champs critiques manquants
    missing_critical = _get_missing_critical_fields(metrics, debug)
    
    # Récupérer les seuils du profil
    thresholds = PROFILE_THRESHOLDS[profile]
    
    # Valider selon le profil
    reasons = []
    actions = []
    status = ValidationStatus.GO
    
    # 1. Champs critiques
    if len(missing_critical) > thresholds["missing_critical_fields_max"]:
        reasons.append(f"missing_critical_fields: {len(missing_critical)} (max: {thresholds['missing_critical_fields_max']})")
        actions.append("add_identity_sources")
        if profile != ValidationProfile.DRAFT:
            status = ValidationStatus.NO_GO
    
    # 2. Couverture requise
    if scores["required_coverage"] < thresholds["required_coverage_min"]:
        reasons.append(f"low_required_coverage: {scores['required_coverage']:.2f} < {thresholds['required_coverage_min']}")
        actions.append("add_sources")
        if profile != ValidationProfile.DRAFT:
            status = ValidationStatus.NO_GO
    
    # 3. Score de qualité
    if scores["quality_score"] < thresholds["quality_score_min"]:
        reasons.append(f"low_quality_score: {scores['quality_score']:.2f} < {thresholds['quality_score_min']}")
        actions.append("improve_source_quality")
        if profile != ValidationProfile.DRAFT:
            status = ValidationStatus.NO_GO
    
    # 4. Nombre de sources
    if sources_count < thresholds["sources_count_min"]:
        reasons.append(f"insufficient_sources: {sources_count} < {thresholds['sources_count_min']}")
        actions.append("add_rag_sources")
        if profile != ValidationProfile.DRAFT:
            status = ValidationStatus.NO_GO
    
    # 5. Confiance moyenne
    if scores["avg_confidence"] < thresholds["confidence_min"]:
        reasons.append(f"low_confidence: {scores['avg_confidence']:.2f} < {thresholds['confidence_min']}")
        actions.append("verify_extracted_fields")
        if profile != ValidationProfile.DRAFT:
            status = ValidationStatus.NO_GO
    
    # 6. Vérifier si GOLD manquant (warning)
    if meta.get("gold_score", 0) < 0.3:
        reasons.append("no_gold_detected")
        actions.append("select_gold_candidate")
        # GOLD manquant n'est pas bloquant mais dégradé
        if status == ValidationStatus.GO and profile == ValidationProfile.STRICT:
            status = ValidationStatus.NO_GO
    
    # Si profil DRAFT, toujours marquer DRAFT
    if profile == ValidationProfile.DRAFT:
        status = ValidationStatus.DRAFT
        if not reasons:
            reasons.append("draft_mode_enabled")
        if not actions:
            actions.append("review_and_complete")
    
    # Ajouter les champs manquants dans les raisons
    if missing_critical:
        reasons.append(f"missing_fields: {', '.join(missing_critical)}")
        actions.append("confirm_identity")
    
    return ValidationResult(
        status=status.value,
        profile=profile.value,
        reasons=reasons,
        actions=actions,
        scores=scores,
    )


def validate_batch(
    output_dir: Path,
    profile: ValidationProfile = ValidationProfile.STANDARD,
) -> Dict[str, ValidationResult]:
    """
    Valide tous les rapports d'un batch.
    
    Args:
        output_dir: Dossier contenant les outputs (metrics.json, debug.json)
        profile: Profil de validation à utiliser
    
    Returns:
        Dict {client_name: ValidationResult}
    
    Example:
        >>> results = validate_batch(Path("output"), ValidationProfile.STRICT)
        >>> go_count = sum(1 for r in results.values() if r.status == "GO")
        >>> print(f"{go_count}/{len(results)} rapports validés")
    """
    results = {}
    
    # Trouver tous les metrics.json
    for metrics_file in output_dir.glob("*_metrics.json"):
        client_name = metrics_file.stem.replace("_metrics", "")
        
        # Trouver les fichiers associés
        debug_file = output_dir / f"{client_name}_debug.json"
        
        # Chercher meta.json dans sandbox si disponible
        meta_file = None
        sandbox_path = Path("sandbox")
        if sandbox_path.exists():
            for batch_dir in sandbox_path.iterdir():
                if batch_dir.is_dir():
                    client_meta = batch_dir / client_name / "meta.json"
                    if client_meta.exists():
                        meta_file = client_meta
                        break
        
        # Valider
        result = validate_report(
            metrics_path=metrics_file,
            debug_path=debug_file if debug_file.exists() else None,
            meta_path=meta_file,
            profile=profile,
        )
        
        results[client_name] = result
    
    return results


def get_validation_summary(results: Dict[str, ValidationResult]) -> Dict[str, Any]:
    """
    Génère un résumé des validations.
    
    Args:
        results: Dict {client_name: ValidationResult}
    
    Returns:
        Dict avec statistiques globales
    
    Example:
        >>> results = validate_batch(Path("output"))
        >>> summary = get_validation_summary(results)
        >>> print(f"Taux GO: {summary['go_rate']:.1%}")
    """
    total = len(results)
    go_count = sum(1 for r in results.values() if r.status == ValidationStatus.GO)
    no_go_count = sum(1 for r in results.values() if r.status == ValidationStatus.NO_GO)
    draft_count = sum(1 for r in results.values() if r.status == ValidationStatus.DRAFT)
    
    # Top reasons
    all_reasons = []
    for result in results.values():
        all_reasons.extend(result.reasons)
    
    reason_counts = {}
    for reason in all_reasons:
        # Extraire le type de raison (avant le ":")
        reason_type = reason.split(":")[0] if ":" in reason else reason
        reason_counts[reason_type] = reason_counts.get(reason_type, 0) + 1
    
    top_reasons = sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Scores moyens
    avg_scores = {}
    if results:
        for key in ["required_coverage", "weighted_coverage", "quality_score", "avg_confidence"]:
            values = [r.scores.get(key, 0) for r in results.values()]
            avg_scores[key] = sum(values) / len(values) if values else 0
    
    return {
        "total": total,
        "go_count": go_count,
        "no_go_count": no_go_count,
        "draft_count": draft_count,
        "go_rate": go_count / total if total > 0 else 0,
        "top_reasons": top_reasons,
        "avg_scores": avg_scores,
    }


def _load_json(path: Optional[Path]) -> Dict[str, Any]:
    """Charge un fichier JSON."""
    if not path or not path.exists():
        return {}
    
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _get_missing_critical_fields(metrics: Dict, debug: Dict) -> List[str]:
    """Identifie les champs critiques manquants."""
    missing = []
    
    # Récupérer les champs extraits avec leurs valeurs
    extracted_fields = {}
    
    if debug.get("fields"):
        for field_name, field_info in debug["fields"].items():
            if isinstance(field_info, dict):
                value = field_info.get("value", "")
                extracted_fields[field_name] = value
            else:
                extracted_fields[field_name] = field_info
    
    # Vérifier identité (nom + prenom obligatoires)
    for field in CRITICAL_FIELDS["identity"]:
        if field in ["nom", "prenom"]:
            value = extracted_fields.get(field, "")
            if not value or value == "Non renseigné":
                missing.append(field)
    
    # Vérifier AVS : si présent → doit être extrait, sinon accepter "Non renseigné / à confirmer"
    avs_field = "numero_avs"
    avs_value = extracted_fields.get(avs_field, "")
    if avs_value and avs_value not in ["Non renseigné", "Non renseigné / à confirmer", "À confirmer"]:
        # AVS présent et extrait : OK
        pass
    elif not avs_value or avs_value == "Non renseigné":
        # AVS non trouvé : doit être marqué "Non renseigné / à confirmer"
        missing.append(f"{avs_field}_confirmation_needed")
    
    # Vérifier profession OU formation : au moins l'un des deux DOIT être renseigné
    profession = extracted_fields.get("situation_professionnelle", "")
    formation = extracted_fields.get("niveau_formation", "")
    
    profession_filled = profession and profession != "Non renseigné"
    formation_filled = formation and formation != "Non renseigné"
    
    if not profession_filled and not formation_filled:
        missing.append("profession_or_formation")
    
    return missing


def export_validation_report(
    results: Dict[str, ValidationResult],
    output_path: Path,
    format: str = "json",
) -> None:
    """
    Exporte les résultats de validation.
    
    Args:
        results: Dict {client_name: ValidationResult}
        output_path: Chemin du fichier de sortie
        format: Format d'export (json, csv, markdown)
    
    Example:
        >>> results = validate_batch(Path("output"))
        >>> export_validation_report(results, Path("validation_report.json"))
    """
    if format == "json":
        data = {
            "summary": get_validation_summary(results),
            "results": {name: result.to_dict() for name, result in results.items()},
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    elif format == "markdown":
        lines = ["# Rapport de Validation", ""]
        
        summary = get_validation_summary(results)
        lines.append(f"**Total**: {summary['total']} rapports")
        lines.append(f"**GO**: {summary['go_count']} ({summary['go_rate']:.1%})")
        lines.append(f"**NO_GO**: {summary['no_go_count']}")
        lines.append(f"**DRAFT**: {summary['draft_count']}")
        lines.append("")
        
        lines.append("## Détails par Client")
        lines.append("")
        
        for name, result in results.items():
            status_emoji = "✅" if result.status == "GO" else "❌" if result.status == "NO_GO" else "📝"
            lines.append(f"### {status_emoji} {name}")
            lines.append(f"- **Status**: {result.status}")
            lines.append(f"- **Profile**: {result.profile}")
            lines.append(f"- **Quality Score**: {result.scores.get('quality_score', 0):.2f}")
            lines.append(f"- **Required Coverage**: {result.scores.get('required_coverage', 0):.2%}")
            
            if result.reasons:
                lines.append(f"- **Reasons**: {', '.join(result.reasons)}")
            
            if result.actions:
                lines.append(f"- **Actions**: {', '.join(result.actions)}")
            
            lines.append("")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    
    elif format == "csv":
        import csv
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Client", "Status", "Profile", "Quality Score",
                "Required Coverage", "Reasons", "Actions"
            ])
            
            for name, result in results.items():
                writer.writerow([
                    name,
                    result.status,
                    result.profile,
                    f"{result.scores.get('quality_score', 0):.2f}",
                    f"{result.scores.get('required_coverage', 0):.2%}",
                    "; ".join(result.reasons),
                    "; ".join(result.actions),
                ])


# ============================================================================
# CLI pour test rapide
# ============================================================================

def main():
    """Point d'entrée CLI pour tester la validation."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python validation_profiles.py <metrics.json> [profile]")
        print("Profiles: strict, standard, draft")
        sys.exit(1)
    
    metrics_path = Path(sys.argv[1])
    profile_name = sys.argv[2] if len(sys.argv) > 2 else "standard"
    
    profile = ValidationProfile[profile_name.upper()]
    
    # Déduire les chemins debug et meta
    base_name = metrics_path.stem.replace("_metrics", "")
    debug_path = metrics_path.parent / f"{base_name}_debug.json"
    
    result = validate_report(
        metrics_path=metrics_path,
        debug_path=debug_path if debug_path.exists() else None,
        profile=profile,
    )
    
    print("=" * 70)
    print(f"VALIDATION REPORT - Profile: {profile.value.upper()}")
    print("=" * 70)
    print()
    print(f"Status: {result.status}")
    print(f"Profile: {result.profile}")
    print()
    print("Scores:")
    for key, value in result.scores.items():
        print(f"  - {key}: {value:.2f}")
    print()
    
    if result.reasons:
        print("Reasons:")
        for reason in result.reasons:
            print(f"  ❌ {reason}")
        print()
    
    if result.actions:
        print("Recommended Actions:")
        for action in result.actions:
            print(f"  🔧 {action}")
        print()
    
    # Export JSON
    json_output = metrics_path.parent / f"{base_name}_validation.json"
    with open(json_output, 'w', encoding='utf-8') as f:
        f.write(result.to_json())
    
    print(f"✅ Validation exported to: {json_output}")
    
    sys.exit(0 if result.status == "GO" else 1)


if __name__ == "__main__":
    main()

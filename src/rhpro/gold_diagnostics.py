"""
Module de diagnostic pour les clients "GOLD missing".

Objectif : Comprendre pourquoi certains clients n'ont pas de GOLD détecté
sans modifier l'algorithme de détection existant.

Usage:
    from src.rhpro.gold_diagnostics import diagnose_gold_missing
    
    if not gold_detected:
        diagnostic = diagnose_gold_missing(client_folder)
        write_diagnostic(diagnostic, output_file)
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from .client_scanner import (
    GOLD_EXTENSIONS,
    GOLD_KEYWORDS_HIGH_PRIORITY,
    GOLD_KEYWORDS_MEDIUM_PRIORITY,
    GOLD_EXCLUDE_PATTERNS,
    score_gold_candidate,
)
from src.utils.file_filters import is_ignored_filename


def extract_text_snippets(file_path: Path, max_snippets: int = 3, snippet_length: int = 200) -> List[str]:
    """
    Extrait des snippets de texte d'un fichier pour diagnostic.
    
    Args:
        file_path: Chemin vers le fichier
        max_snippets: Nombre max de snippets à extraire
        snippet_length: Longueur max de chaque snippet
        
    Returns:
        Liste de snippets (texte brut)
    """
    snippets = []
    
    try:
        if file_path.suffix == ".docx":
            from docx import Document
            doc = Document(str(file_path))
            
            # Extraire les 3 premiers paragraphes non-vides
            para_count = 0
            for para in doc.paragraphs:
                if para.text.strip():
                    text = para.text.strip()[:snippet_length]
                    snippets.append(text)
                    para_count += 1
                    if para_count >= max_snippets:
                        break
                        
        elif file_path.suffix in [".txt", ".md"]:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = []
                for line in f:
                    if line.strip():
                        lines.append(line.strip())
                        if len(lines) >= max_snippets:
                            break
                snippets = [line[:snippet_length] for line in lines]
                
        elif file_path.suffix == ".pdf":
            # Éviter extraction lourde, retourner un placeholder
            snippets = ["[PDF - extraction non implémentée pour diagnostic]"]
            
    except Exception as e:
        snippets = [f"[Erreur extraction: {type(e).__name__}]"]
    
    return snippets


def analyze_candidate_rejection(file_path: Path, score: float, threshold: float = 0.5) -> List[str]:
    """
    Analyse pourquoi un candidat a été rejeté.
    
    Args:
        file_path: Chemin du fichier candidat
        score: Score GOLD calculé
        threshold: Seuil de décision
        
    Returns:
        Liste des raisons de rejet
    """
    reasons = []
    filename = file_path.name.lower()
    
    # 1. Extension
    if file_path.suffix not in GOLD_EXTENSIONS:
        reasons.append(f"unsupported_extension:{file_path.suffix}")
    
    # 2. Patterns d'exclusion
    for pattern in GOLD_EXCLUDE_PATTERNS:
        if pattern in filename:
            reasons.append(f"excluded_pattern:{pattern}")
    
    # 3. Mots-clés manquants
    high_matches = [kw for kw in GOLD_KEYWORDS_HIGH_PRIORITY if kw in filename]
    medium_matches = [kw for kw in GOLD_KEYWORDS_MEDIUM_PRIORITY if kw in filename]
    
    if not high_matches and not medium_matches:
        reasons.append("no_gold_keywords_found")
    elif not high_matches:
        reasons.append("no_high_priority_keywords")
    
    # 4. Score en dessous du seuil
    if score < threshold:
        reasons.append(f"below_threshold:{score:.2f}<{threshold}")
    
    # 5. Fichier vide ou très petit
    if file_path.exists():
        size = file_path.stat().st_size
        if size == 0:
            reasons.append("empty_file")
        elif size < 1024:  # < 1 KB
            reasons.append(f"too_small:{size}bytes")
    
    return reasons if reasons else ["score_acceptable_but_not_best"]


def diagnose_gold_missing(client_folder: Path, gold_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Diagnostique pourquoi le GOLD n'a pas été détecté pour un client.
    
    Args:
        client_folder: Dossier du client
        gold_result: Résultat de find_gold_document() (None si non détecté)
        
    Returns:
        Dict de diagnostic structuré
    """
    client_folder = Path(client_folder).resolve()
    
    diagnostic = {
        "client_id": client_folder.name,
        "client_path": str(client_folder),
        "gold_detected": gold_result is not None,
        "timestamp": datetime.now().isoformat(),
        "candidates": [],
        "notes": [],
    }
    
    # Si GOLD détecté, pas besoin de diagnostic
    if gold_result:
        diagnostic["notes"].append("gold_detected_ok")
        return diagnostic
    
    # Scanner tous les fichiers potentiels (même ceux exclus)
    all_docx_files = []
    for file_path in client_folder.rglob("*"):
        if file_path.is_file() and file_path.suffix in GOLD_EXTENSIONS:
            all_docx_files.append(file_path)
    
    # Analyser chaque fichier
    for file_path in all_docx_files:
        # Vérifier si ignoré par filtres
        is_ignored = is_ignored_filename(file_path)
        
        # Calculer le score
        score = score_gold_candidate(file_path)
        
        # Analyser les raisons de rejet
        reject_reasons = analyze_candidate_rejection(file_path, score)
        
        # Extraire snippets (seulement si pas ignoré pour éviter coût)
        snippets = []
        if not is_ignored and score > 0.0:
            snippets = extract_text_snippets(file_path, max_snippets=3, snippet_length=150)
        
        # Construire l'entrée candidat
        relative_path = file_path.relative_to(client_folder)
        candidate = {
            "path": str(relative_path),
            "absolute_path": str(file_path),
            "type": file_path.suffix,
            "size_bytes": file_path.stat().st_size if file_path.exists() else 0,
            "is_ignored": is_ignored,
            "gold_score": round(score, 3),
            "gold_pass": score >= 0.5,  # Seuil de décision
            "reject_reasons": reject_reasons,
            "snippets": snippets,
        }
        
        diagnostic["candidates"].append(candidate)
    
    # Ajouter des notes de diagnostic
    if not all_docx_files:
        diagnostic["notes"].append("no_docx_files_found")
    else:
        diagnostic["notes"].append(f"{len(all_docx_files)}_docx_files_scanned")
    
    # Identifier patterns communs
    if all_docx_files:
        all_ignored = all(is_ignored_filename(f) for f in all_docx_files)
        if all_ignored:
            diagnostic["notes"].append("all_files_ignored_by_filters")
        
        max_score = max((score_gold_candidate(f) for f in all_docx_files), default=0.0)
        if max_score < 0.1:
            diagnostic["notes"].append("all_scores_very_low")
        elif max_score < 0.5:
            diagnostic["notes"].append(f"max_score_below_threshold:{max_score:.2f}")
    
    # Tri des candidats par score décroissant
    diagnostic["candidates"].sort(key=lambda c: c["gold_score"], reverse=True)
    
    return diagnostic


def write_diagnostics_jsonl(diagnostics: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Écrit les diagnostics dans un fichier JSONL.
    
    Args:
        diagnostics: Liste de diagnostics
        output_path: Chemin du fichier de sortie
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        for diag in diagnostics:
            f.write(json.dumps(diag, ensure_ascii=False) + "\n")


def write_diagnostics_summary(diagnostics: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Écrit un résumé Markdown lisible des diagnostics.
    
    Args:
        diagnostics: Liste de diagnostics
        output_path: Chemin du fichier de sortie
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Diagnostic GOLD Missing\n\n")
        f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Nombre de clients analysés**: {len(diagnostics)}\n\n")
        f.write("---\n\n")
        
        for diag in diagnostics:
            f.write(f"## Client: {diag['client_id']}\n\n")
            f.write(f"**Path**: `{diag['client_path']}`\n\n")
            
            if diag.get('notes'):
                f.write("**Notes**:\n")
                for note in diag['notes']:
                    f.write(f"- {note}\n")
                f.write("\n")
            
            candidates = diag.get('candidates', [])
            f.write(f"**Candidats analysés**: {len(candidates)}\n\n")
            
            if candidates:
                f.write("| Fichier | Score | Pass | Raisons Rejet | Snippets |\n")
                f.write("|---------|-------|------|---------------|----------|\n")
                
                for cand in candidates[:5]:  # Top 5 seulement
                    filename = Path(cand['path']).name
                    score = cand['gold_score']
                    passed = "✅" if cand['gold_pass'] else "❌"
                    reasons = ", ".join(cand['reject_reasons'][:2])  # 2 premières raisons
                    snippet_preview = cand['snippets'][0][:50] + "..." if cand['snippets'] else "N/A"
                    
                    f.write(f"| {filename} | {score:.2f} | {passed} | {reasons} | {snippet_preview} |\n")
                
                f.write("\n")
                
                # Détails du meilleur candidat
                if candidates[0]['gold_score'] > 0.0:
                    best = candidates[0]
                    f.write("### Meilleur Candidat\n\n")
                    f.write(f"**Fichier**: `{best['path']}`\n")
                    f.write(f"**Score**: {best['gold_score']}\n")
                    f.write(f"**Taille**: {best['size_bytes']} bytes\n")
                    f.write(f"**Ignoré**: {best['is_ignored']}\n\n")
                    
                    if best['reject_reasons']:
                        f.write("**Raisons de rejet**:\n")
                        for reason in best['reject_reasons']:
                            f.write(f"- `{reason}`\n")
                        f.write("\n")
                    
                    if best['snippets']:
                        f.write("**Snippets extraits**:\n")
                        for i, snippet in enumerate(best['snippets'][:3], 1):
                            f.write(f"\n{i}. `{snippet}`\n")
                        f.write("\n")
            
            f.write("---\n\n")

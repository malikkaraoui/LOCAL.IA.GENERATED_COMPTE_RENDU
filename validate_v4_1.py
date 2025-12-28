#!/usr/bin/env python3
"""
Script de validation V4.1 - Patch tables + GOLD strict

Teste les critères d'acceptation avant utilisation de l'interface Streamlit.
"""
import sys
from pathlib import Path
from src.rhpro.dataset_training import analyze_dataset

# Configuration
BATCH_20_PATH = "/Users/malik/Documents/RH PRO BASE DONNEE/DATASET TRAINING/BATCH 20"


def validate_v4_1(dataset_path: str):
    """
    Valide les critères d'acceptation V4.1 sur un dataset.
    
    Critères:
    1. Aucune section avec coverage>0 et lines=0
    2. unknown_titles sans PII (AVS, dates, NOM/PRENOM)
    3. GOLD sélectionné si présent
    4. Sections avec lines>0 ou absentes
    """
    print("=" * 70)
    print("🔍 VALIDATION V4.1 - Patch tables + GOLD strict")
    print("=" * 70)
    print()
    
    # Vérifier path
    dataset = Path(dataset_path)
    if not dataset.exists():
        print(f"❌ Dataset introuvable : {dataset_path}")
        return False
    
    print(f"📂 Dataset : {dataset.name}")
    print(f"📍 Path    : {dataset}")
    print()
    
    # Lancer analyse
    print("⏳ Analyse en cours...")
    try:
        result = analyze_dataset(dataset_path, limit=None)
    except Exception as e:
        print(f"❌ Erreur analyse : {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print(f"✅ Analyse terminée : {len(result.clients)} clients")
    print()
    
    # ============================================================================
    # CRITÈRE 1 : Aucune section avec coverage>0 et lines=0
    # ============================================================================
    print("=" * 70)
    print("✅ CRITÈRE 1 : Sections fantômes (coverage>0 mais lines=0)")
    print("=" * 70)
    
    sections_stats = result.patterns.get("sections_stats", {})
    
    phantom_sections = []
    for sec, stats in sections_stats.items():
        coverage = stats.get("coverage", 0)
        avg_lines = stats.get("avg_lines", 0)
        median_lines = stats.get("p50_lines", 0)
        p90_lines = stats.get("p90_lines", 0)
        
        if coverage > 0 and avg_lines == 0 and median_lines == 0 and p90_lines == 0:
            phantom_sections.append({
                "section": sec,
                "coverage": coverage * 100,
                "avg": avg_lines,
                "median": median_lines,
                "p90": p90_lines
            })
    
    if phantom_sections:
        print(f"❌ ÉCHEC : {len(phantom_sections)} section(s) fantôme(s) détectée(s)")
        for phantom in phantom_sections:
            print(f"   - {phantom['section']}: coverage={phantom['coverage']}%, "
                  f"lines=(avg={phantom['avg']}, median={phantom['median']}, p90={phantom['p90']})")
        print()
    else:
        print("✅ SUCCÈS : Aucune section fantôme")
        print()
    
    # ============================================================================
    # CRITÈRE 2 : unknown_titles sans PII
    # ============================================================================
    print("=" * 70)
    print("✅ CRITÈRE 2 : Anti-PII dans unknown_titles")
    print("=" * 70)
    
    # unknown_titles_top est un dict {title: count}
    unknown_titles_dict = result.patterns.get("unknown_titles_top", {})
    
    # Patterns PII à détecter
    pii_patterns = {
        "labels": ["NOM", "PRENOM", "N AVS", "AVS", "N°AVS", "NUMERO AVS", 
                   "DATE", "DATES", "DATE DE NAISSANCE"],
        "avs_pattern": r"\b756[\s\.]?\d{4}[\s\.]?\d{4}[\s\.]?\d{2}\b",
        "date_pattern": r"\b\d{1,2}[\/\.\s]\d{1,2}[\/\.\s]\d{2,4}\b"
    }
    
    pii_detected = []
    
    for title, count in unknown_titles_dict.items():
        # Labels formulaires
        if title in pii_patterns["labels"]:
            pii_detected.append(f"{title} (count={count}) - label formulaire")
            continue
        
        # AVS suisse
        import re
        if re.search(pii_patterns["avs_pattern"], title):
            pii_detected.append(f"{title} (count={count}) - AVS suisse")
            continue
        
        # Dates
        if re.search(pii_patterns["date_pattern"], title):
            pii_detected.append(f"{title} (count={count}) - date")
            continue
        
        # Trop de chiffres
        digit_count = sum(c.isdigit() for c in title)
        if digit_count >= 6:
            pii_detected.append(f"{title} (count={count}) - trop de chiffres ({digit_count})")
    
    if pii_detected:
        print(f"❌ ÉCHEC : {len(pii_detected)} titre(s) PII détecté(s)")
        for pii in pii_detected[:10]:  # Limiter à 10
            print(f"   - {pii}")
        if len(pii_detected) > 10:
            print(f"   ... et {len(pii_detected) - 10} autres")
        print()
    else:
        print("✅ SUCCÈS : Aucun PII détecté dans unknown_titles_top")
        print(f"   Titres inconnus : {len(unknown_titles_dict)}")
        if unknown_titles_dict:
            print("   Top 5 :")
            for i, (title, count) in enumerate(list(unknown_titles_dict.items())[:5]):
                print(f"      {i+1}. {title} (count={count})")
        print()
    
    # ============================================================================
    # CRITÈRE 3 : GOLD sélectionné
    # ============================================================================
    print("=" * 70)
    print("✅ CRITÈRE 3 : Sélection GOLD stricte")
    print("=" * 70)
    
    gold_selection_issues = []
    clients_with_gold = 0
    
    # Accéder aux debug docx_selections si disponible
    docx_selections = getattr(result, 'docx_selections', [])
    
    if docx_selections:
        for selection in docx_selections:
            client = selection.get("client", "?")
            selected = selection.get("selected_docx")
            score = selection.get("score", 0)
            gold_mode = selection.get("gold_mode", False)
            candidates = selection.get("candidates", [])
            
            # Déterminer si client a GOLD
            has_gold = any(c.get("is_gold", False) for c in candidates)
            
            if has_gold:
                clients_with_gold += 1
                
                # Vérifier que selected est GOLD
                selected_is_gold = False
                if selected:
                    selected_name = Path(selected).name.lower()
                    selected_is_gold = "gold" in selected_name or any(
                        c.get("path") == selected and c.get("is_gold", False) 
                        for c in candidates
                    )
                
                if not selected_is_gold:
                    gold_selection_issues.append({
                        "client": client,
                        "selected": Path(selected).name if selected else "None",
                        "gold_mode": gold_mode,
                        "score": score
                    })
        
        print(f"Clients avec GOLD : {clients_with_gold}")
        
        if gold_selection_issues:
            print(f"❌ ÉCHEC : {len(gold_selection_issues)} client(s) sans GOLD sélectionné")
            for issue in gold_selection_issues[:5]:
                print(f"   - {issue['client']}: sélection={issue['selected']}, "
                      f"gold_mode={issue['gold_mode']}, score={issue['score']}")
            print()
        else:
            if clients_with_gold > 0:
                print("✅ SUCCÈS : Tous les clients avec GOLD ont un GOLD sélectionné")
            else:
                print("⚠️  INFO : Aucun client avec GOLD dans ce dataset")
            print()
    else:
        print("⚠️  INFO : Pas de debug docx_selections disponible")
        print("   (Relancer avec version récente de dataset_training.py)")
        print()
    
    # ============================================================================
    # CRITÈRE 4 : Sections avec lines>0
    # ============================================================================
    print("=" * 70)
    print("✅ CRITÈRE 4 : Cohérence coverage ↔ lines")
    print("=" * 70)
    
    for sec, stats in sections_stats.items():
        coverage = stats.get("coverage", 0) * 100
        clients = stats.get("clients", 0)
        lines_avg = stats.get("avg_lines", 0)
        lines_median = stats.get("p50_lines", 0)
        
        status = "✅" if (coverage > 0 and lines_avg > 0) or (coverage == 0) else "❌"
        print(f"{status} {sec:40s} coverage={coverage:5.1f}% clients={clients:2d} "
              f"lines(avg={lines_avg:.1f}, median={lines_median:.1f})")
    
    print()
    
    # ============================================================================
    # RÉSUMÉ
    # ============================================================================
    print("=" * 70)
    print("📊 RÉSUMÉ VALIDATION V4.1")
    print("=" * 70)
    
    all_passed = (
        len(phantom_sections) == 0 and
        len(pii_detected) == 0 and
        len(gold_selection_issues) == 0
    )
    
    print(f"Sections fantômes    : {'✅ 0' if len(phantom_sections) == 0 else f'❌ {len(phantom_sections)}'}")
    print(f"PII détectés         : {'✅ 0' if len(pii_detected) == 0 else f'❌ {len(pii_detected)}'}")
    print(f"GOLD non sélectionné : {'✅ 0' if len(gold_selection_issues) == 0 else f'❌ {len(gold_selection_issues)}'}")
    print()
    
    if all_passed:
        print("🎉 ✅ VALIDATION V4.1 RÉUSSIE")
        print("   Le dataset est prêt pour l'interface Streamlit !")
        return True
    else:
        print("⚠️  ❌ VALIDATION V4.1 ÉCHOUÉE")
        print("   Des corrections sont nécessaires avant production.")
        return False


if __name__ == "__main__":
    # Utiliser BATCH_20_PATH par défaut ou argument
    dataset_path = sys.argv[1] if len(sys.argv) > 1 else BATCH_20_PATH
    
    success = validate_v4_1(dataset_path)
    sys.exit(0 if success else 1)

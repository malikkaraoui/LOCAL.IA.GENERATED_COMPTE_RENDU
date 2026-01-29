#!/usr/bin/env python3
"""
Démonstration du système de prompt wrapper V1
Conforme à prompt.md - Montre comment les prompts SYSTEM et USER sont construits
"""

from core.field_specs_v2 import (
    FIELD_SPECS_V2,
    build_system_prompt,
    build_user_prompt,
    validate_prompt_has_sentinel,
    PROMPT_SENTINEL,
    PROMPT_VERSION
)


def demo_system_prompt():
    """Montre le SYSTEM PROMPT global"""
    print("=" * 80)
    print("SYSTEM PROMPT (Règles globales non négociables)")
    print("=" * 80)
    
    system_prompt = build_system_prompt()
    
    print(f"\n📊 Statistiques:")
    print(f"   - Longueur: {len(system_prompt)} caractères")
    print(f"   - Version: {PROMPT_VERSION}")
    print(f"   - Marqueur: {PROMPT_SENTINEL}")
    
    print(f"\n📝 Contenu (premiers 1000 caractères):")
    print("-" * 80)
    print(system_prompt[:1000])
    print("...\n")


def demo_user_prompt(field_key: str = "PROFESSION"):
    """Montre un USER PROMPT pour un champ spécifique"""
    print("=" * 80)
    print(f"USER PROMPT (Champ: {field_key})")
    print("=" * 80)
    
    if field_key not in FIELD_SPECS_V2:
        print(f"❌ Champ {field_key} non trouvé")
        return
    
    spec = FIELD_SPECS_V2[field_key]
    
    # Exemple de sources RAG
    fake_sources = f"""
[Source 1] Actuellement en recherche d'emploi depuis 3 mois.
Dernier poste : Agent administratif dans une PME du secteur logistique.
Contrat CDI à temps plein (35h/semaine).

[Source 2] Missions principales :
- Gestion administrative quotidienne
- Saisie de données et mise à jour de fichiers Excel
- Accueil téléphonique
- Support aux équipes opérationnelles

[Source 3] Environnement de travail :
- Équipe de 5 personnes
- Bureau ouvert (open space)
- Horaires fixes 8h30-17h30
"""
    
    user_prompt = build_user_prompt(
        field_spec=spec,
        sources=fake_sources,
        sources_count=3
    )
    
    print(f"\n📊 Statistiques:")
    print(f"   - Type: {spec.field_type}")
    print(f"   - Max chars: {spec.max_chars}")
    print(f"   - Require sources: {spec.require_sources}")
    print(f"   - Longueur prompt: {len(user_prompt)} caractères")
    
    print(f"\n📝 Contenu complet:")
    print("-" * 80)
    print(user_prompt)
    print("-" * 80)


def demo_combined_prompt():
    """Montre le prompt complet (SYSTEM + USER) qui serait envoyé au LLM"""
    print("\n" + "=" * 80)
    print("PROMPT COMPLET (SYSTEM + USER)")
    print("=" * 80)
    
    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(
        field_spec=FIELD_SPECS_V2["PROFESSION"],
        sources="[Test] Employé comme technicien depuis 2 ans.",
        sources_count=1
    )
    
    combined = system_prompt + "\n\n" + user_prompt
    
    print(f"\n📊 Statistiques:")
    print(f"   - Longueur totale: {len(combined)} caractères")
    print(f"   - Longueur SYSTEM: {len(system_prompt)} caractères")
    print(f"   - Longueur USER: {len(user_prompt)} caractères")
    
    # Test de validation
    print(f"\n🔍 Validation:")
    try:
        validate_prompt_has_sentinel(combined)
        print(f"   ✅ Marqueur sentinel présent: {PROMPT_SENTINEL}")
        print(f"   ✅ Prompt valide et prêt à être envoyé au LLM")
    except ValueError as e:
        print(f"   ❌ Erreur de validation: {e}")


def demo_all_field_types():
    """Montre des exemples pour chaque type de champ"""
    print("\n" + "=" * 80)
    print("EXEMPLES PAR TYPE DE CHAMP")
    print("=" * 80)
    
    examples = {
        "narrative": "PROFESSION",
        "list": "RESSOURCES_MOTIVATIONNELLES",
        "enum": "FRANCAIS_POSITIONNEMENT_DE_NIVEAU"
    }
    
    for field_type, field_key in examples.items():
        print(f"\n📋 Type: {field_type.upper()} - Exemple: {field_key}")
        print("-" * 80)
        
        spec = FIELD_SPECS_V2[field_key]
        user_prompt = build_user_prompt(
            field_spec=spec,
            sources="[Test] Source exemple pour démonstration.",
            sources_count=1
        )
        
        # Extraire juste les règles de réponse
        if "RÈGLES DE RÉPONSE:" in user_prompt:
            rules = user_prompt.split("RÈGLES DE RÉPONSE:")[1]
            print("RÈGLES SPÉCIFIQUES:")
            print(rules[:400] + "...")


def main():
    """Démonstration complète du système de prompt wrapper"""
    print("\n🎯 DÉMONSTRATION DU SYSTÈME DE PROMPT WRAPPER V1")
    print("Conforme à prompt.md - Garantit la cohérence des prompts LLM\n")
    
    # 1. SYSTEM prompt
    demo_system_prompt()
    
    input("\n[Appuyez sur Entrée pour continuer...]")
    
    # 2. USER prompt (narratif)
    demo_user_prompt("PROFESSION")
    
    input("\n[Appuyez sur Entrée pour continuer...]")
    
    # 3. USER prompt (liste)
    demo_user_prompt("RESSOURCES_MOTIVATIONNELLES")
    
    input("\n[Appuyez sur Entrée pour continuer...]")
    
    # 4. USER prompt (enum)
    demo_user_prompt("FRANCAIS_POSITIONNEMENT_DE_NIVEAU")
    
    input("\n[Appuyez sur Entrée pour continuer...]")
    
    # 5. Prompt complet
    demo_combined_prompt()
    
    input("\n[Appuyez sur Entrée pour continuer...]")
    
    # 6. Exemples par type
    demo_all_field_types()
    
    print("\n" + "=" * 80)
    print("✅ DÉMONSTRATION TERMINÉE")
    print("=" * 80)
    print(f"\n📋 Résumé:")
    print(f"   - Marqueur sentinel: {PROMPT_SENTINEL}")
    print(f"   - Version: {PROMPT_VERSION}")
    print(f"   - Nombre de champs: {len(FIELD_SPECS_V2)}")
    print(f"   - Types: deterministic, narrative, list, enum")
    print(f"\n💡 Le système garantit que chaque appel LLM:")
    print(f"   1. Contient le marqueur sentinel (validation fail-fast)")
    print(f"   2. Respecte les règles anti-hallucination")
    print(f"   3. Inclut les contraintes de format par type")
    print(f"   4. Délimite clairement les sources (<SOURCES>)")
    print(f"\n🎯 Conforme à: docs/prompt.md")


if __name__ == "__main__":
    main()

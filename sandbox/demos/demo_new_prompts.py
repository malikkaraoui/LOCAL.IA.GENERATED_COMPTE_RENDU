#!/usr/bin/env python3
"""
Script de démonstration des nouveaux prompts LLM
Affiche les instructions pour chaque type de champ
"""

from core.field_specs_v2 import FIELD_SPECS_V2

def show_prompt(field_key: str, max_lines: int = 20):
    """Affiche le prompt d'un champ"""
    if field_key not in FIELD_SPECS_V2:
        print(f"❌ Champ {field_key} non trouvé")
        return
    
    spec = FIELD_SPECS_V2[field_key]
    print(f"\n{'='*80}")
    print(f"📋 {field_key}")
    print(f"{'='*80}")
    print(f"Type: {spec.field_type}")
    print(f"Query: {spec.query}")
    print(f"Max chars: {spec.max_chars}")
    print(f"Max lines: {spec.max_lines}")
    if spec.enum_values:
        print(f"Valeurs enum: {spec.enum_values}")
    print(f"\n📝 Instructions:")
    print("-" * 80)
    
    lines = spec.instructions.split('\n')
    for i, line in enumerate(lines[:max_lines], 1):
        print(line)
    
    if len(lines) > max_lines:
        print(f"... ({len(lines) - max_lines} lignes supplémentaires)")


def main():
    print("🎯 DÉMONSTRATION DES NOUVEAUX PROMPTS LLM")
    print("=" * 80)
    
    # 1. Nouveau champ
    print("\n\n🆕 NOUVEAU CHAMP AJOUTÉ")
    show_prompt("RELATION_A_LA_CARRIERE")
    
    # 2. Exemple narratif avec nouvelle structure
    print("\n\n📝 EXEMPLE CHAMP NARRATIF (nouvelle structure)")
    show_prompt("PROFESSION")
    
    # 3. Exemple liste avec exemples
    print("\n\n📋 EXEMPLE CHAMP LISTE (avec exemples)")
    show_prompt("RESSOURCES_MOTIVATIONNELLES")
    
    # 4. Enum bureautique modifié
    print("\n\n🔢 ENUM BUREAUTIQUE (valeurs modifiées)")
    show_prompt("WORD_EXCEL_POWERPOINT_OUTLOOK_POSITIONNEMENT_DE_NIVEAU", max_lines=30)
    
    # 5. Statistiques finales
    print("\n\n📊 STATISTIQUES")
    print("=" * 80)
    
    by_type = {}
    for spec in FIELD_SPECS_V2.values():
        field_type = spec.field_type
        if field_type not in by_type:
            by_type[field_type] = []
        by_type[field_type].append(spec.key)
    
    for field_type, keys in sorted(by_type.items()):
        print(f"\n{field_type.upper()} ({len(keys)} champs):")
        for key in keys:
            spec = FIELD_SPECS_V2[key]
            extra = ""
            if spec.require_sources:
                extra = " [require_sources]"
            if spec.enum_values:
                extra = f" {spec.enum_values}"
            print(f"  - {key}{extra}")
    
    print("\n" + "=" * 80)
    print(f"✅ Total: {len(FIELD_SPECS_V2)} champs")
    print("=" * 80)


if __name__ == "__main__":
    main()

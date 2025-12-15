#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""CLI utilitaire pour générer answers.json à partir d'un template et d'un payload."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.generate import generate_fields
from core.template_fields import build_field_specs, extract_placeholders_from_docx
from core.location_date import build_location_date


def parse_list(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def write_missing_debug(answers: Dict[str, Any], path: Optional[Path]) -> None:
    if not path:
        return
    missing = {
        key: data["missing_info"]
        for key, data in answers.items()
        if data.get("missing_info")
    }
    if not missing:
        return
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(missing, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Génère answers.json en respectant instructions.md")
    parser.add_argument("--template", required=True, help="Template DOCX avec {{placeholders}}")
    parser.add_argument("--extracted", required=True, help="Payload JSON issu d'extract_sources")
    parser.add_argument("--out", default="out/answers.json", help="Fichier de sortie")
    parser.add_argument("--missing-debug", default="", help="Chemin facultatif pour debug_missing.json")
    parser.add_argument("--model", default="mistral:latest")
    parser.add_argument("--host", default="http://localhost:11434")
    parser.add_argument("--topk", type=int, default=10)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--top_p", type=float, default=0.9)
    parser.add_argument("--chunk-size", type=int, default=1200)
    parser.add_argument("--overlap", type=int, default=200)
    parser.add_argument("--include", default="", help="Filtre include (chemins)")
    parser.add_argument("--exclude", default="", help="Filtre exclude (chemins)")
    parser.add_argument("--debug-dir", default="out/debug", help="Répertoire de traces par champ")
    parser.add_argument("--fields", default="", help="JSON facultatif de overrides de champs")
    parser.add_argument("--name", default="", help="Prénom pour les champs déterministes")
    parser.add_argument("--surname", default="", help="Nom")
    parser.add_argument("--civility", default="Monsieur", help="Monsieur/Madame/Autre")
    parser.add_argument("--location-date", default="", help="Valeur brute pour {{LIEU_ET_DATE}} (déprécié si auto)")
    parser.add_argument("--location-city", default="", help="Lieu à utiliser avec la date du jour (ex: Genève)")
    parser.add_argument("--auto-date", action="store_true", help="Utiliser automatiquement la date du jour pour {{LIEU_ET_DATE}}")
    parser.add_argument("--date-format", default="%d/%m/%Y", help="Format strftime pour la date du jour")
    parser.add_argument("--avs-number", default="", help="Valeur pour {{NUMERO_AVS}} (jamais générée)")
    args = parser.parse_args()

    template_path = Path(args.template).expanduser().resolve()
    placeholders = extract_placeholders_from_docx(template_path)
    if not placeholders:
        raise SystemExit("Aucun champ {{...}} détecté dans le template.")

    payload = json.loads(Path(args.extracted).expanduser().read_text(encoding="utf-8"))
    custom_fields = None
    if args.fields:
        custom_fields = json.loads(Path(args.fields).expanduser().read_text(encoding="utf-8"))

    fields = build_field_specs(placeholders, custom_fields)
    location_date_value = build_location_date(
        args.location_city,
        args.location_date,
        auto_date=args.auto_date,
        date_format=args.date_format,
    )

    deterministic = {
        "MONSIEUR_OU_MADAME": args.civility,
        "NAME": args.name,
        "SURNAME": args.surname,
        "LIEU_ET_DATE": location_date_value,
        "NUMERO_AVS": args.avs_number,
    }

    answers = generate_fields(
        payload,
        model=args.model,
        host=args.host,
        topk=args.topk,
        temperature=args.temperature,
        top_p=args.top_p,
        include_filters=parse_list(args.include),
        exclude_filters=parse_list(args.exclude),
        debug_dir=Path(args.debug_dir),
        fields=fields,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        deterministic_values=deterministic,
    )

    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(answers, ensure_ascii=False, indent=2), encoding="utf-8")

    missing_debug = Path(args.missing_debug).expanduser() if args.missing_debug else None
    write_missing_debug(answers, missing_debug)

    print(f"✅ answers.json -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Rendu CLI basé sur les fonctions core.render."""

from __future__ import annotations

import argparse
from pathlib import Path

from core.render import render_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Rend un DOCX à partir d'un answers.json")
    parser.add_argument("--template", required=True, help="Chemin du template DOCX")
    parser.add_argument("--answers", required=True, help="answers.json généré")
    parser.add_argument("--output", required=True, help="Chemin du DOCX de sortie")
    parser.add_argument("--name", default="", help="Prénom")
    parser.add_argument("--surname", default="", help="Nom")
    parser.add_argument("--civility", default="Monsieur", help="Civilité")
    parser.add_argument("--location-date", default="", help="Valeur pour {{LIEU_ET_DATE}}")
    args = parser.parse_args()

    render_report(
        template=args.template,
        answers=args.answers,
        output=args.output,
        name=args.name,
        surname=args.surname,
        civility=args.civility,
        location_date=args.location_date,
    )
    print(f"OK: rendu DOCX -> {Path(args.output).expanduser().resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

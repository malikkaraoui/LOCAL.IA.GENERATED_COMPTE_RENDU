"""Debug local: vérifier extraction + détection AVS sur un dossier client.

Usage:
  .venv/bin/python tools/debug_avs_detect.py "CLIENTS/KARAOUI Malik/sources"

Note: ce script n'affiche JAMAIS le numéro AVS en clair. Il masque les chiffres.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Permet d'importer les modules du repo sans installation.
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.extract_sources import extract_one, walk_files
from core.avs import detect_avs_number


def mask_digits(s: str) -> str:
    return "".join("X" if ch.isdigit() else ch for ch in s)


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python tools/debug_avs_detect.py <dir_to_scan>")
        return 2

    root = Path(sys.argv[1]).expanduser().resolve()
    print("scan dir exists:", root.exists(), root)
    if not root.exists():
        return 2

    files = walk_files(root)
    print("file count:", len(files))

    docs = []
    for p in files:
        if p.suffix.lower() == ".txt":
            d = extract_one(p, enable_soffice=False)
            if d.text:
                docs.append({"path": d.path, "ext": d.ext, "text": d.text, "pages": d.pages})

    print("txt docs with text:", len(docs))

    payload = {"documents": docs}
    avs = detect_avs_number(payload)

    # Compteurs
    n_756 = sum(1 for d in docs if "756" in d["text"])
    n_avs_word = sum(1 for d in docs if ("AVS" in d["text"] or "avs" in d["text"]))

    print("docs containing '756':", n_756)
    print("docs containing 'AVS/avs':", n_avs_word)

    if avs:
        print("detect_avs_number: <FOUND>")
        print("normalized (masked):", mask_digits(avs))
        return 0

    print("detect_avs_number: <NOT FOUND>")

    # Montrer un extrait masqué autour d'une occurrence de '756' si présente
    for d in docs:
        t = d["text"]
        i = t.find("756")
        if i != -1:
            snippet = t[max(0, i - 60) : i + 60]
            print("sample around '756' in", Path(d["path"]).name)
            print(mask_digits(snippet))
            break

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

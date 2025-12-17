"""Branding DOCX (entête + pied de page).

Ce module met à jour un template DOCX en remplaçant des placeholders `{{...}}` dans les headers,
et en remplaçant optionnellement un logo d'entête et/ou de pied de page.

Important:
- La mécanique de modification DOCX (zip + XML + relations images) est volontairement conservée.
- Ce module est conçu pour être appelé depuis le backend (FastAPI) sans exécution via terminal.
"""
from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path
from typing import Dict, Optional, Tuple, Union
from xml.sax.saxutils import escape as xml_escape

from lxml import etree as ET  # type: ignore
from PIL import Image  # type: ignore


PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
REL = f"{{{PKG_REL_NS}}}Relationship"


def _build_mapping(cfg: dict) -> Dict[str, str]:
    """
    Construit le mapping final (clés = noms des placeholders dans le DOCX).
    Supporte soit les champs combinés (RUE_NUMERO / VILLE_CP),
    soit les champs séparés (RUE+NUMERO / VILLE+CP).
    """

    def get_str(key: str) -> str:
        v = cfg.get(key, "")
        return "" if v is None else str(v)

    # champs "simples"
    titre = get_str("TITRE_DOCUMENT")
    societe = get_str("SOCIETE")
    tel = get_str("TEL")
    email = get_str("EMAIL")

    # champs combinés possibles
    rue_numero = get_str("RUE_NUMERO")
    if not rue_numero.strip():
        rue = get_str("RUE")
        numero = get_str("NUMERO")
        rue_numero = " ".join([x for x in [rue.strip(), numero.strip()] if x])

    ville_cp = get_str("VILLE_CP")
    if not ville_cp.strip():
        ville = get_str("VILLE")
        cp = get_str("CP")
        ville_cp = " ".join([x for x in [ville.strip(), cp.strip()] if x])

    mapping = {
        "TITRE_DOCUMENT": titre,
        "SOCIETE": societe,
        "RUE_NUMERO": rue_numero,
        "VILLE_CP": ville_cp,
        "TEL": tel,
        "EMAIL": email,
    }
    return mapping


def _replace_placeholders_in_xml(xml_text: str, mapping: Dict[str, str]) -> str:
    """
    Remplace {{KEY}} ou {{ KEY }} dans un XML Word.
    IMPORTANT: on XML-escape les valeurs pour ne pas casser le XML.
    """
    out = xml_text
    for key, raw_val in mapping.items():
        val = xml_escape(raw_val or "")
        pattern = re.compile(r"\{\{\s*" + re.escape(key) + r"\s*\}\}")
        out = pattern.sub(val, out)
    return out


def _find_parts(z: zipfile.ZipFile, kind: str) -> Tuple[list[str], list[str]]:
    """
    Retourne:
      - la liste des XML (word/{kind}*.xml)
      - la liste des rels correspondants (word/_rels/{kind}*.xml.rels)
    kind ∈ { 'header', 'footer' }
    """
    if kind not in {"header", "footer"}:
        raise ValueError("kind must be 'header' or 'footer'")
    xmls = sorted([n for n in z.namelist() if re.fullmatch(rf"word/{kind}\d+\.xml", n)])
    rels = sorted([n for n in z.namelist() if re.fullmatch(rf"word/_rels/{kind}\d+\.xml\.rels", n)])
    return xmls, rels


def _convert_logo_bytes(logo_path: Path, target_ext: str) -> bytes:
    """Convertit le logo en bytes du format attendu par le fichier cible (png/jpg/tif)."""
    target_ext = target_ext.lower().lstrip(".")
    with Image.open(logo_path) as im:
        # Pour éviter des surprises avec transparence, on conserve si possible en PNG,
        # sinon on convertit en RGB.
        if target_ext in ("jpg", "jpeg", "tif", "tiff"):
            if im.mode in ("RGBA", "LA"):
                bg = Image.new("RGB", im.size, (255, 255, 255))
                bg.paste(im, mask=im.split()[-1])
                im2 = bg
            else:
                im2 = im.convert("RGB") if im.mode != "RGB" else im
        else:
            im2 = im  # PNG ok en RGBA

        buf = io.BytesIO()
        if target_ext in ("tif", "tiff"):
            im2.save(buf, format="TIFF", compression="tiff_deflate")
        elif target_ext in ("jpg", "jpeg"):
            im2.save(buf, format="JPEG", quality=95)
        elif target_ext == "png":
            im2.save(buf, format="PNG", optimize=True)
        else:
            im2.save(buf, format="PNG", optimize=True)
        return buf.getvalue()


def _pick_image_targets_from_rels(rels_xml: bytes) -> list[str]:
    """Lit un {header|footer}*.xml.rels et retourne la liste des Targets des relations image."""
    root = ET.fromstring(rels_xml)
    targets = []
    for r in root.findall(REL):
        rtype = r.get("Type", "")
        if rtype.endswith("/image"):
            tgt = r.get("Target")
            if tgt:
                targets.append(tgt)
    return targets


def update_docx_header(
    template_docx: Path,
    output_docx: Path,
    mapping: Dict[str, str],
    logo_path: Optional[Path] = None,
    footer_logo_path: Optional[Path] = None,
    replace_logo_in_all_headers: bool = True,
    replace_logo_in_all_footers: bool = True,
) -> None:
    """
    Met à jour le(s) header(s) (placeholders + logo header optionnel) et le logo du footer (optionnel).

    Heuristique: on remplace l'image uniquement si le header/footer ne contient qu'UNE seule relation image
    (ça évite de casser d'autres pictos/logos).
    """
    if not template_docx.exists():
        raise FileNotFoundError(template_docx)
    if logo_path and not logo_path.exists():
        raise FileNotFoundError(logo_path)
    if footer_logo_path and not footer_logo_path.exists():
        raise FileNotFoundError(footer_logo_path)

    with zipfile.ZipFile(template_docx, "r") as zin:
        headers, header_rels = _find_parts(zin, "header")
        footers, footer_rels = _find_parts(zin, "footer")

        # XML modifiés (uniquement headers; on ne touche pas au body)
        new_xml: Dict[str, bytes] = {}
        for h in headers:
            xml = zin.read(h).decode("utf-8", errors="ignore")
            xml2 = _replace_placeholders_in_xml(xml, mapping)
            if xml2 != xml:
                new_xml[h] = xml2.encode("utf-8")

        # Images à remplacer
        image_replacements: Dict[str, bytes] = {}

        # --- Logo HEADER
        if logo_path:
            rels_to_process = header_rels if replace_logo_in_all_headers else [r for r in header_rels if r.endswith("header2.xml.rels")]
            for rels_name in rels_to_process:
                rels_bytes = zin.read(rels_name)
                targets = _pick_image_targets_from_rels(rels_bytes)
                if len(targets) != 1:
                    continue
                media_path = "word/" + targets[0]
                if media_path not in zin.namelist():
                    continue
                ext = Path(media_path).suffix
                image_replacements[media_path] = _convert_logo_bytes(logo_path, ext)

        # --- Logo FOOTER
        if footer_logo_path:
            rels_to_process = footer_rels if replace_logo_in_all_footers else [r for r in footer_rels if r.endswith("footer1.xml.rels")]
            for rels_name in rels_to_process:
                rels_bytes = zin.read(rels_name)
                targets = _pick_image_targets_from_rels(rels_bytes)
                if len(targets) != 1:
                    continue
                media_path = "word/" + targets[0]
                if media_path not in zin.namelist():
                    continue
                ext = Path(media_path).suffix
                image_replacements[media_path] = _convert_logo_bytes(footer_logo_path, ext)

        # Écrit le nouveau docx
        output_docx.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_docx, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                name = item.filename
                if name in new_xml:
                    zout.writestr(item, new_xml[name])
                elif name in image_replacements:
                    zout.writestr(item, image_replacements[name])
                else:
                    zout.writestr(item, zin.read(name))


def apply_branding_to_docx(
    template_docx: Union[str, Path],
    output_docx: Union[str, Path],
    fields: Dict[str, object],
    logo_header: Optional[Union[str, Path]] = None,
    logo_footer: Optional[Union[str, Path]] = None,
    *,
    replace_logo_in_all_headers: bool = True,
    replace_logo_in_all_footers: bool = True,
) -> Path:
    """Applique le branding (champs + logos) sur un template DOCX.

    Args:
        template_docx: chemin du template source (non modifié).
        output_docx: chemin du docx résultat à écrire.
        fields: dictionnaire de valeurs saisies par l'utilisateur.
            Clés attendues (case-insensitive):
              - titre_document, societe, tel, email
              - rue, numero, ville, cp
            ou directement: TITRE_DOCUMENT, SOCIETE, TEL, EMAIL, RUE_NUMERO, VILLE_CP.
        logo_header: fichier image du logo header (optionnel).
        logo_footer: fichier image du logo footer (optionnel).
    """

    tpl = Path(template_docx)
    out = Path(output_docx)

    # Normaliser les clés (case-insensitive) sans changer la mécanique _build_mapping.
    normalized: Dict[str, object] = {}
    for k, v in (fields or {}).items():
        if k is None:
            continue
        normalized[str(k).strip().upper()] = v

    # Aliases pour les champs fournis en snake_case depuis l'API
    # (ex: titre_document -> TITRE_DOCUMENT)
    alias_map = {
        "TITRE_DOCUMENT": ["TITRE_DOCUMENT", "TITRE", "TITRE-DOCUMENT", "TITRE_DOCUMENT"],
        "SOCIETE": ["SOCIETE", "SOCIÉTÉ", "COMPANY"],
        "TEL": ["TEL", "TELEPHONE", "TÉL", "TÉLÉPHONE"],
        "EMAIL": ["EMAIL", "E-MAIL"],
        "RUE": ["RUE"],
        "NUMERO": ["NUMERO", "NUMÉRO"],
        "VILLE": ["VILLE"],
        "CP": ["CP", "CODE_POSTAL"],
        "RUE_NUMERO": ["RUE_NUMERO"],
        "VILLE_CP": ["VILLE_CP"],
    }

    # Si l'appelant a envoyé des clés snake_case, elles auront été upper() (ex: TITRE_DOCUMENT ok).
    # On applique juste un fallback de correspondance (pas de transformation invasive).
    cfg: Dict[str, object] = {}
    for out_key, candidates in alias_map.items():
        for c in candidates:
            if c in normalized:
                cfg[out_key] = normalized[c]
                break

    mapping = _build_mapping(cfg)
    header_logo_path = Path(logo_header) if logo_header else None
    footer_logo_path = Path(logo_footer) if logo_footer else None

    update_docx_header(
        template_docx=tpl,
        output_docx=out,
        mapping=mapping,
        logo_path=header_logo_path,
        footer_logo_path=footer_logo_path,
        replace_logo_in_all_headers=replace_logo_in_all_headers,
        replace_logo_in_all_footers=replace_logo_in_all_footers,
    )
    return out

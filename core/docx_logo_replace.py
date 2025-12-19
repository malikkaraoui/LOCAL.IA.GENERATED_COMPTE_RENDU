"""Remplacement robuste de logos dans un DOCX (OpenXML) via placeholders Alt Text.

Principe (important):
- Le template fixe la géométrie (Logo Box) dans header/footer.
- Le code ne modifie JAMAIS les coordonnées/dimensions dans les XML.
- On remplace uniquement le fichier image dans word/media/ identifié par le tag.

Support:
- DrawingML: wp:docPr/@descr ou @title + a:blip r:embed
- VML: v:imagedata r:id + tag sur o:title/o:descr/alt (shape ou imagedata)

Ce module est utilisé par core.docx_branding.
"""

from __future__ import annotations

import io
import logging
import posixpath
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

from lxml import etree as ET  # type: ignore

from core.logo_processing import LogoNormalizeConfig, emu_to_px, normalize_logo_to_bytes

logger = logging.getLogger(__name__)


# Namespaces courants Word
NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "v": "urn:schemas-microsoft-com:vml",
    "o": "urn:schemas-microsoft-com:office:office",
}

PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
REL = f"{{{PKG_REL_NS}}}Relationship"


class MissingLogoPlaceholderError(ValueError):
    """Placeholder LOGO_HEADER/FOOTER introuvable dans les headers/footers du template."""


@dataclass(frozen=True)
class LogoReplaceHit:
    part_name: str  # word/headerX.xml ou word/footerX.xml
    rels_name: str  # word/_rels/headerX.xml.rels
    rid: str
    tag: str
    box_px: Optional[Tuple[int, int]]


def strip_logo_crop_in_part_xml(xml_bytes: bytes, *, tag: str) -> Tuple[bytes, bool]:
    """Supprime le rognage (crop) stocké dans le XML Word pour un placeholder logo.

    Pourquoi:
    - Word peut enregistrer un crop sur l'image placeholder (DrawingML: <a:srcRect .../>).
    - Si on remplace uniquement word/media/..., Word continue d'appliquer ce crop au nouveau logo.

    Contrat:
    - On ne modifie PAS la géométrie/position (extent/offset/anchor...).
    - On enlève uniquement les informations de rognage:
      - DrawingML: <a:srcRect .../>
      - VML: attributs croptop/cropleft/cropbottom/cropright sur v:imagedata
    """

    if not xml_bytes:
        return xml_bytes, False

    root = ET.fromstring(xml_bytes)
    changed = False

    # DrawingML: crop via a:srcRect (souvent dans pic:blipFill)
    for docpr in root.findall(".//wp:docPr", namespaces=NS):
        if not _element_attr_equals_tag(docpr, tag):
            continue

        container = _find_nearest_ancestor(docpr, localnames=("inline", "anchor"), ns=NS["wp"])
        if container is None:
            continue

        # Retirer tous les a:srcRect dans ce drawing
        for src_rect in container.findall(".//a:srcRect", namespaces=NS):
            parent = src_rect.getparent()
            if parent is None:
                continue
            parent.remove(src_rect)
            changed = True

    # VML: rognage stocké en attributs sur v:imagedata
    for imagedata in root.findall(".//v:imagedata", namespaces=NS):
        rid = imagedata.get(f"{{{NS['r']}}}id")
        if not rid:
            continue

        shape = _find_nearest_ancestor(imagedata, localnames=("shape",), ns=NS["v"])
        tagged = _element_attr_equals_tag(imagedata, tag) or (shape is not None and _element_attr_equals_tag(shape, tag))
        if not tagged:
            continue

        for attr in ("croptop", "cropleft", "cropbottom", "cropright"):
            if attr in imagedata.attrib:
                del imagedata.attrib[attr]
                changed = True

    if not changed:
        return xml_bytes, False

    out = ET.tostring(root, encoding="UTF-8", xml_declaration=True)
    return out, True


def _iter_parts(z: zipfile.ZipFile, kind: str) -> List[str]:
    if kind not in {"header", "footer"}:
        raise ValueError("kind must be 'header' or 'footer'")
    return sorted([n for n in z.namelist() if re.fullmatch(rf"word/{kind}\d+\.xml", n)])


def _rels_for_part(part_name: str) -> str:
    # word/header1.xml -> word/_rels/header1.xml.rels
    p = Path(part_name)
    return str(Path("word") / "_rels" / (p.name + ".rels"))


def _element_attr_equals_tag(el: ET._Element, tag: str) -> bool:
    if not tag:
        return False
    # docPr uses descr/title without namespace; VML often uses o:title/o:descr.
    for key in ("descr", "title", "alt"):
        v = el.get(key)
        if v is not None and v.strip() == tag:
            return True
    for ns_key in ("o",):
        for key in ("title", "descr"):
            v = el.get(f"{{{NS[ns_key]}}}{key}")
            if v is not None and v.strip() == tag:
                return True
    return False


def _find_nearest_ancestor(el: ET._Element, localnames: Sequence[str], ns: str) -> Optional[ET._Element]:
    cur = el
    while cur is not None:
        if ET.QName(cur).namespace == ns and ET.QName(cur).localname in localnames:
            return cur
        cur = cur.getparent()
    return None


def _extract_box_px_from_drawing(container: ET._Element, *, dpi: int) -> Optional[Tuple[int, int]]:
    # 1) wp:extent (le plus direct)
    extent = container.find(".//wp:extent", namespaces=NS)
    if extent is not None:
        cx = extent.get("cx")
        cy = extent.get("cy")
        if cx and cy:
            try:
                return (emu_to_px(int(cx), dpi), emu_to_px(int(cy), dpi))
            except Exception:
                pass

    # 2) a:ext (fallback)
    aext = container.find(".//a:ext", namespaces=NS)
    if aext is not None:
        cx = aext.get("cx")
        cy = aext.get("cy")
        if cx and cy:
            try:
                return (emu_to_px(int(cx), dpi), emu_to_px(int(cy), dpi))
            except Exception:
                pass

    return None


def _extract_box_px_from_vml(shape: ET._Element, *, dpi: int) -> Optional[Tuple[int, int]]:
    # Word VML style: width:123pt;height:45pt
    style = shape.get("style") or ""
    m_w = re.search(r"width\s*:\s*([0-9.]+)\s*(pt|in|cm|mm|px)", style)
    m_h = re.search(r"height\s*:\s*([0-9.]+)\s*(pt|in|cm|mm|px)", style)
    if not (m_w and m_h):
        return None

    def to_px(val: float, unit: str) -> int:
        if unit == "px":
            return max(1, int(round(val)))
        if unit == "in":
            return max(1, int(round(val * dpi)))
        if unit == "pt":
            return max(1, int(round((val / 72.0) * dpi)))
        if unit == "cm":
            return max(1, int(round((val / 2.54) * dpi)))
        if unit == "mm":
            return max(1, int(round((val / 25.4) * dpi)))
        return max(1, int(round(val)))

    try:
        w_px = to_px(float(m_w.group(1)), m_w.group(2))
        h_px = to_px(float(m_h.group(1)), m_h.group(2))
        return (w_px, h_px)
    except Exception:
        return None


def _iter_logo_hits_in_part(xml_bytes: bytes, *, part_name: str, tag: str, dpi: int) -> Iterator[LogoReplaceHit]:
    root = ET.fromstring(xml_bytes)

    # DrawingML: match wp:docPr
    for docpr in root.findall(".//wp:docPr", namespaces=NS):
        if not (_element_attr_equals_tag(docpr, tag)):
            continue

        container = _find_nearest_ancestor(docpr, localnames=("inline", "anchor"), ns=NS["wp"])
        if container is None:
            continue

        blip = container.find(".//a:blip", namespaces=NS)
        if blip is None:
            continue

        rid = blip.get(f"{{{NS['r']}}}embed")
        if not rid:
            continue

        box_px = _extract_box_px_from_drawing(container, dpi=dpi)
        yield LogoReplaceHit(
            part_name=part_name,
            rels_name=_rels_for_part(part_name),
            rid=rid,
            tag=tag,
            box_px=box_px,
        )

    # VML: match v:imagedata r:id
    for imagedata in root.findall(".//v:imagedata", namespaces=NS):
        rid = imagedata.get(f"{{{NS['r']}}}id")
        if not rid:
            continue

        shape = _find_nearest_ancestor(imagedata, localnames=("shape",), ns=NS["v"])
        tagged = _element_attr_equals_tag(imagedata, tag) or (shape is not None and _element_attr_equals_tag(shape, tag))
        if not tagged:
            continue

        box_px = _extract_box_px_from_vml(shape, dpi=dpi) if shape is not None else None
        yield LogoReplaceHit(
            part_name=part_name,
            rels_name=_rels_for_part(part_name),
            rid=rid,
            tag=tag,
            box_px=box_px,
        )


def _normalize_target_path(z: zipfile.ZipFile, target: str, *, media_basename_fallback: bool = True) -> Optional[str]:
    """Retourne un chemin interne zip (ex: word/media/image1.png).

    Word stocke généralement les images sous word/media/.
    Les Targets peuvent être relatifs (media/..., ../media/...).
    """

    target = (target or "").replace("\\", "/").lstrip("/")
    if not target:
        return None

    # Base = 'word/' (source part headerX.xml est dans word/)
    cand = posixpath.normpath(posixpath.join("word", target))
    if cand in z.namelist():
        return cand

    # Fallback: essayer word/media/<basename>
    if media_basename_fallback:
        base = posixpath.basename(target)
        if base:
            cand2 = posixpath.join("word", "media", base)
            if cand2 in z.namelist():
                return cand2

    # Dernier fallback: si la target est déjà complète
    if target in z.namelist():
        return target

    return None


def _resolve_target_from_rels(rels_bytes: bytes, rid: str) -> Optional[str]:
    root = ET.fromstring(rels_bytes)
    for rel in root.findall(REL):
        if rel.get("Id") != rid:
            continue
        rtype = rel.get("Type", "")
        if not rtype.endswith("/image"):
            # On cherche uniquement les relations image
            continue
        return rel.get("Target")
    return None


def build_logo_image_replacements(
    zin: zipfile.ZipFile,
    *,
    tag: str,
    logo_bytes: bytes,
    cfg: LogoNormalizeConfig,
    kinds: Sequence[str] = ("header", "footer"),
    limit_to_first_part_per_kind: bool = False,
) -> Dict[str, bytes]:
    """Retourne un mapping {media_path_in_zip: normalized_image_bytes}.

    Ne modifie pas le zip.
    """

    parts: List[str] = []
    for kind in kinds:
        kparts = _iter_parts(zin, kind)
        if limit_to_first_part_per_kind and kparts:
            kparts = [kparts[0]]
        parts.extend(kparts)

    hits: List[LogoReplaceHit] = []
    for part in parts:
        try:
            xml_bytes = zin.read(part)
        except KeyError:
            continue
        hits.extend(list(_iter_logo_hits_in_part(xml_bytes, part_name=part, tag=tag, dpi=cfg.dpi)))

    if not hits:
        raise MissingLogoPlaceholderError(
            f"Placeholder '{tag}' introuvable dans les headers/footers du template. "
            "Dans Word: sélectionne l'image placeholder → 'Texte de remplacement' → "
            f"mettre '{tag}' (dans le header/footer approprié, y compris first/even/odd si activé)."
        )

    # Résoudre rId -> Target -> media path
    desired_by_media: Dict[str, Tuple[int, int]] = {}
    for h in hits:
        if h.rels_name not in zin.namelist():
            logger.warning("rels manquant pour %s: %s", h.part_name, h.rels_name)
            continue
        rels_bytes = zin.read(h.rels_name)
        target = _resolve_target_from_rels(rels_bytes, h.rid)
        if not target:
            logger.warning("rId non résolu (%s) dans %s", h.rid, h.rels_name)
            continue
        media_path = _normalize_target_path(zin, target)
        if not media_path:
            logger.warning("Target image introuvable dans zip: %s (part=%s)", target, h.part_name)
            continue

        # Taille cible: box_px si dispo, sinon fallback basé sur une box 6.25x2.0cm à dpi
        if h.box_px is not None:
            box_w, box_h = h.box_px
        else:
            # 6.25cm x 2cm -> inches * dpi
            box_w = max(1, int(round((6.25 / 2.54) * cfg.dpi)))
            box_h = max(1, int(round((2.00 / 2.54) * cfg.dpi)))

        prev = desired_by_media.get(media_path)
        if prev is None:
            desired_by_media[media_path] = (box_w, box_h)
        else:
            # Prendre la taille max (qualité) si le même target est utilisé par plusieurs headers/footers.
            desired_by_media[media_path] = (max(prev[0], box_w), max(prev[1], box_h))

        logger.info(
            "logo hit: tag=%s part=%s rid=%s target=%s media=%s box_px=%s",
            tag,
            h.part_name,
            h.rid,
            target,
            media_path,
            h.box_px,
        )

    if not desired_by_media:
        raise MissingLogoPlaceholderError(
            f"Placeholder '{tag}' trouvé mais aucune relation image n'a pu être résolue. "
            "Vérifie que l'image placeholder est bien une image Word (pas une forme sans image) "
            "et qu'elle référence un fichier dans word/media/."
        )

    replacements: Dict[str, bytes] = {}
    for media_path, (w_px, h_px) in desired_by_media.items():
        ext = Path(media_path).suffix.lower() or ".png"
        replacements[media_path] = normalize_logo_to_bytes(
            logo_bytes,
            target_w_px=w_px,
            target_h_px=h_px,
            output_ext=ext,
            cfg=cfg,
        )
    return replacements

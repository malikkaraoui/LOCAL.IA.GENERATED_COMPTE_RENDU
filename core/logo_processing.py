"""Normalisation d'images logo pour insertion stable dans des templates DOCX.

But:
- Convertir un logo uploadé (formats variés, marges, transparence) en une image
  prête à être injectée dans une 'Logo Box' Word sans toucher à la géométrie.

Le template Word fixe la box (position + taille). Le code ne fait que produire
un bitmap aux bonnes dimensions et remplacer le fichier dans word/media/.
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass
from typing import Literal, Optional, Tuple

from PIL import Image, ImageChops, ImageOps  # type: ignore


Mode = Literal["contain"]
Background = Literal["transparent", "white"]

Align = Literal["left", "center"]
VAlign = Literal["center"]


@dataclass(frozen=True)
class LogoNormalizeConfig:
    # V3 “béton”: un seul mode autorisé.
    mode: Mode = "contain"

    # V3 “béton”: alignements safe (le template Word fixe la géométrie; on n'édite pas le XML).
    # - left: collage à gauche (utile pour l'entête: à gauche de la box)
    # - center: centré dans la box (utile pour le pied de page)
    align: Align = "left"
    valign: VAlign = "center"

    # Compat: trim=True conserve l'ancien comportement (transparent + quasi-blanc)
    # mais on expose aussi des flags séparés pour un contrôle plus fin.
    trim: bool = True
    trim_transparent: bool = True
    trim_near_white: bool = True
    padding_pct: float = 0.08
    background: Background = "transparent"
    dpi: int = 300

    # Trim quasi-blanc
    near_white_threshold: int = 245  # 0..255; plus haut = moins agressif
    alpha_threshold: int = 8
    # garde-fou: si trop de pixels supprimés -> fallback (spéc V3: 60%)
    max_trim_removed_pct: float = 0.60

    # Si le trim retire beaucoup de surface, on l'accepte quand même si la surface restante
    # reste suffisamment "significative" (ex: logo petit au centre d'un grand fond blanc).
    # Cela évite de désactiver le trim near-white sur des logos JPEG avec grosses marges.
    min_remaining_area_pct: float = 0.05


def emu_to_px(emu: int, dpi: int) -> int:
    # 1 inch = 914400 EMU
    inches = float(emu) / 914_400.0
    return max(1, int(round(inches * float(dpi))))


def _safe_bbox(bbox: Optional[Tuple[int, int, int, int]], size: Tuple[int, int]) -> Tuple[int, int, int, int]:
    if bbox is None:
        return (0, 0, size[0], size[1])
    x0, y0, x1, y1 = bbox
    x0 = max(0, min(size[0], x0))
    y0 = max(0, min(size[1], y0))
    x1 = max(0, min(size[0], x1))
    y1 = max(0, min(size[1], y1))
    if x1 <= x0 or y1 <= y0:
        return (0, 0, size[0], size[1])
    return (x0, y0, x1, y1)


def _trim_transparent(im: Image.Image, *, alpha_threshold: int) -> Image.Image:
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    alpha = im.split()[-1]
    # Faire un masque binaire alpha>threshold pour éviter d'inclure des bords quasi-transparents.
    mask = alpha.point(lambda a: 255 if a > alpha_threshold else 0)
    bbox = mask.getbbox()
    bbox = _safe_bbox(bbox, im.size)
    return im.crop(bbox)


def _trim_near_white(im: Image.Image, *, near_white_threshold: int, alpha_threshold: int) -> Image.Image:
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    r, g, b, a = im.split()

    # Marquer comme "background" les pixels (1) presque blancs ET (2) opaques.
    # On conserve l'info alpha pour ne pas considérer des zones transparentes comme "blanc".
    def _bg_mask_channel(ch: Image.Image) -> Image.Image:
        return ch.point(lambda x: 255 if x >= near_white_threshold else 0)

    bg_rgb = ImageChops.multiply(ImageChops.multiply(_bg_mask_channel(r), _bg_mask_channel(g)), _bg_mask_channel(b))
    opaque = a.point(lambda x: 255 if x > alpha_threshold else 0)
    bg = ImageChops.multiply(bg_rgb, opaque)

    # Foreground = NOT(bg) mais en gardant aussi les zones transparentes hors calcul.
    fg = ImageChops.invert(bg)
    bbox = fg.getbbox()
    bbox = _safe_bbox(bbox, im.size)
    return im.crop(bbox)


def _apply_trim_with_guard(im: Image.Image, cfg: LogoNormalizeConfig) -> Image.Image:
    if not cfg.trim:
        return im

    w0, h0 = im.size
    if w0 <= 1 or h0 <= 1:
        return im

    # Pour rester robuste: on applique d'abord le trim transparent si activé.
    im1 = im
    if cfg.trim_transparent:
        im1 = _trim_transparent(im1, alpha_threshold=cfg.alpha_threshold)

    w1, h1 = im1.size
    if w1 <= 1 or h1 <= 1:
        return im1

    if not cfg.trim_near_white:
        return im1

    # 2) Trim quasi-blanc (tentatives) — garde-fou si trop agressif
    # Note: seuil plus bas = plus agressif (on coupe plus), donc on part du seuil demandé
    # puis on le rend moins agressif si nécessaire.
    candidates = [
        int(cfg.near_white_threshold),
        min(255, int(cfg.near_white_threshold) + 5),
        min(255, int(cfg.near_white_threshold) + 10),
    ]

    best = im1
    for thr in candidates:
        im2 = _trim_near_white(im1, near_white_threshold=thr, alpha_threshold=cfg.alpha_threshold)
        w2, h2 = im2.size
        remaining = float(w2 * h2) / float(w1 * h1)
        removed = 1.0 - remaining

        # On accepte si:
        # - le trim n'est pas "trop" agressif, OU
        # - le trim est agressif mais la surface restante reste suffisamment grande
        #   (cas fréquent: gros fond blanc autour d'un logo).
        if removed <= cfg.max_trim_removed_pct or remaining >= cfg.min_remaining_area_pct:
            best = im2
            break

    # Si aucune tentative near-white ne passe le garde-fou, on revient à transparent-only.
    return best


def _make_background(size: Tuple[int, int], background: Background) -> Image.Image:
    if background == "transparent":
        return Image.new("RGBA", size, (0, 0, 0, 0))
    return Image.new("RGBA", size, (255, 255, 255, 255))


def normalize_logo_to_bytes(
    logo_bytes: bytes,
    *,
    target_w_px: int,
    target_h_px: int,
    output_ext: str = ".png",
    cfg: LogoNormalizeConfig = LogoNormalizeConfig(),
) -> bytes:
    """Normalise un logo dans une box (target_w_px x target_h_px) et retourne des bytes.

    - applique exif_transpose (rotation EXIF)
    - trim (transparent + quasi-blanc) + garde-fou
    - padding
    - contain (uniquement)
    - resize LANCZOS
    - encode dans le format correspondant à output_ext
    """

    if not logo_bytes:
        raise ValueError("logo_bytes vide")
    if target_w_px <= 0 or target_h_px <= 0:
        raise ValueError("Dimensions cible invalides")

    output_ext = (output_ext or ".png").lower().strip()
    if not output_ext.startswith("."):
        output_ext = "." + output_ext

    with Image.open(io.BytesIO(logo_bytes)) as im0:
        im0 = ImageOps.exif_transpose(im0)
        im = im0.convert("RGBA")

    im = _apply_trim_with_guard(im, cfg)

    # V3: mode/align/valign safe
    if cfg.mode != "contain":
        raise ValueError("LogoNormalizeConfig.mode doit être 'contain' (mode safe uniquement)")
    if cfg.align not in ("left", "center"):
        raise ValueError("LogoNormalizeConfig.align doit être 'left' ou 'center' (mode safe uniquement)")
    if cfg.valign != "center":
        raise ValueError("LogoNormalizeConfig.valign doit être 'center' (mode safe uniquement)")

    # Inner box avec padding (V3: padding en pixels basé sur min(box_w, box_h))
    pad_pct = max(0.0, min(0.45, float(cfg.padding_pct)))
    pad_px = int(round(float(min(target_w_px, target_h_px)) * pad_pct))
    # On évite de manger la box entière.
    pad_px = max(0, min(pad_px, (min(target_w_px, target_h_px) // 2) - 1))

    inner_w = max(1, target_w_px - 2 * pad_px)
    inner_h = max(1, target_h_px - 2 * pad_px)

    src_w, src_h = im.size
    if src_w <= 0 or src_h <= 0:
        raise ValueError("Image source invalide")

    # V3: contain uniquement (jamais cover / jamais crop)
    scale = min(inner_w / float(src_w), inner_h / float(src_h))

    new_w = max(1, int(round(src_w * scale)))
    new_h = max(1, int(round(src_h * scale)))
    resized = im.resize((new_w, new_h), resample=Image.Resampling.LANCZOS)

    # V3: canvas finale = box Word (ratio identique), puis collage selon l'alignement.
    canvas = _make_background((target_w_px, target_h_px), cfg.background)
    paste_w, paste_h = resized.size
    if cfg.align == "center":
        x = pad_px + max(0, (inner_w - paste_w) // 2)
    else:
        x = pad_px
    # (formule équivalente au centrage dans la box complète, tout en respectant le padding)
    y = pad_px + max(0, (inner_h - paste_h) // 2)
    canvas.paste(resized, (x, y), resized)

    # Encoder selon extension cible
    buf = io.BytesIO()

    if output_ext in (".jpg", ".jpeg"):
        # JPEG ne supporte pas l'alpha: on aplatit sur fond blanc pour éviter un fond noir.
        if canvas.mode == "RGBA":
            bg = Image.new("RGB", canvas.size, (255, 255, 255))
            bg.paste(canvas, mask=canvas.split()[-1])
            out = bg
        else:
            out = canvas.convert("RGB")
        out.save(buf, format="JPEG", quality=95)
    elif output_ext in (".tif", ".tiff"):
        # Word supporte bien TIFF; on aplatit si demandé
        if cfg.background == "white":
            out = canvas.convert("RGB")
        else:
            # Certaines versions de Word gèrent l'alpha TIFF; sinon, Word peut l'ignorer.
            out = canvas
        out.save(buf, format="TIFF", compression="tiff_deflate")
    else:
        # PNG par défaut
        canvas.save(buf, format="PNG", optimize=True)

    return buf.getvalue()

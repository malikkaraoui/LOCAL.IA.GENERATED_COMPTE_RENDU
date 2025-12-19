from __future__ import annotations

import io

from PIL import Image, ImageChops  # type: ignore

from core.logo_processing import LogoNormalizeConfig, normalize_logo_to_bytes


def _bbox_alpha(im: Image.Image, *, alpha_threshold: int = 8) -> tuple[int, int, int, int]:
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    a = im.split()[-1]
    mask = a.point(lambda x: 255 if x > alpha_threshold else 0)
    bbox = mask.getbbox()
    assert bbox is not None
    return bbox


def _make_png_rgba(size: tuple[int, int], *, draw: callable[[Image.Image], None]) -> bytes:
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    draw(im)
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def _make_jpg_rgb(size: tuple[int, int], *, draw: callable[[Image.Image], None], quality: int = 95) -> bytes:
    im = Image.new("RGB", size, (255, 255, 255))
    draw(im)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def test_safe_contain_left_align_square_transparent():
    # Logo carré sur fond transparent
    logo = _make_png_rgba(
        (200, 200),
        draw=lambda im: im.paste(Image.new("RGBA", (120, 120), (0, 200, 0, 255)), (40, 40)),
    )

    box_w, box_h = 400, 200
    cfg = LogoNormalizeConfig(padding_pct=0.08, background="transparent", dpi=300)
    out = normalize_logo_to_bytes(logo, target_w_px=box_w, target_h_px=box_h, output_ext=".png", cfg=cfg)

    with Image.open(io.BytesIO(out)) as im:
        assert im.size == (box_w, box_h)
        bbox = _bbox_alpha(im)

        pad = round(min(box_w, box_h) * cfg.padding_pct)
        # Collé à gauche (dans la box utile)
        assert bbox[0] <= pad + 1

        # Centrage vertical
        cy = (bbox[1] + bbox[3]) / 2.0
        assert abs(cy - (box_h / 2.0)) <= 2.0


def test_safe_contain_left_align_wide_logo_ratio_preserved():
    # Logo très large
    logo = _make_png_rgba(
        (400, 100),
        draw=lambda im: im.paste(Image.new("RGBA", (380, 80), (200, 0, 0, 255)), (10, 10)),
    )

    # Ratio attendu = ratio du contenu utile (après trim), pas du canvas initial.
    with Image.open(io.BytesIO(logo)) as src:
        bb = _bbox_alpha(src)
        expected_ratio = (bb[2] - bb[0]) / float(bb[3] - bb[1])

    box_w, box_h = 300, 300
    cfg = LogoNormalizeConfig(padding_pct=0.08, background="transparent", dpi=300)
    out = normalize_logo_to_bytes(logo, target_w_px=box_w, target_h_px=box_h, output_ext=".png", cfg=cfg)

    with Image.open(io.BytesIO(out)) as im:
        bbox = _bbox_alpha(im)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]

        # Ratio ~= ratio du contenu utile. On accepte une petite tolérance due au resize.
        ratio = w / float(h)
        assert abs(ratio - expected_ratio) <= 0.2

        # Collé à gauche
        pad = round(min(box_w, box_h) * cfg.padding_pct)
        assert bbox[0] <= pad + 1


def test_safe_trim_near_white_jpg_margins_get_removed():
    # JPEG avec grosses marges blanches : on dessine un rectangle sombre au centre.
    logo = _make_jpg_rgb(
        (600, 300),
        draw=lambda im: im.paste(Image.new("RGB", (200, 100), (20, 20, 20)), (200, 100)),
    )

    box_w, box_h = 600, 200

    # Avec trim near-white
    cfg_trim = LogoNormalizeConfig(padding_pct=0.08, background="transparent", dpi=300, trim=True, trim_near_white=True)
    out_trim = normalize_logo_to_bytes(logo, target_w_px=box_w, target_h_px=box_h, output_ext=".png", cfg=cfg_trim)

    # Sans trim near-white (trim transparent n'a pas d'effet sur un JPEG opaque)
    cfg_no = LogoNormalizeConfig(padding_pct=0.08, background="transparent", dpi=300, trim=True, trim_near_white=False)
    out_no = normalize_logo_to_bytes(logo, target_w_px=box_w, target_h_px=box_h, output_ext=".png", cfg=cfg_no)

    with Image.open(io.BytesIO(out_trim)) as im_t, Image.open(io.BytesIO(out_no)) as im_n:
        def bbox_dark(im: Image.Image) -> tuple[int, int, int, int]:
            im = im.convert("RGBA")
            r, g, b, a = im.split()
            # Pixel considéré "contenu" si (alpha>8) ET (max(r,g,b)<200)
            alpha_mask = a.point(lambda x: 255 if x > 8 else 0)
            max_rgb = ImageChops.lighter(ImageChops.lighter(r, g), b)
            dark_mask = max_rgb.point(lambda x: 255 if x < 200 else 0)
            mask = ImageChops.multiply(alpha_mask, dark_mask)
            bbox = mask.getbbox()
            assert bbox is not None
            return bbox

        bt = bbox_dark(im_t)
        bn = bbox_dark(im_n)

        wt = bt[2] - bt[0]
        wn = bn[2] - bn[0]

        # Si on a bien trimmé les marges blanches, le rectangle sombre devrait occuper plus de largeur utile.
        assert wt > wn


def test_safe_no_crop_border_survives():
    # On dessine un cadre (border) pour détecter un éventuel crop.
    def draw_border(im: Image.Image) -> None:
        # rectangle plein + bord 2px
        w, h = im.size
        fill = Image.new("RGBA", (w - 20, h - 20), (0, 120, 200, 255))
        im.paste(fill, (10, 10), fill)
        # bord jaune
        border = Image.new("RGBA", (w - 20, h - 20), (0, 0, 0, 0))
        for x in range(w - 20):
            for y in (0, 1, h - 21, h - 22):
                border.putpixel((x, y), (255, 255, 0, 255))
        for y in range(h - 20):
            for x in (0, 1, w - 21, w - 22):
                border.putpixel((x, y), (255, 255, 0, 255))
        im.paste(border, (10, 10), border)

    logo = _make_png_rgba((220, 120), draw=draw_border)

    box_w, box_h = 500, 180
    cfg = LogoNormalizeConfig(padding_pct=0.08, background="transparent", dpi=300)
    out = normalize_logo_to_bytes(logo, target_w_px=box_w, target_h_px=box_h, output_ext=".png", cfg=cfg)

    with Image.open(io.BytesIO(out)) as im:
        bbox = _bbox_alpha(im)
        # Le cadre ne doit pas être coupé: bbox est intégralement dans la zone utile à partir du pad.
        pad = round(min(box_w, box_h) * cfg.padding_pct)
        assert bbox[0] <= pad + 1
        assert bbox[2] <= box_w  # triviale, mais on garde la contrainte explicite
        assert bbox[1] >= 0 and bbox[3] <= box_h

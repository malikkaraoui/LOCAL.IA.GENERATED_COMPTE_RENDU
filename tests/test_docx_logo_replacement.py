from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest
from PIL import Image  # type: ignore

from lxml import etree as ET  # type: ignore

from core.docx_branding import update_docx_header


def _png_bytes(color=(255, 0, 0, 255), size=(32, 32)) -> bytes:
    buf = io.BytesIO()
    im = Image.new("RGBA", size, color)
    im.save(buf, format="PNG")
    return buf.getvalue()


def _bbox_alpha(im: Image.Image, *, alpha_threshold: int = 8) -> tuple[int, int, int, int]:
    im = im.convert("RGBA")
    a = im.split()[-1]
    mask = a.point(lambda x: 255 if x > alpha_threshold else 0)
    bbox = mask.getbbox()
    assert bbox is not None
    return bbox


def _make_docx(path: Path, files: dict[str, bytes]) -> None:
    # Docx minimal: notre code ne dépend que de word/header*.xml, rels, et word/media/*
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)


def _read_zip_file(path: Path, name: str) -> bytes:
    with zipfile.ZipFile(path, "r") as z:
        return z.read(name)


W_HDR_DRAWING = (
    "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
    "<w:hdr xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'"
    " xmlns:wp='http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'"
    " xmlns:a='http://schemas.openxmlformats.org/drawingml/2006/main'"
    " xmlns:r='http://schemas.openxmlformats.org/officeDocument/2006/relationships'"
    " xmlns:pic='http://schemas.openxmlformats.org/drawingml/2006/picture'>"
    "  <w:p><w:r><w:drawing>"
    "    <wp:inline>"
    "      <wp:extent cx='914400' cy='457200'/>"  # 1in x 0.5in
    "      <wp:docPr id='1' name='Logo' descr='{TAG}'/>"
    "      <a:graphic>"
    "        <a:graphicData uri='http://schemas.openxmlformats.org/drawingml/2006/picture'>"
    "          <pic:pic>"
    "            <pic:blipFill><a:blip r:embed='rId1'/></pic:blipFill>"
    "          </pic:pic>"
    "        </a:graphicData>"
    "      </a:graphic>"
    "    </wp:inline>"
    "  </w:drawing></w:r></w:p>"
    "</w:hdr>"
)

W_HDR_DRAWING_TITLE = W_HDR_DRAWING.replace("descr='{TAG}'", "title='{TAG}'")

W_HDR_DRAWING_CROPPED = W_HDR_DRAWING.replace(
    "<pic:blipFill><a:blip r:embed='rId1'/></pic:blipFill>",
    "<pic:blipFill>"
    "<a:blip r:embed='rId1'/>"
    "<a:srcRect l='10000' t='20000' r='30000' b='40000'/>"
    "</pic:blipFill>",
)

W_HDR_VML = (
    "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
    "<w:hdr xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'"
    " xmlns:v='urn:schemas-microsoft-com:vml'"
    " xmlns:o='urn:schemas-microsoft-com:office:office'"
    " xmlns:r='http://schemas.openxmlformats.org/officeDocument/2006/relationships'>"
    "  <w:p><w:r><w:pict>"
    "    <v:shape id='logo1' o:title='{TAG}' style='width:72pt;height:36pt'>"
    "      <v:imagedata r:id='rId5' o:title='{TAG}'/>"
    "    </v:shape>"
    "  </w:pict></w:r></w:p>"
    "</w:hdr>"
)

W_HDR_VML_CROPPED = W_HDR_VML.replace(
    "<v:imagedata r:id='rId5' o:title='{TAG}'/>",
    "<v:imagedata r:id='rId5' o:title='{TAG}' croptop='1000f' cropleft='2000f' cropbottom='3000f' cropright='4000f'/>",
)

RELS_RID1 = (
    "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
    "<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'>"
    "  <Relationship Id='rId1' Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/image' Target='media/image1.png'/>"
    "  <Relationship Id='rId2' Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/image' Target='media/keep.png'/>"
    "</Relationships>"
).encode("utf-8")

RELS_RID5 = (
    "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
    "<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'>"
    "  <Relationship Id='rId5' Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/image' Target='media/image5.png'/>"
    "</Relationships>"
).encode("utf-8")


def test_update_docx_header_replaces_logo_by_descr(tmp_path: Path):
    tpl = tmp_path / "tpl.docx"
    out = tmp_path / "out.docx"

    original = _png_bytes((255, 0, 0, 255), (10, 10))
    keep = _png_bytes((0, 0, 255, 255), (10, 10))

    _make_docx(
        tpl,
        {
            "word/header1.xml": W_HDR_DRAWING.format(TAG="LOGO_HEADER").encode("utf-8"),
            "word/_rels/header1.xml.rels": RELS_RID1,
            "word/media/image1.png": original,
            "word/media/keep.png": keep,
        },
    )

    logo_path = tmp_path / "new_logo.png"
    # logo avec "marges" (petit carré au centre)
    with Image.new("RGBA", (80, 80), (0, 0, 0, 0)) as bg:
        fg = Image.new("RGBA", (20, 20), (0, 255, 0, 255))
        bg.paste(fg, (30, 30), fg)
        bg.save(logo_path)

    update_docx_header(tpl, out, mapping={}, logo_path=logo_path)

    replaced = _read_zip_file(out, "word/media/image1.png")
    kept = _read_zip_file(out, "word/media/keep.png")
    assert replaced != original
    assert kept == keep

    # géométrie inchangée: header1.xml pas modifié (pas de placeholders)
    assert _read_zip_file(out, "word/header1.xml") == _read_zip_file(tpl, "word/header1.xml")

    # image valide
    with Image.open(io.BytesIO(replaced)) as im:
        assert im.size == (300, 150)  # 1in x 0.5in à 300 dpi

        # V3: collé à gauche + centré verticalement
        bbox = _bbox_alpha(im)
        pad = round(min(im.size) * 0.08)
        assert bbox[0] <= pad + 1

        cy = (bbox[1] + bbox[3]) / 2.0
        assert abs(cy - (im.size[1] / 2.0)) <= 2.0


def test_update_docx_header_replaces_logo_by_title(tmp_path: Path):
    tpl = tmp_path / "tpl.docx"
    out = tmp_path / "out.docx"

    original = _png_bytes((255, 0, 0, 255), (10, 10))
    _make_docx(
        tpl,
        {
            "word/header1.xml": W_HDR_DRAWING_TITLE.format(TAG="LOGO_HEADER").encode("utf-8"),
            "word/_rels/header1.xml.rels": RELS_RID1,
            "word/media/image1.png": original,
            "word/media/keep.png": _png_bytes((0, 0, 255, 255), (10, 10)),
        },
    )

    logo_path = tmp_path / "new_logo.png"
    logo_path.write_bytes(_png_bytes((0, 255, 0, 255), (50, 20)))

    update_docx_header(tpl, out, mapping={}, logo_path=logo_path)
    replaced = _read_zip_file(out, "word/media/image1.png")
    assert replaced != original


def test_update_docx_header_replaces_logo_with_trailing_newline(tmp_path: Path):
    tpl = tmp_path / "tpl.docx"
    out = tmp_path / "out.docx"

    original = _png_bytes((255, 0, 0, 255), (10, 10))
    _make_docx(
        tpl,
        {
            # Word peut injecter un retour à la ligne dans descr (LOGO_HEADER\n)
            "word/header1.xml": W_HDR_DRAWING.format(TAG="LOGO_HEADER\n").encode("utf-8"),
            "word/_rels/header1.xml.rels": RELS_RID1,
            "word/media/image1.png": original,
            "word/media/keep.png": _png_bytes((0, 0, 255, 255), (10, 10)),
        },
    )

    logo_path = tmp_path / "new_logo.png"
    logo_path.write_bytes(_png_bytes((0, 255, 0, 255), (50, 20)))

    update_docx_header(tpl, out, mapping={}, logo_path=logo_path)
    replaced = _read_zip_file(out, "word/media/image1.png")
    assert replaced != original


def test_update_docx_header_replaces_logo_vml(tmp_path: Path):
    tpl = tmp_path / "tpl.docx"
    out = tmp_path / "out.docx"

    original = _png_bytes((255, 0, 0, 255), (10, 10))
    _make_docx(
        tpl,
        {
            "word/header1.xml": W_HDR_VML.format(TAG="LOGO_HEADER").encode("utf-8"),
            "word/_rels/header1.xml.rels": RELS_RID5,
            "word/media/image5.png": original,
        },
    )

    logo_path = tmp_path / "new_logo.png"
    logo_path.write_bytes(_png_bytes((0, 255, 0, 255), (64, 64)))

    update_docx_header(tpl, out, mapping={}, logo_path=logo_path)
    replaced = _read_zip_file(out, "word/media/image5.png")
    assert replaced != original


def test_update_docx_header_missing_placeholder_raises(tmp_path: Path):
    tpl = tmp_path / "tpl.docx"
    out = tmp_path / "out.docx"

    _make_docx(
        tpl,
        {
            "word/header1.xml": W_HDR_DRAWING.format(TAG="NOT_IT").encode("utf-8"),
            "word/_rels/header1.xml.rels": RELS_RID1,
            "word/media/image1.png": _png_bytes((255, 0, 0, 255), (10, 10)),
            "word/media/keep.png": _png_bytes((0, 0, 255, 255), (10, 10)),
        },
    )

    logo_path = tmp_path / "new_logo.png"
    logo_path.write_bytes(_png_bytes((0, 255, 0, 255), (50, 20)))

    with pytest.raises(ValueError) as exc:
        update_docx_header(tpl, out, mapping={}, logo_path=logo_path)

    assert "LOGO_HEADER" in str(exc.value)


def test_update_docx_header_strips_drawingml_crop_srcrect(tmp_path: Path):
    tpl = tmp_path / "tpl.docx"
    out = tmp_path / "out.docx"

    original = _png_bytes((255, 0, 0, 255), (10, 10))
    _make_docx(
        tpl,
        {
            "word/header1.xml": W_HDR_DRAWING_CROPPED.format(TAG="LOGO_HEADER").encode("utf-8"),
            "word/_rels/header1.xml.rels": RELS_RID1,
            "word/media/image1.png": original,
            "word/media/keep.png": _png_bytes((0, 0, 255, 255), (10, 10)),
        },
    )

    logo_path = tmp_path / "new_logo.png"
    logo_path.write_bytes(_png_bytes((0, 255, 0, 255), (50, 20)))

    update_docx_header(tpl, out, mapping={}, logo_path=logo_path)

    # media remplacé
    replaced = _read_zip_file(out, "word/media/image1.png")
    assert replaced != original

    # crop supprimé (mais géométrie conservée)
    in_xml = _read_zip_file(tpl, "word/header1.xml")
    out_xml = _read_zip_file(out, "word/header1.xml")

    in_root = ET.fromstring(in_xml)
    out_root = ET.fromstring(out_xml)

    # plus de a:srcRect sur la drawing concernée
    assert out_root.findall(".//a:srcRect", namespaces={
        "a": "http://schemas.openxmlformats.org/drawingml/2006/main"
    }) == []

    # extent inchangé
    ns = {
        "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    }
    in_extent = in_root.find(".//wp:extent", namespaces=ns)
    out_extent = out_root.find(".//wp:extent", namespaces=ns)
    assert in_extent is not None and out_extent is not None
    assert in_extent.get("cx") == out_extent.get("cx")
    assert in_extent.get("cy") == out_extent.get("cy")


def test_update_docx_header_strips_vml_crop_attrs(tmp_path: Path):
    tpl = tmp_path / "tpl.docx"
    out = tmp_path / "out.docx"

    original = _png_bytes((255, 0, 0, 255), (10, 10))
    _make_docx(
        tpl,
        {
            "word/header1.xml": W_HDR_VML_CROPPED.format(TAG="LOGO_HEADER").encode("utf-8"),
            "word/_rels/header1.xml.rels": RELS_RID5,
            "word/media/image5.png": original,
        },
    )

    logo_path = tmp_path / "new_logo.png"
    logo_path.write_bytes(_png_bytes((0, 255, 0, 255), (64, 64)))

    update_docx_header(tpl, out, mapping={}, logo_path=logo_path)

    # media remplacé
    replaced = _read_zip_file(out, "word/media/image5.png")
    assert replaced != original

    in_root = ET.fromstring(_read_zip_file(tpl, "word/header1.xml"))
    out_root = ET.fromstring(_read_zip_file(out, "word/header1.xml"))

    ns = {
        "v": "urn:schemas-microsoft-com:vml",
    }
    in_shape = in_root.find(".//v:shape", namespaces=ns)
    out_shape = out_root.find(".//v:shape", namespaces=ns)
    assert in_shape is not None and out_shape is not None
    assert (in_shape.get("style") or "") == (out_shape.get("style") or "")

    in_img = in_root.find(".//v:imagedata", namespaces=ns)
    out_img = out_root.find(".//v:imagedata", namespaces=ns)
    assert in_img is not None and out_img is not None
    assert "croptop" in in_img.attrib
    assert "cropleft" in in_img.attrib
    assert "cropbottom" in in_img.attrib
    assert "cropright" in in_img.attrib

    assert "croptop" not in out_img.attrib
    assert "cropleft" not in out_img.attrib
    assert "cropbottom" not in out_img.attrib
    assert "cropright" not in out_img.attrib

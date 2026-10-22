from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps


IMAGE_TAG_RE = re.compile(r"<image\b[^>]*>", re.DOTALL)
HREF_RE = re.compile(r'(?P<prefix>\b(?:xlink:href|href)=")[^"]*(?P<suffix>")')
ID_RE = re.compile(r'\bid="([^"]+)"')
ATTR_RE_TEMPLATE = r'\b{attribute}="([^"]+)"'
REL_RE = re.compile(
    r'<Relationship\b[^>]*\bId="(?P<id>[^"]+)"[^>]*\bTarget="(?P<target>[^"]+)"[^>]*/?>'
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def attr(tag: str, attribute: str) -> str:
    match = re.search(ATTR_RE_TEMPLATE.format(attribute=re.escape(attribute)), tag)
    if not match:
        raise ValueError(f"Missing {attribute} in image tag")
    return match.group(1)


def normalize_feature(path: Path) -> Image.Image:
    values = np.load(path)
    if values.ndim != 3:
        raise ValueError(f"Expected CHW/HWC feature tensor: {path} {values.shape}")
    if values.shape[0] in (1, 2, 3, 4):
        values = np.moveaxis(values[:3], 0, -1)
    if values.shape[-1] == 1:
        values = np.repeat(values, 3, axis=-1)
    channels = []
    for index in range(3):
        channel = values[..., index].astype(np.float32)
        finite = channel[np.isfinite(channel)]
        low, high = np.percentile(finite, [2, 98]) if finite.size else (0.0, 1.0)
        if high <= low:
            high = low + 1.0
        channels.append(np.clip((channel - low) / (high - low), 0.0, 1.0))
    rgb = np.stack(channels, axis=-1)
    return Image.fromarray(np.uint8(rgb * 255.0), "RGB")


def flatten_rgb(image: Image.Image) -> Image.Image:
    image = image.convert("RGBA")
    background = Image.new("RGBA", image.size, "white")
    background.alpha_composite(image)
    return background.convert("RGB")


def build_composite(frame_dir: Path, output: Path, size: tuple[int, int]) -> None:
    width, height = size
    top_height = round(height * 0.63)
    bottom_height = height - top_height
    half_width = width // 2

    with Image.open(frame_dir / "render_rgb.png") as source:
        render = ImageOps.fit(
            flatten_rgb(source),
            (width, top_height),
            method=Image.Resampling.LANCZOS,
        )
    language = ImageOps.fit(
        normalize_feature(frame_dir / "language_feature.npy"),
        (half_width, bottom_height),
        method=Image.Resampling.LANCZOS,
    )
    with Image.open(frame_dir / "identity_feature.png") as source:
        identity = ImageOps.fit(
            flatten_rgb(source),
            (width - half_width, bottom_height),
            method=Image.Resampling.LANCZOS,
        )

    composite = Image.new("RGB", size, "white")
    composite.paste(render, (0, 0))
    composite.paste(language, (0, top_height))
    composite.paste(identity, (half_width, top_height))
    output.parent.mkdir(parents=True, exist_ok=True)
    composite.save(output, format="PNG", optimize=True)


def replace_svg_image(svg_path: Path, image_id: str, png_path: Path) -> dict:
    before = svg_path.read_text(encoding="utf-8")
    target_tag = None
    for match in IMAGE_TAG_RE.finditer(before):
        id_match = ID_RE.search(match.group(0))
        if id_match and id_match.group(1) == image_id:
            target_tag = match.group(0)
            break
    if target_tag is None:
        raise KeyError(image_id)

    width = round(float(attr(target_tag, "width")) * 5)
    height = round(float(attr(target_tag, "height")) * 5)
    build_composite(args.frame_dir, png_path, (width, height))
    data_uri = "data:image/png;base64," + base64.b64encode(png_path.read_bytes()).decode("ascii")
    replacement, count = HREF_RE.subn(
        lambda match: f"{match.group('prefix')}{data_uri}{match.group('suffix')}",
        target_tag,
        count=1,
    )
    if count != 1:
        raise AssertionError("Image href was not replaced exactly once")
    static_before = HREF_RE.sub(r"\g<prefix>__IMAGE_DATA__\g<suffix>", target_tag)
    static_after = HREF_RE.sub(r"\g<prefix>__IMAGE_DATA__\g<suffix>", replacement)
    if static_before != static_after:
        raise AssertionError("Image geometry changed")

    after = before.replace(target_tag, replacement, 1)
    scrub_before = HREF_RE.sub(r"\g<prefix>__IMAGE_DATA__\g<suffix>", before)
    scrub_after = HREF_RE.sub(r"\g<prefix>__IMAGE_DATA__\g<suffix>", after)
    if scrub_before != scrub_after:
        raise AssertionError("SVG content outside image payload changed")
    svg_path.write_text(after, encoding="utf-8", newline="")
    return {
        "image_id": image_id,
        "target_pixels": [width, height],
        "svg_non_image_content_unchanged": True,
        "composite_sha256": sha256(png_path.read_bytes()),
    }


def export_svg(inkscape: Path, svg: Path) -> None:
    for extension in ("png", "pdf"):
        output = svg.with_suffix(f".{extension}")
        command = [
            str(inkscape),
            str(svg),
            "--export-area-page",
            f"--export-filename={output}",
        ]
        if extension == "png":
            command.append("--export-dpi=300")
        subprocess.run(command, check=True)


def media_target_for_description(document_xml: str, relationships_xml: str, description: str) -> str:
    relations = {
        match.group("id"): match.group("target")
        for match in REL_RE.finditer(relationships_xml)
    }
    doc_pr = re.search(
        rf'<wp:docPr\b[^>]*\bdescr="{re.escape(description)}"[^>]*/?>',
        document_xml,
    )
    if not doc_pr:
        raise KeyError(description)
    drawing_start = document_xml.rfind("<w:drawing", 0, doc_pr.start())
    drawing_end = document_xml.find("</w:drawing>", doc_pr.end())
    drawing = document_xml[drawing_start : drawing_end + len("</w:drawing>")]
    relationship_id = re.search(r'<a:blip\b[^>]*\br:embed="([^"]+)"', drawing).group(1)
    return "word/" + relations[relationship_id].replace("\\", "/")


def fit_for_docx(source: Path, target_size: tuple[int, int]) -> bytes:
    with Image.open(source) as image:
        contained = ImageOps.contain(
            flatten_rgb(image), target_size, method=Image.Resampling.LANCZOS
        )
    canvas = Image.new("RGB", target_size, "white")
    canvas.paste(
        contained,
        ((target_size[0] - contained.width) // 2, (target_size[1] - contained.height) // 2),
    )
    buffer = BytesIO()
    canvas.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def replace_docx_pipeline_image(docx_path: Path, pipeline_png: Path, backup_path: Path) -> dict:
    if not backup_path.exists():
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(docx_path, backup_path)

    with zipfile.ZipFile(docx_path, "r") as source_zip:
        document_xml = source_zip.read("word/document.xml").decode("utf-8")
        relationships_xml = source_zip.read("word/_rels/document.xml.rels").decode("utf-8")
        media_name = media_target_for_description(
            document_xml, relationships_xml, "ILGS-IPR训练流程"
        )
        with Image.open(BytesIO(source_zip.read(media_name))) as embedded:
            target_size = embedded.size
        replacement = fit_for_docx(pipeline_png, target_size)
        entries = [(info, source_zip.read(info.filename)) for info in source_zip.infolist()]

    with tempfile.NamedTemporaryFile(
        dir=docx_path.parent, suffix=".docx", delete=False
    ) as handle:
        temporary = Path(handle.name)
    try:
        with zipfile.ZipFile(temporary, "w") as output_zip:
            for info, payload in entries:
                output_zip.writestr(info, replacement if info.filename == media_name else payload)
        shutil.move(str(temporary), docx_path)
    finally:
        temporary.unlink(missing_ok=True)

    with zipfile.ZipFile(backup_path, "r") as before_zip, zipfile.ZipFile(
        docx_path, "r"
    ) as after_zip:
        changed = [
            name
            for name in before_zip.namelist()
            if before_zip.read(name) != after_zip.read(name)
        ]
        if changed != [media_name]:
            raise AssertionError(f"Unexpected DOCX entries changed: {changed}")
    return {
        "docx_changed_entry": media_name,
        "docx_layout_xml_unchanged": True,
        "embedded_pixels": list(target_size),
    }


def main() -> None:
    global args
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--frame-dir",
        type=Path,
        default=Path(
            r"D:\downloads\real_main_figure_assets_20261018_extracted\real_main_figure_assets_20261018\covered_desk\models\ipr\test\frames\11"
        ),
    )
    parser.add_argument(
        "--svg",
        type=Path,
        default=Path(r"D:\wlxy\ilgs\文章图\pipeline_final_current_ipr.svg"),
    )
    parser.add_argument(
        "--docx",
        type=Path,
        default=Path(r"D:\wlxy\ILGS-IPR_中文_统一方法与协议修订_主图真实素材_20261018.docx"),
    )
    parser.add_argument(
        "--inkscape",
        type=Path,
        default=Path(r"E:\Inkscape\bin\inkscape.com"),
    )
    parser.add_argument(
        "--audit-dir",
        type=Path,
        default=Path(r"outputs\real_main_figure_content_only_20261018\frame11_update"),
    )
    args = parser.parse_args()

    args.audit_dir.mkdir(parents=True, exist_ok=True)
    svg_backup = args.audit_dir / "pipeline_before_frame11.svg"
    if not svg_backup.exists():
        shutil.copy2(args.svg, svg_backup)
    composite = args.audit_dir / "covered_desk_frame11_gaussian_composite.png"
    report = replace_svg_image(args.svg, "gaussian-illustration-image", composite)
    export_svg(args.inkscape, args.svg)
    report.update(
        replace_docx_pipeline_image(
            args.docx,
            args.svg.with_suffix(".png"),
            args.audit_dir / "manuscript_before_frame11.docx",
        )
    )
    report.update(
        {
            "source_frame": str(args.frame_dir),
            "svg": str(args.svg),
            "docx": str(args.docx),
            "scope": "one embedded pipeline image only",
        }
    )
    audit_path = args.audit_dir / "frame11_replacement_audit.json"
    audit_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(audit_path)


if __name__ == "__main__":
    main()

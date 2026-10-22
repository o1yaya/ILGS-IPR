from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tempfile
import zipfile
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps


REL_RE = re.compile(
    r'<Relationship\b[^>]*\bId="(?P<id>[^"]+)"[^>]*\bTarget="(?P<target>[^"]+)"[^>]*/?>'
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fit_with_white_padding(source: Path, size: tuple[int, int]) -> bytes:
    with Image.open(source) as image:
        image = image.convert("RGBA")
        background = Image.new("RGBA", image.size, "white")
        background.alpha_composite(image)
        contained = ImageOps.contain(
            background.convert("RGB"),
            size,
            method=Image.Resampling.LANCZOS,
        )
    canvas = Image.new("RGB", size, "white")
    x = (size[0] - contained.width) // 2
    y = (size[1] - contained.height) // 2
    canvas.paste(contained, (x, y))
    buffer = BytesIO()
    canvas.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def media_target_for_description(
    document_xml: str,
    relationships_xml: str,
    description: str,
) -> str:
    relations = {
        match.group("id"): match.group("target")
        for match in REL_RE.finditer(relationships_xml)
    }
    doc_pr = re.search(
        rf'<wp:docPr\b[^>]*\bdescr="{re.escape(description)}"[^>]*/?>',
        document_xml,
    )
    if not doc_pr:
        raise KeyError(f"Drawing description not found: {description}")
    drawing_start = document_xml.rfind("<w:drawing", 0, doc_pr.start())
    drawing_end = document_xml.find("</w:drawing>", doc_pr.end())
    if drawing_start < 0 or drawing_end < 0:
        raise ValueError(f"Could not isolate drawing for {description}")
    drawing = document_xml[drawing_start : drawing_end + len("</w:drawing>")]
    blip = re.search(r'<a:blip\b[^>]*\br:embed="([^"]+)"', drawing)
    if not blip:
        raise ValueError(f"Embedded relationship not found for {description}")
    target = relations[blip.group(1)]
    return "word/" + target.replace("\\", "/")


def png_dimensions(data: bytes) -> tuple[int, int]:
    with Image.open(BytesIO(data)) as image:
        return image.size


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Replace only the two embedded main-figure PNG payloads in a DOCX."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(r"D:\wlxy\ILGS-IPR_中文_统一方法与协议修订_主图整合_20261018.docx"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(r"D:\wlxy\ILGS-IPR_中文_统一方法与协议修订_主图真实素材_20261018.docx"),
    )
    parser.add_argument(
        "--pipeline",
        type=Path,
        default=Path(r"D:\wlxy\ilgs\文章图\pipeline_final_current_ipr.png"),
    )
    parser.add_argument(
        "--method",
        type=Path,
        default=Path(r"D:\wlxy\ilgs\文章图\method_final_current_ipr.png"),
    )
    parser.add_argument(
        "--audit",
        type=Path,
        default=Path(
            r"outputs\real_main_figure_content_only_20261018\manuscript_media_only_audit.json"
        ),
    )
    args = parser.parse_args()

    source_bytes = args.source.read_bytes()
    with zipfile.ZipFile(BytesIO(source_bytes), "r") as source_zip:
        document_xml = source_zip.read("word/document.xml").decode("utf-8")
        relationships_xml = source_zip.read("word/_rels/document.xml.rels").decode("utf-8")
        pipeline_media = media_target_for_description(
            document_xml, relationships_xml, "ILGS-IPR训练流程"
        )
        method_media = media_target_for_description(
            document_xml,
            relationships_xml,
            "IPR可靠性估计与置信加权身份损失",
        )

        original_pipeline = source_zip.read(pipeline_media)
        original_method = source_zip.read(method_media)
        pipeline_size = png_dimensions(original_pipeline)
        method_size = png_dimensions(original_method)

        replacements = {
            pipeline_media: fit_with_white_padding(args.pipeline, pipeline_size),
            method_media: fit_with_white_padding(args.method, method_size),
        }

        args.output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            dir=args.output.parent, suffix=".docx", delete=False
        ) as handle:
            temp_path = Path(handle.name)

        try:
            with zipfile.ZipFile(temp_path, "w") as output_zip:
                for info in source_zip.infolist():
                    payload = replacements.get(info.filename, source_zip.read(info.filename))
                    output_zip.writestr(info, payload)
            shutil.move(str(temp_path), args.output)
        finally:
            temp_path.unlink(missing_ok=True)

    with zipfile.ZipFile(args.source, "r") as source_zip, zipfile.ZipFile(
        args.output, "r"
    ) as output_zip:
        source_names = source_zip.namelist()
        output_names = output_zip.namelist()
        if source_names != output_names:
            raise AssertionError("DOCX package entry order or names changed")
        changed = []
        unchanged = []
        for name in source_names:
            source_payload = source_zip.read(name)
            output_payload = output_zip.read(name)
            if source_payload == output_payload:
                unchanged.append(name)
            else:
                changed.append(name)
        expected_changed = sorted(replacements)
        if sorted(changed) != expected_changed:
            raise AssertionError(
                f"Unexpected DOCX entries changed: {changed}; expected {expected_changed}"
            )

        if source_zip.read("word/document.xml") != output_zip.read("word/document.xml"):
            raise AssertionError("Word layout XML changed")
        if source_zip.read("word/_rels/document.xml.rels") != output_zip.read(
            "word/_rels/document.xml.rels"
        ):
            raise AssertionError("Word relationship XML changed")

    report = {
        "scope": "DOCX embedded image payloads only",
        "source": str(args.source),
        "output": str(args.output),
        "source_sha256": sha256(source_bytes),
        "output_sha256": sha256(args.output.read_bytes()),
        "changed_package_entries": changed,
        "unchanged_package_entry_count": len(unchanged),
        "document_xml_unchanged": True,
        "relationships_xml_unchanged": True,
        "pipeline": {
            "media": pipeline_media,
            "source_figure": str(args.pipeline),
            "embedded_size": list(pipeline_size),
        },
        "method": {
            "media": method_media,
            "source_figure": str(args.method),
            "embedded_size": list(method_size),
        },
    }
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    args.audit.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()

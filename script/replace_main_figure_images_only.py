from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import shutil
import subprocess
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps


IMAGE_TAG_RE = re.compile(r"<image\b[^>]*>", re.DOTALL)
ID_RE = re.compile(r'\bid="([^"]+)"')
ATTR_RE_TEMPLATE = r'\b{attribute}="([^"]+)"'
HREF_RE = re.compile(r'(?P<prefix>\b(?:xlink:href|href)=")[^"]*(?P<suffix>")')
DATA_URI_PREFIX = "data:image/png;base64,"


METHOD_MAPPING = {
    "novel-view-image": "bench_render_rgb.png",
    "language-feature-image": "bench_language_feature.png",
    "identity-feature-image": "bench_identity_feature.png",
    "segment-similarity-image": "bench_ipr_mask.png",
    "stage1-rgb-image": "bench_rgb_train.png",
    "stage1-noisy-map": "bench_raw_labels.png",
    "cleanup-image": "bench_cleanup_zoom.png",
    "semantic-image": "bench_crop_consistency.png",
    "area-image": "bench_large_risk.png",
    "reliability-map-image": "bench_reliability.png",
    "official-image": "bench_official_overlay.png",
    "ipr-image": "bench_ipr_overlay.png",
}


PIPELINE_MAPPING = {
    "input-rgb-image": "covered_desk_rgb_train.png",
    "input-labels-image": "covered_desk_raw_labels.png",
    "cleanup-mask-image": "covered_desk_cleanup_zoom.png",
    "semantic-crops-image": "covered_desk_crop_consistency.png",
    "area-prior-image": "covered_desk_large_risk.png",
    "clean-labels-image": "covered_desk_clean_labels.png",
    "reliability-image": "covered_desk_reliability.png",
    "gaussian-illustration-image": "__covered_desk_gaussian_composite.png",
    "rasterized-identity-image": "covered_desk_identity_logits.png",
    "target-identity-image": "covered_desk_clean_labels.png",
    "rasterized-language-image": "covered_desk_language_feature.png",
    "rendered-rgb-image": "covered_desk_render_rgb.png",
    "target-rgb-image": "covered_desk_rgb_test.png",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def attr(tag: str, attribute: str) -> str:
    match = re.search(ATTR_RE_TEMPLATE.format(attribute=re.escape(attribute)), tag)
    if not match:
        raise ValueError(f"Missing {attribute!r} in image tag")
    return match.group(1)


def image_nodes(svg_text: str) -> dict[str, str]:
    nodes: dict[str, str] = {}
    for match in IMAGE_TAG_RE.finditer(svg_text):
        tag = match.group(0)
        id_match = ID_RE.search(tag)
        if id_match:
            nodes[id_match.group(1)] = tag
    return nodes


def target_pixels(tag: str, scale: float = 5.0) -> tuple[int, int]:
    width = max(1, round(float(attr(tag, "width")) * scale))
    height = max(1, round(float(attr(tag, "height")) * scale))
    return width, height


def flatten_rgb(image: Image.Image) -> Image.Image:
    image = image.convert("RGBA")
    background = Image.new("RGBA", image.size, "white")
    background.alpha_composite(image)
    return background.convert("RGB")


def fit_asset(source: Path, output: Path, size: tuple[int, int]) -> Path:
    with Image.open(source) as image:
        fitted = ImageOps.fit(
            flatten_rgb(image),
            size,
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        fitted.save(output, format="PNG", optimize=True)
    return output


def build_gaussian_composite(asset_dir: Path, output: Path, size: tuple[int, int]) -> Path:
    width, height = size
    top_height = round(height * 0.63)
    bottom_height = height - top_height
    half_width = width // 2

    with Image.open(asset_dir / "covered_desk_render_rgb.png") as render_src:
        render = ImageOps.fit(
            flatten_rgb(render_src),
            (width, top_height),
            method=Image.Resampling.LANCZOS,
        )
    with Image.open(asset_dir / "covered_desk_language_feature.png") as language_src:
        language = ImageOps.fit(
            flatten_rgb(language_src),
            (half_width, bottom_height),
            method=Image.Resampling.LANCZOS,
        )
    with Image.open(asset_dir / "covered_desk_identity_feature.png") as identity_src:
        identity = ImageOps.fit(
            flatten_rgb(identity_src),
            (width - half_width, bottom_height),
            method=Image.Resampling.LANCZOS,
        )

    composite = Image.new("RGB", size, "white")
    composite.paste(render, (0, 0))
    composite.paste(language, (0, top_height))
    composite.paste(identity, (half_width, top_height))
    output.parent.mkdir(parents=True, exist_ok=True)
    composite.save(output, format="PNG", optimize=True)
    return output


def png_data_uri(path: Path) -> str:
    return DATA_URI_PREFIX + base64.b64encode(path.read_bytes()).decode("ascii")


def static_tag(tag: str) -> str:
    return HREF_RE.sub(r"\g<prefix>__IMAGE_DATA__\g<suffix>", tag, count=1)


def replace_images(
    svg_path: Path,
    mapping: dict[str, str],
    asset_dir: Path,
    prepared_dir: Path,
    backup_dir: Path,
) -> dict:
    original_bytes = svg_path.read_bytes()
    original = original_bytes.decode("utf-8")
    before_nodes = image_nodes(original)
    missing = sorted(set(mapping) - set(before_nodes))
    if missing:
        raise KeyError(f"Missing image ids in {svg_path.name}: {missing}")

    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / svg_path.name
    if not backup_path.exists():
        shutil.copy2(svg_path, backup_path)

    replacements: dict[str, dict] = {}
    updated = original

    for image_id, asset_name in mapping.items():
        tag = before_nodes[image_id]
        size = target_pixels(tag)
        prepared_path = prepared_dir / f"{svg_path.stem}__{image_id}.png"

        if asset_name == "__covered_desk_gaussian_composite.png":
            build_gaussian_composite(asset_dir, prepared_path, size)
            source_path = prepared_path
        else:
            source_path = asset_dir / asset_name
            if not source_path.is_file():
                raise FileNotFoundError(source_path)
            fit_asset(source_path, prepared_path, size)
            source_path = prepared_path

        new_href = png_data_uri(source_path)
        new_tag, count = HREF_RE.subn(
            lambda match: f"{match.group('prefix')}{new_href}{match.group('suffix')}",
            tag,
            count=1,
        )
        if count != 1:
            raise ValueError(f"Expected one href in image node {image_id}")
        if static_tag(tag) != static_tag(new_tag):
            raise AssertionError(f"Non-image attributes changed in node {image_id}")
        if updated.count(tag) != 1:
            raise AssertionError(f"Image tag {image_id} was not unique")
        updated = updated.replace(tag, new_tag, 1)
        replacements[image_id] = {
            "source": asset_name,
            "prepared": str(prepared_path),
            "target_pixels": list(size),
            "prepared_sha256": sha256_bytes(prepared_path.read_bytes()),
        }

    svg_path.write_text(updated, encoding="utf-8", newline="")
    final_bytes = svg_path.read_bytes()
    final = final_bytes.decode("utf-8")
    after_nodes = image_nodes(final)

    if set(before_nodes) != set(after_nodes):
        raise AssertionError("Image-node set changed")
    for image_id in before_nodes:
        if static_tag(before_nodes[image_id]) != static_tag(after_nodes[image_id]):
            raise AssertionError(f"Image geometry or attributes changed: {image_id}")

    scrubbed_before = HREF_RE.sub(r"\g<prefix>__IMAGE_DATA__\g<suffix>", original)
    scrubbed_after = HREF_RE.sub(r"\g<prefix>__IMAGE_DATA__\g<suffix>", final)
    if scrubbed_before != scrubbed_after:
        raise AssertionError("SVG content outside embedded image data changed")

    return {
        "svg": str(svg_path),
        "backup": str(backup_path),
        "before_sha256": sha256_bytes(original_bytes),
        "after_sha256": sha256_bytes(final_bytes),
        "canvas_tag": re.search(r"<svg\b[^>]*>", original, re.DOTALL).group(0),
        "image_count": len(before_nodes),
        "changed_image_ids": sorted(replacements),
        "unchanged_image_ids": sorted(set(before_nodes) - set(replacements)),
        "replacements": replacements,
        "layout_invariant": True,
    }


def export_figure(inkscape: Path, svg_path: Path) -> dict[str, str]:
    outputs = {}
    for extension in ("png", "pdf"):
        output = svg_path.with_suffix(f".{extension}")
        command = [
            str(inkscape),
            str(svg_path),
            "--export-area-page",
            f"--export-filename={output}",
        ]
        if extension == "png":
            command.append("--export-dpi=300")
        subprocess.run(command, check=True)
        outputs[extension] = str(output)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Replace only embedded raster content in the approved SVG layouts."
    )
    parser.add_argument(
        "--figure-dir",
        type=Path,
        default=Path(r"D:\wlxy\ilgs\文章图"),
    )
    parser.add_argument(
        "--asset-dir",
        type=Path,
        default=Path(r"D:\wlxy\ilgs\文章图\current_ipr_real_assets"),
    )
    parser.add_argument(
        "--inkscape",
        type=Path,
        default=Path(r"E:\Inkscape\bin\inkscape.com"),
    )
    parser.add_argument(
        "--audit-dir",
        type=Path,
        default=Path(r"outputs\real_main_figure_content_only_20261018"),
    )
    args = parser.parse_args()

    args.audit_dir.mkdir(parents=True, exist_ok=True)
    prepared_dir = args.figure_dir / "layout_preserved_real_assets"
    backup_dir = args.audit_dir / "layout_baseline"

    figures = [
        (args.figure_dir / "pipeline_final_current_ipr.svg", PIPELINE_MAPPING),
        (args.figure_dir / "method_final_current_ipr.svg", METHOD_MAPPING),
    ]

    report = {
        "scope": "embedded raster content only",
        "manual_pixel_editing": False,
        "method_scene": "3D-OVS bench, seed 0",
        "pipeline_scene": "3D-OVS covered_desk, seed 0",
        "retained_schematic_nodes": {
            "pipeline_final_current_ipr.svg": [
                "outlier-mask-image",
                "target-language-image",
            ]
        },
        "retention_reason": (
            "The online outlier gate and the language-supervision target were not "
            "persisted as independently auditable raster exports; their existing "
            "schematic tiles were retained instead of fabricating evidence."
        ),
        "figures": [],
    }

    for svg_path, mapping in figures:
        entry = replace_images(
            svg_path,
            mapping,
            args.asset_dir,
            prepared_dir,
            backup_dir,
        )
        entry["exports"] = export_figure(args.inkscape, svg_path)
        report["figures"].append(entry)

    report_path = args.audit_dir / "content_only_replacement_audit.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(report_path)


if __name__ == "__main__":
    main()

from __future__ import annotations

import base64
import re
import shutil
import zipfile
from pathlib import Path

from PIL import Image, ImageOps


WORKSPACE = Path(r"D:\PycharmProjects\PythonProject\ILGS_release-main")
ROOT = WORKSPACE / "outputs" / "method_figure_compact_highlight_20261008"
SOURCE_SVG = ROOT / "IPR_method_gpt_image2_top_pipeline_AI_package_v2" / "IPR_method_gpt_image2_top_pipeline_AI_v2.svg"
PACKAGE = ROOT / "IPR_method_gpt_image2_top_pipeline_AI_package_v3"
ASSETS = PACKAGE / "assets"
OUTPUT_SVG = PACKAGE / "IPR_method_gpt_image2_top_pipeline_AI_v3.svg"
EMBEDDED_SVG = ROOT / "IPR_method_gpt_image2_top_pipeline_AI_v3_embedded.svg"
ZIP_PATH = ROOT / "IPR_method_gpt_image2_top_pipeline_AI_package_v3.zip"

PPT_ASSETS = ROOT / "ppt_assets"
QUERY = Path(r"D:\downloads\ipr_method_assets\bench_20261007_203512_313407\query\ipr\2")

# Each Illustrator image gets a unique 72-DPI raster whose intrinsic pixel
# dimensions exactly match the SVG placement frame. Illustrator therefore does
# not need to implement SVG image fitting, cropping, or repeated-link reuse.
SPECS = {
    "novel-view-image": (PPT_ASSETS / "input_rgb.jpg", (375, 236), "crop", "novel_view.jpg"),
    "language-feature-image": (QUERY / "language_latent_rgb.png", (342, 183), "stretch", "language_feature.png"),
    "identity-feature-image": (QUERY / "identity_labels.png", (347, 183), "stretch", "identity_feature.png"),
    "segment-similarity-image": (QUERY / "segment_heatmap.png", (349, 183), "stretch", "segment_similarity.png"),
    "stage1-rgb-image": (PPT_ASSETS / "input_rgb.jpg", (373, 168), "crop", "input_rgb.jpg"),
    "stage1-noisy-map": (PPT_ASSETS / "noisy_identity_map.png", (373, 163), "stretch", "noisy_identity_map.png"),
    "cleanup-image": (PPT_ASSETS / "structure_cleanup.png", (240, 135), "stretch", "structure_cleanup.png"),
    "semantic-image": (PPT_ASSETS / "semantic_evidence.png", (233, 135), "stretch", "semantic_evidence.png"),
    "area-image": (PPT_ASSETS / "area_prior.png", (239, 135), "stretch", "area_prior.png"),
    "reliability-map-image": (PPT_ASSETS / "reliability_map.png", (196, 95), "stretch", "reliability_map.png"),
    "official-image": (PPT_ASSETS / "official_noisy_prediction.png", (389, 140), "stretch", "official_prediction.png"),
    "ipr-image": (PPT_ASSETS / "ipr_refined_prediction.png", (389, 147), "stretch", "ipr_prediction.png"),
}


def make_asset(source: Path, size: tuple[int, int], mode: str, destination: Path) -> None:
    with Image.open(source) as image:
        if destination.suffix.lower() in {".jpg", ".jpeg"}:
            image = image.convert("RGB")
        else:
            image = image.convert("RGBA")

        if mode == "crop":
            result = ImageOps.fit(image, size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
        else:
            result = image.resize(size, Image.Resampling.LANCZOS)

        if destination.suffix.lower() in {".jpg", ".jpeg"}:
            result.save(destination, quality=95, subsampling=0, dpi=(72, 72))
        else:
            result.save(destination, optimize=True, dpi=(72, 72))


def update_image_tag(svg: str, element_id: str, relative_href: str) -> str:
    pattern = re.compile(rf'<image\b(?=[^>]*\bid="{re.escape(element_id)}")[^>]*/>')
    match = pattern.search(svg)
    if not match:
        raise RuntimeError(f"Image element not found: {element_id}")

    tag = match.group(0)
    tag = re.sub(r'\s+(?:href|xlink:href)="[^"]*"', "", tag)
    tag = re.sub(r'\s+clip-path="[^"]*"', "", tag)
    tag = re.sub(r'preserveAspectRatio="[^"]*"', 'preserveAspectRatio="xMinYMin meet"', tag)
    tag = tag[:-2] + f' xlink:href="{relative_href}" image-rendering="auto"/>'
    return svg[: match.start()] + tag + svg[match.end() :]


def data_uri(path: Path) -> str:
    mime = "image/jpeg" if path.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    svg = SOURCE_SVG.read_text(encoding="utf-8")

    for element_id, (source, size, mode, filename) in SPECS.items():
        destination = ASSETS / filename
        make_asset(source, size, mode, destination)
        svg = update_image_tag(svg, element_id, f"assets/{filename}")

    OUTPUT_SVG.write_text(svg, encoding="utf-8")

    embedded = svg
    for _, (_, _, _, filename) in SPECS.items():
        embedded = embedded.replace(f'assets/{filename}', data_uri(ASSETS / filename))
    EMBEDDED_SVG.write_text(embedded, encoding="utf-8")

    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(OUTPUT_SVG, OUTPUT_SVG.name)
        for asset in sorted(ASSETS.iterdir()):
            archive.write(asset, f"assets/{asset.name}")

    print(OUTPUT_SVG)
    print(EMBEDDED_SVG)
    print(ZIP_PATH)


if __name__ == "__main__":
    main()

import fs from "node:fs/promises";
import path from "node:path";

const workspace = "D:\\PycharmProjects\\PythonProject\\ILGS_release-main";
const outDir = path.join(workspace, "outputs", "method_figure_compact_highlight_20261008");
const sourcePng = path.join(outDir, "IPR_method_gpt_image2_layout.png");
const vectorSvg = path.join(outDir, "IPR_method_editable.svg");
const exactSvg = path.join(outDir, "IPR_method_gpt_image2_layout_exact.svg");
const layeredSvg = path.join(outDir, "IPR_method_gpt_image2_layout_layered_editable.svg");
const vectorNamedSvg = path.join(outDir, "IPR_method_gpt_image2_layout_vector_editable.svg");

const pngBytes = await fs.readFile(sourcePng);
const pngUri = `data:image/png;base64,${pngBytes.toString("base64")}`;
const vectorText = await fs.readFile(vectorSvg, "utf8");
const openEnd = vectorText.indexOf(">");
const closeStart = vectorText.lastIndexOf("</svg>");
if (openEnd < 0 || closeStart < 0) throw new Error("Could not parse editable SVG");
const vectorInner = vectorText.slice(openEnd + 1, closeStart);

const exact = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
     width="1774" height="887" viewBox="0 0 1774 887">
  <title>IPR method figure - exact GPT Image 2 layout</title>
  <desc>Exact visual SVG wrapper of IPR_method_gpt_image2_layout.png.</desc>
  <g id="exact-reference" inkscape:groupmode="layer" inkscape:label="Exact reference image">
    <image id="exact-layout-image" x="0" y="0" width="1774" height="887"
           preserveAspectRatio="none" href="${pngUri}"/>
  </g>
</svg>`;

const layered = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
     xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
     width="1774" height="887" viewBox="0 0 1774 887">
  <title>IPR method figure - exact reference with editable vector layers</title>
  <desc>The visible layer is the exact supplied PNG. Hide it and show the editable-vector layer to edit individual labels, arrows, frames and images.</desc>
  <g id="editable-vector-reconstruction"
     inkscape:groupmode="layer"
     inkscape:label="Editable vector reconstruction - SHOW TO EDIT"
     style="display:none">
${vectorInner}
  </g>
  <g id="exact-reference-locked"
     inkscape:groupmode="layer"
     inkscape:label="Exact supplied figure - HIDE TO EDIT"
     sodipodi:insensitive="true">
    <image id="exact-layout-reference" x="0" y="0" width="1774" height="887"
           preserveAspectRatio="none" href="${pngUri}"/>
  </g>
</svg>`;

await Promise.all([
  fs.writeFile(exactSvg, exact, "utf8"),
  fs.writeFile(layeredSvg, layered, "utf8"),
  fs.copyFile(vectorSvg, vectorNamedSvg),
]);

console.log(JSON.stringify({ exactSvg, layeredSvg, vectorNamedSvg }, null, 2));

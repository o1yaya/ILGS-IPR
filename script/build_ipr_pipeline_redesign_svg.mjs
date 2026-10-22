import fs from "node:fs/promises";
import path from "node:path";
import { execFileSync } from "node:child_process";

const workspace = "D:\\PycharmProjects\\PythonProject\\ILGS_release-main";
const outDir = path.join(workspace, "outputs", "pipeline_redesign_20261009");
const assetDir = path.join(outDir, "source_assets");
const output = path.join(outDir, "ILGS_IPR_pipeline_redesign_editable.svg");

const files = {
  rgb: "D:\\downloads\\ipr_noise_examples_20261008\\blue_sofa\\best\\rgb.png",
  identity: "D:\\downloads\\ipr_noise_examples_20261008\\blue_sofa\\best\\identity_ids_labeled.png",
  gptLayout: "C:\\Users\\hp\\.codex\\generated_images\\019e6412-dcce-7710-90c5-d9c2607741f1\\exec-8fae9659-411d-4f0d-abd2-2fdaf29571f9.png",
};

await fs.mkdir(assetDir, { recursive: true });
for (const [key, file] of Object.entries(files)) {
  await fs.copyFile(file, path.join(assetDir, `${key}${path.extname(file).toLowerCase()}`));
}

execFileSync("powershell.exe", [
  "-NoProfile", "-ExecutionPolicy", "Bypass",
  "-File", path.join(workspace, "script", "crop_official_pipeline_gpt_assets.ps1"),
  "-Source", files.gptLayout, "-OutputDir", assetDir,
], { stdio: "inherit" });

async function dataUri(file) {
  const bytes = await fs.readFile(file);
  const ext = path.extname(file).toLowerCase();
  const mime = ext === ".jpg" || ext === ".jpeg" ? "image/jpeg" : "image/png";
  return `data:${mime};base64,${bytes.toString("base64")}`;
}

const raster = {
  rgb: files.rgb,
  identity: path.join(assetDir, "identity_labels.png"),
  clip: path.join(assetDir, "clip_features.png"),
  gaussian: path.join(assetDir, "gaussian_field.png"),
  language: path.join(assetDir, "language_feature.png"),
  outlier: path.join(assetDir, "outlier_mask.png"),
  cleanup: path.join(assetDir, "ipr_cleanup.png"),
  semantic: path.join(assetDir, "ipr_semantic.png"),
  area: path.join(assetDir, "ipr_area.png"),
  clean: path.join(assetDir, "ipr_clean_labels.png"),
  reliability: path.join(assetDir, "ipr_reliability.png"),
};
const im = Object.fromEntries(await Promise.all(
  Object.entries(raster).map(async ([key, file]) => [key, await dataUri(file)]),
));

const svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
     width="1800" height="760" viewBox="0 0 1800 760">
  <title>ILGS with Identity-Preserving Reliability</title>
  <desc>A compact four-stage pipeline emphasizing where IPR enters ILGS and how clean labels and reliability weights affect identity optimization.</desc>
  <metadata>Images are embedded. Text, paths, frames, loss blocks, badges, and arrows are editable SVG elements.</metadata>
  <defs>
    <marker id="arr-dark" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto" markerUnits="strokeWidth"><path d="M0 0L9 4.5L0 9Z" fill="#21313c"/></marker>
    <marker id="arr-orange" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto" markerUnits="strokeWidth"><path d="M0 0L9 4.5L0 9Z" fill="#e87518"/></marker>
    <marker id="arr-teal" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto" markerUnits="strokeWidth"><path d="M0 0L9 4.5L0 9Z" fill="#087b6a"/></marker>
    <marker id="arr-red" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto" markerUnits="strokeWidth"><path d="M0 0L9 4.5L0 9Z" fill="#d63d45"/></marker>
    <clipPath id="in-rgb"><rect x="49" y="122" width="216" height="126" rx="4"/></clipPath>
    <clipPath id="in-id"><rect x="49" y="326" width="216" height="126" rx="4"/></clipPath>
    <clipPath id="in-clip"><rect x="49" y="530" width="216" height="126" rx="4"/></clipPath>
    <clipPath id="opt-id-p"><rect x="1324" y="151" width="122" height="92" rx="3"/></clipPath>
    <clipPath id="opt-id-t"><rect x="1629" y="151" width="122" height="92" rx="3"/></clipPath>
    <clipPath id="opt-lang-p"><rect x="1324" y="354" width="122" height="92" rx="3"/></clipPath>
    <clipPath id="opt-lang-t"><rect x="1629" y="354" width="122" height="92" rx="3"/></clipPath>
    <clipPath id="opt-rgb-p"><rect x="1324" y="557" width="122" height="92" rx="3"/></clipPath>
    <clipPath id="opt-rgb-t"><rect x="1629" y="557" width="122" height="92" rx="3"/></clipPath>
    <style><![CDATA[
      text { font-family: Arial, Helvetica, sans-serif; letter-spacing: 0; }
      .stage-title { font-size: 22px; font-weight: 700; fill: #18303d; }
      .panel-label { font-size: 14px; font-weight: 700; fill: #22323d; }
      .small { font-size: 11.5px; fill: #334650; }
      .tiny { font-size: 10.5px; fill: #455965; }
      .panel { stroke-width: 1.7; }
    ]]></style>
  </defs>

  <g id="background" inkscape:groupmode="layer" inkscape:label="Background">
    <rect width="1800" height="760" fill="#ffffff"/>
  </g>

  <g id="stage-panels" inkscape:groupmode="layer" inkscape:label="Stage panels">
    <rect class="panel" x="24" y="46" width="270" height="668" rx="8" fill="#f5f6f7" stroke="#dce2e6"/>
    <rect class="panel" x="309" y="46" width="510" height="668" rx="8" fill="#fff8ef" stroke="#ef9a4e" stroke-width="2.2"/>
    <rect class="panel" x="834" y="46" width="450" height="668" rx="8" fill="#eff6fd" stroke="#ccdeed"/>
    <rect class="panel" x="1299" y="46" width="477" height="668" rx="8" fill="#eff8ec" stroke="#cfe2c7"/>
  </g>

  <g id="stage-headings" inkscape:groupmode="layer" inkscape:label="Stage headings">
    <circle cx="52" cy="78" r="18" fill="#344955"/><text x="52" y="85" text-anchor="middle" fill="#fff" font-size="20" font-weight="700">1</text>
    <text class="stage-title" x="79" y="85">Input supervision</text>
    <circle cx="337" cy="78" r="18" fill="#e87518"/><text x="337" y="85" text-anchor="middle" fill="#fff" font-size="20" font-weight="700">2</text>
    <text class="stage-title" x="364" y="85">Identity-Preserving Reliability</text>
    <circle cx="862" cy="78" r="18" fill="#27699b"/><text x="862" y="85" text-anchor="middle" fill="#fff" font-size="20" font-weight="700">3</text>
    <text class="stage-title" x="889" y="85">Gaussian learning</text>
    <circle cx="1327" cy="78" r="18" fill="#24765d"/><text x="1327" y="85" text-anchor="middle" fill="#fff" font-size="20" font-weight="700">4</text>
    <text class="stage-title" x="1354" y="85">Joint optimization</text>
  </g>

  <g id="inputs" inkscape:groupmode="layer" inkscape:label="Input supervision">
    <image x="49" y="122" width="216" height="126" preserveAspectRatio="xMidYMid slice" clip-path="url(#in-rgb)" xlink:href="${im.rgb}"/>
    <rect x="49" y="122" width="216" height="126" rx="4" fill="none" stroke="#bfcbd2"/>
    <text class="panel-label" x="157" y="271" text-anchor="middle">RGB images</text>
    <image x="49" y="326" width="216" height="126" preserveAspectRatio="xMidYMid slice" clip-path="url(#in-id)" xlink:href="${im.identity}"/>
    <rect x="49" y="326" width="216" height="126" rx="4" fill="none" stroke="#bfcbd2"/>
    <text class="panel-label" x="157" y="475" text-anchor="middle">Noisy identity labels</text>
    <image x="49" y="530" width="216" height="126" preserveAspectRatio="xMidYMid slice" clip-path="url(#in-clip)" xlink:href="${im.clip}"/>
    <rect x="49" y="530" width="216" height="126" rx="4" fill="none" stroke="#bfcbd2"/>
    <text class="panel-label" x="157" y="679" text-anchor="middle">CLIP features</text>
  </g>

  <g id="ipr" inkscape:groupmode="layer" inkscape:label="IPR evidence and outputs">
    <text class="panel-label" x="395" y="119" text-anchor="middle" fill="#a3510d">Cleanup</text>
    <text class="panel-label" x="564" y="119" text-anchor="middle" fill="#a3510d">Semantic</text>
    <text class="panel-label" x="733" y="119" text-anchor="middle" fill="#a3510d">Area prior</text>
    <image x="329" y="132" width="132" height="104" preserveAspectRatio="xMidYMid slice" xlink:href="${im.cleanup}"/>
    <rect x="329" y="132" width="132" height="104" fill="none" stroke="#ef9a4e"/>
    <image x="498" y="132" width="132" height="104" preserveAspectRatio="xMidYMid slice" xlink:href="${im.semantic}"/>
    <rect x="498" y="132" width="132" height="104" fill="none" stroke="#ef9a4e"/>
    <image x="667" y="132" width="132" height="104" preserveAspectRatio="xMidYMid slice" xlink:href="${im.area}"/>
    <rect x="667" y="132" width="132" height="104" fill="none" stroke="#ef9a4e"/>

    <path d="M395 241 V266 H552" fill="none" stroke="#e87518" stroke-width="2.1"/>
    <path d="M733 241 V266 H576" fill="none" stroke="#e87518" stroke-width="2.1"/>
    <path d="M564 241 V272" fill="none" stroke="#e87518" stroke-width="2.1" marker-end="url(#arr-orange)"/>
    <rect x="375" y="278" width="378" height="50" rx="6" fill="#fff0df" stroke="#e87518" stroke-width="1.6"/>
    <text x="564" y="309" text-anchor="middle" fill="#9b4b0c" font-size="16" font-weight="700">pixel reliability estimation</text>

    <text class="panel-label" x="435" y="365" text-anchor="middle" fill="#a3510d">Clean labels Y′</text>
    <text class="panel-label" x="693" y="365" text-anchor="middle" fill="#087b6a">Reliability W</text>
    <image x="337" y="379" width="196" height="145" preserveAspectRatio="xMidYMid slice" xlink:href="${im.clean}"/>
    <rect x="337" y="379" width="196" height="145" rx="4" fill="none" stroke="#e87518" stroke-width="2"/>
    <image x="595" y="379" width="196" height="145" preserveAspectRatio="xMidYMid slice" xlink:href="${im.reliability}"/>
    <rect x="595" y="379" width="196" height="145" rx="4" fill="none" stroke="#087b6a" stroke-width="2"/>
    <path d="M564 328 V350 H435 V371" fill="none" stroke="#e87518" stroke-width="2.2" marker-end="url(#arr-orange)"/>
    <path d="M564 328 V350 H693 V371" fill="none" stroke="#087b6a" stroke-width="2.2" marker-end="url(#arr-teal)"/>

    <rect x="337" y="568" width="454" height="72" rx="6" fill="#ffffff" stroke="#efc89f"/>
    <circle cx="383" cy="604" r="17" fill="#ffe1bf"/><path d="M374 604 L381 611 L393 596" fill="none" stroke="#b85d0d" stroke-width="3"/>
    <text class="panel-label" x="410" y="600">preserve anchors</text>
    <circle cx="596" cy="604" r="17" fill="#d8f0e9"/><path d="M586 604 H606" stroke="#087b6a" stroke-width="3"/><path d="M596 594 V614" stroke="#087b6a" stroke-width="3"/>
    <text class="panel-label" x="623" y="600">suppress noisy pixels</text>
    <text class="small" x="564" y="627" text-anchor="middle">identity labels stay discrete; reliability remains continuous</text>
  </g>

  <g id="gaussian" inkscape:groupmode="layer" inkscape:label="Identity-aware Gaussian field">
    <image x="858" y="117" width="402" height="381" preserveAspectRatio="xMidYMid meet" xlink:href="${im.gaussian}"/>
    <rect x="858" y="117" width="402" height="381" fill="none" stroke="#b8d0e2"/>
    <text class="small" x="1059" y="519" text-anchor="middle">Identity-aware language Gaussian field</text>

    <rect x="868" y="551" width="382" height="105" rx="6" fill="#ffffff" stroke="#9ebbd0" stroke-width="1.4"/>
    <rect x="869" y="552" width="127" height="103" fill="#f2f4f5"/>
    <rect x="996" y="552" width="127" height="103" fill="#e7f2fc"/>
    <rect x="1123" y="552" width="126" height="103" fill="#fff0bf"/>
    <text class="panel-label" x="932" y="600" text-anchor="middle">appearance</text>
    <text class="panel-label" x="1060" y="600" text-anchor="middle">language</text>
    <text class="panel-label" x="1186" y="600" text-anchor="middle">identity</text>
    <text class="tiny" x="932" y="625" text-anchor="middle">color + geometry</text>
    <text class="tiny" x="1060" y="625" text-anchor="middle">CLIP-aligned</text>
    <text class="tiny" x="1186" y="625" text-anchor="middle">confidence-weighted</text>
  </g>

  <g id="optimization" inkscape:groupmode="layer" inkscape:label="Optimization branches">
    <image x="1324" y="151" width="122" height="92" preserveAspectRatio="xMidYMid slice" clip-path="url(#opt-id-p)" xlink:href="${im.identity}"/>
    <rect x="1324" y="151" width="122" height="92" fill="none" stroke="#a9c59f"/>
    <text class="small" x="1385" y="263" text-anchor="middle">Rasterized identity</text>
    <rect x="1490" y="168" width="105" height="62" rx="6" fill="#fff" stroke="#d55d30" stroke-width="1.8"/>
    <text class="panel-label" x="1542" y="194" text-anchor="middle">Weighted</text>
    <text class="panel-label" x="1542" y="214" text-anchor="middle">identity loss</text>
    <image x="1629" y="151" width="122" height="92" preserveAspectRatio="xMidYMid slice" clip-path="url(#opt-id-t)" xlink:href="${im.clean}"/>
    <rect x="1629" y="151" width="122" height="92" fill="none" stroke="#a9c59f"/>
    <text class="small" x="1690" y="263" text-anchor="middle">Clean labels Y′</text>
    <path d="M1446 197 H1478" fill="none" stroke="#d63d45" stroke-width="2.4" marker-end="url(#arr-red)"/>
    <path d="M1629 197 H1607" fill="none" stroke="#d63d45" stroke-width="2.4" marker-end="url(#arr-red)"/>

    <rect x="1495" y="105" width="95" height="45" rx="5" fill="#fff8dc" stroke="#d7b448"/>
    <image x="1502" y="112" width="38" height="30" preserveAspectRatio="xMidYMid slice" xlink:href="${im.outlier}"/>
    <text class="tiny" x="1564" y="124" text-anchor="middle" font-weight="700">Outlier</text>
    <text class="tiny" x="1564" y="138" text-anchor="middle" font-weight="700">mask</text>
    <path d="M1542 150 V161" fill="none" stroke="#21313c" stroke-width="2" marker-end="url(#arr-dark)"/>

    <image x="1324" y="354" width="122" height="92" preserveAspectRatio="xMidYMid slice" clip-path="url(#opt-lang-p)" xlink:href="${im.language}"/>
    <rect x="1324" y="354" width="122" height="92" fill="none" stroke="#a9c59f"/>
    <text class="small" x="1385" y="466" text-anchor="middle">Rasterized language</text>
    <rect x="1490" y="371" width="105" height="62" rx="6" fill="#fff" stroke="#3f5968" stroke-width="1.6"/>
    <text class="panel-label" x="1542" y="408" text-anchor="middle">Language loss</text>
    <image x="1629" y="354" width="122" height="92" preserveAspectRatio="xMidYMid slice" clip-path="url(#opt-lang-t)" xlink:href="${im.clip}"/>
    <rect x="1629" y="354" width="122" height="92" fill="none" stroke="#a9c59f"/>
    <text class="small" x="1690" y="466" text-anchor="middle">CLIP feature map</text>
    <path d="M1446 400 H1478" fill="none" stroke="#d63d45" stroke-width="2.4" marker-end="url(#arr-red)"/>
    <path d="M1629 400 H1607" fill="none" stroke="#d63d45" stroke-width="2.4" marker-end="url(#arr-red)"/>

    <image x="1324" y="557" width="122" height="92" preserveAspectRatio="xMidYMid slice" clip-path="url(#opt-rgb-p)" xlink:href="${im.rgb}"/>
    <rect x="1324" y="557" width="122" height="92" fill="none" stroke="#a9c59f"/>
    <text class="small" x="1385" y="669" text-anchor="middle">Rendered RGB</text>
    <rect x="1490" y="574" width="105" height="62" rx="6" fill="#fff" stroke="#3f5968" stroke-width="1.6"/>
    <text class="panel-label" x="1542" y="611" text-anchor="middle">RGB loss</text>
    <image x="1629" y="557" width="122" height="92" preserveAspectRatio="xMidYMid slice" clip-path="url(#opt-rgb-t)" xlink:href="${im.rgb}"/>
    <rect x="1629" y="557" width="122" height="92" fill="none" stroke="#a9c59f"/>
    <text class="small" x="1690" y="669" text-anchor="middle">Ground-truth RGB</text>
    <path d="M1446 603 H1478" fill="none" stroke="#d63d45" stroke-width="2.4" marker-end="url(#arr-red)"/>
    <path d="M1629 603 H1607" fill="none" stroke="#d63d45" stroke-width="2.4" marker-end="url(#arr-red)"/>
  </g>

  <g id="connections" inkscape:groupmode="layer" inkscape:label="Pipeline connections">
    <path d="M265 389 H302 V184 H321" fill="none" stroke="#21313c" stroke-width="2.4" marker-end="url(#arr-dark)"/>
    <path d="M265 185 H300 V732 H820 V302 H846" fill="none" stroke="#21313c" stroke-width="2.4" marker-end="url(#arr-dark)"/>
    <path d="M265 593 H300" fill="none" stroke="#21313c" stroke-width="2.4"/>
    <path d="M820 732 H1060 V663" fill="none" stroke="#21313c" stroke-width="2.4" marker-end="url(#arr-dark)"/>

    <path d="M1250 603 H1289 V197 H1312" fill="none" stroke="#21313c" stroke-width="2.4" marker-end="url(#arr-dark)"/>
    <path d="M1289 400 H1312" fill="none" stroke="#21313c" stroke-width="2.4" marker-end="url(#arr-dark)"/>
    <path d="M1289 603 H1312" fill="none" stroke="#21313c" stroke-width="2.4" marker-end="url(#arr-dark)"/>

    <path d="M337 451 H316 V99 H1690 V139" fill="none" stroke="#e87518" stroke-width="2.8" marker-end="url(#arr-orange)"/>
    <rect x="1190" y="88" width="42" height="23" rx="4" fill="#fff"/>
    <text x="1211" y="105" text-anchor="middle" fill="#a84f0b" font-size="16" font-weight="700">Y′</text>

    <path d="M791 451 H821 V696 H1763 V280 H1542 V242" fill="none" stroke="#087b6a" stroke-width="2.8" marker-end="url(#arr-teal)"/>
    <rect x="1190" y="684" width="42" height="23" rx="4" fill="#fff"/>
    <text x="1211" y="701" text-anchor="middle" fill="#087b6a" font-size="16" font-weight="700">W</text>
  </g>
</svg>`;

await fs.writeFile(output, svg, "utf8");
console.log(output);

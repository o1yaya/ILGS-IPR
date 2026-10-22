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
     width="1800" height="700" viewBox="0 0 1800 700">
  <title>Compact ILGS-IPR pipeline</title>
  <desc>Four-stage publication pipeline with compact spacing and corrected supervision, rendering, and loss connections.</desc>
  <metadata>Raster panels are embedded. Text, arrows, frames, loss blocks, and badges are editable vectors.</metadata>
  <defs>
    <marker id="a-dark" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto" markerUnits="strokeWidth"><path d="M0 0L9 4.5L0 9Z" fill="#243640"/></marker>
    <marker id="a-orange" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto" markerUnits="strokeWidth"><path d="M0 0L9 4.5L0 9Z" fill="#e87518"/></marker>
    <marker id="a-teal" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto" markerUnits="strokeWidth"><path d="M0 0L9 4.5L0 9Z" fill="#087b6a"/></marker>
    <marker id="a-red" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto" markerUnits="strokeWidth"><path d="M0 0L9 4.5L0 9Z" fill="#d63d45"/></marker>
    <clipPath id="i1"><rect x="51" y="112" width="216" height="112" rx="4"/></clipPath>
    <clipPath id="i2"><rect x="51" y="292" width="216" height="112" rx="4"/></clipPath>
    <clipPath id="i3"><rect x="51" y="472" width="216" height="112" rx="4"/></clipPath>
    <clipPath id="p1"><rect x="1324" y="174" width="122" height="86" rx="3"/></clipPath>
    <clipPath id="t1"><rect x="1629" y="174" width="122" height="86" rx="3"/></clipPath>
    <clipPath id="p2"><rect x="1360" y="348" width="130" height="76" rx="3"/></clipPath>
    <clipPath id="t2"><rect x="1360" y="530" width="130" height="64" rx="3"/></clipPath>
    <clipPath id="p3"><rect x="1585" y="348" width="130" height="76" rx="3"/></clipPath>
    <clipPath id="t3"><rect x="1585" y="530" width="130" height="64" rx="3"/></clipPath>
    <style><![CDATA[
      text { font-family: Arial, Helvetica, sans-serif; letter-spacing: 0; }
      .title { font-size: 22px; font-weight: 700; fill: #18303d; }
      .label { font-size: 14px; font-weight: 700; fill: #263a45; }
      .small { font-size: 11.5px; fill: #3c515c; }
      .tiny { font-size: 10.5px; fill: #4a5e68; }
    ]]></style>
  </defs>

  <g id="background" inkscape:groupmode="layer" inkscape:label="Background">
    <rect width="1800" height="700" fill="#ffffff"/>
  </g>
  <g id="panels" inkscape:groupmode="layer" inkscape:label="Stage panels">
    <rect x="24" y="42" width="270" height="616" rx="8" fill="#f5f6f7" stroke="#dce2e6" stroke-width="1.7"/>
    <rect x="309" y="42" width="510" height="616" rx="8" fill="#fff8ef" stroke="#ef9a4e" stroke-width="2.1"/>
    <rect x="834" y="42" width="450" height="616" rx="8" fill="#eff6fd" stroke="#ccdeed" stroke-width="1.7"/>
    <rect x="1299" y="42" width="477" height="616" rx="8" fill="#eff8ec" stroke="#cfe2c7" stroke-width="1.7"/>
  </g>

  <g id="headings" inkscape:groupmode="layer" inkscape:label="Stage headings">
    <circle cx="52" cy="75" r="18" fill="#344955"/><text x="52" y="82" text-anchor="middle" fill="#fff" font-size="20" font-weight="700">1</text><text class="title" x="79" y="82">Input supervision</text>
    <circle cx="337" cy="75" r="18" fill="#e87518"/><text x="337" y="82" text-anchor="middle" fill="#fff" font-size="20" font-weight="700">2</text><text class="title" x="364" y="82">Identity-Preserving Reliability</text>
    <circle cx="862" cy="75" r="18" fill="#27699b"/><text x="862" y="82" text-anchor="middle" fill="#fff" font-size="20" font-weight="700">3</text><text class="title" x="889" y="82">Gaussian learning</text>
    <circle cx="1327" cy="75" r="18" fill="#24765d"/><text x="1327" y="82" text-anchor="middle" fill="#fff" font-size="20" font-weight="700">4</text><text class="title" x="1354" y="82">Joint optimization</text>
  </g>

  <g id="inputs" inkscape:groupmode="layer" inkscape:label="Input supervision">
    <image x="51" y="112" width="216" height="112" preserveAspectRatio="xMidYMid slice" clip-path="url(#i1)" xlink:href="${im.rgb}"/><rect x="51" y="112" width="216" height="112" rx="4" fill="none" stroke="#bdc9d0"/><text class="label" x="159" y="247" text-anchor="middle">RGB images</text>
    <image x="51" y="292" width="216" height="112" preserveAspectRatio="xMidYMid slice" clip-path="url(#i2)" xlink:href="${im.identity}"/><rect x="51" y="292" width="216" height="112" rx="4" fill="none" stroke="#bdc9d0"/><text class="label" x="159" y="427" text-anchor="middle">Noisy identity labels</text>
    <image x="51" y="472" width="216" height="112" preserveAspectRatio="xMidYMid slice" clip-path="url(#i3)" xlink:href="${im.clip}"/><rect x="51" y="472" width="216" height="112" rx="4" fill="none" stroke="#bdc9d0"/><text class="label" x="159" y="607" text-anchor="middle">CLIP features</text>
  </g>

  <g id="ipr" inkscape:groupmode="layer" inkscape:label="IPR module">
    <text class="label" x="395" y="113" text-anchor="middle" fill="#a3510d">Cleanup</text><text class="label" x="564" y="113" text-anchor="middle" fill="#a3510d">Semantic reliability</text><text class="label" x="733" y="113" text-anchor="middle" fill="#a3510d">Area prior</text>
    <image x="329" y="124" width="132" height="88" preserveAspectRatio="xMidYMid slice" xlink:href="${im.cleanup}"/><rect x="329" y="124" width="132" height="88" fill="none" stroke="#ef9a4e"/>
    <image x="498" y="124" width="132" height="88" preserveAspectRatio="xMidYMid slice" xlink:href="${im.semantic}"/><rect x="498" y="124" width="132" height="88" fill="none" stroke="#ef9a4e"/>
    <image x="667" y="124" width="132" height="88" preserveAspectRatio="xMidYMid slice" xlink:href="${im.area}"/><rect x="667" y="124" width="132" height="88" fill="none" stroke="#ef9a4e"/>
    <path d="M395 217 V238 H552" fill="none" stroke="#e87518" stroke-width="2"/><path d="M733 217 V238 H576" fill="none" stroke="#e87518" stroke-width="2"/><path d="M564 217 V244" fill="none" stroke="#e87518" stroke-width="2" marker-end="url(#a-orange)"/>
    <rect x="381" y="250" width="366" height="44" rx="6" fill="#fff0df" stroke="#e87518" stroke-width="1.5"/><text x="564" y="278" text-anchor="middle" fill="#9b4b0c" font-size="16" font-weight="700">Pixel reliability estimation</text>
    <path d="M564 294 V317 H435 V333" fill="none" stroke="#e87518" stroke-width="2.2" marker-end="url(#a-orange)"/><path d="M564 294 V317 H693 V333" fill="none" stroke="#087b6a" stroke-width="2.2" marker-end="url(#a-teal)"/>
    <image x="337" y="342" width="196" height="125" preserveAspectRatio="xMidYMid slice" xlink:href="${im.clean}"/><rect x="337" y="342" width="196" height="125" rx="4" fill="none" stroke="#e87518" stroke-width="2"/>
    <image x="595" y="342" width="196" height="125" preserveAspectRatio="xMidYMid slice" xlink:href="${im.reliability}"/><rect x="595" y="342" width="196" height="125" rx="4" fill="none" stroke="#087b6a" stroke-width="2"/>
    <text class="label" x="435" y="490" text-anchor="middle" fill="#a3510d">Clean labels Y′</text><text class="label" x="693" y="490" text-anchor="middle" fill="#087b6a">Reliability W</text>
    <rect x="337" y="515" width="215" height="58" rx="6" fill="#fff" stroke="#efc89f"/><circle cx="370" cy="544" r="15" fill="#ffe1bf"/><path d="M362 544L368 550L379 536" fill="none" stroke="#b85d0d" stroke-width="3"/><text class="label" x="394" y="549">Preserve identity anchors</text>
    <rect x="570" y="515" width="221" height="58" rx="6" fill="#fff" stroke="#b7d9cf"/><circle cx="603" cy="544" r="15" fill="#d8f0e9"/><path d="M594 544H612M603 535V553" stroke="#087b6a" stroke-width="3"/><text class="label" x="627" y="549">Suppress noisy pixels</text>
  </g>

  <g id="gaussian" inkscape:groupmode="layer" inkscape:label="Gaussian field">
    <image x="858" y="111" width="402" height="340" preserveAspectRatio="xMidYMid meet" xlink:href="${im.gaussian}"/><rect x="858" y="111" width="402" height="340" fill="none" stroke="#b8d0e2"/>
    <text class="small" x="1059" y="473" text-anchor="middle">Identity-aware language Gaussian field</text>
    <rect x="868" y="503" width="382" height="94" rx="6" fill="#fff" stroke="#9ebbd0" stroke-width="1.4"/><rect x="869" y="504" width="127" height="92" fill="#f2f4f5"/><rect x="996" y="504" width="127" height="92" fill="#e7f2fc"/><rect x="1123" y="504" width="126" height="92" fill="#fff0bf"/>
    <text class="label" x="932" y="546" text-anchor="middle">appearance</text><text class="label" x="1060" y="546" text-anchor="middle">language</text><text class="label" x="1186" y="546" text-anchor="middle">identity</text>
    <text class="tiny" x="932" y="570" text-anchor="middle">color + geometry</text><text class="tiny" x="1060" y="570" text-anchor="middle">CLIP-aligned</text><text class="tiny" x="1186" y="570" text-anchor="middle">confidence-weighted</text>
  </g>

  <g id="optimization" inkscape:groupmode="layer" inkscape:label="Optimization branches">
    <image x="1324" y="174" width="122" height="86" preserveAspectRatio="xMidYMid slice" clip-path="url(#p1)" xlink:href="${im.identity}"/><rect x="1324" y="174" width="122" height="86" fill="none" stroke="#a9c59f"/><text class="small" x="1385" y="280" text-anchor="middle">Rasterized identity</text>
    <rect x="1490" y="185" width="105" height="64" rx="6" fill="#fff" stroke="#d55d30" stroke-width="1.8"/><text class="label" x="1542" y="212" text-anchor="middle">Weighted</text><text class="label" x="1542" y="232" text-anchor="middle">identity loss</text>
    <image x="1629" y="174" width="122" height="86" preserveAspectRatio="xMidYMid slice" clip-path="url(#t1)" xlink:href="${im.clean}"/><rect x="1629" y="174" width="122" height="86" fill="none" stroke="#a9c59f"/><text class="small" x="1690" y="280" text-anchor="middle">Clean labels Y′</text><path d="M1446 217H1478" fill="none" stroke="#d63d45" stroke-width="2.4" marker-end="url(#a-red)"/><path d="M1629 217H1607" fill="none" stroke="#d63d45" stroke-width="2.4" marker-end="url(#a-red)"/>
    <rect x="1320" y="103" width="166" height="62" rx="6" fill="#fff8dc" stroke="#d7b448" stroke-width="1.4"/><image x="1328" y="110" width="80" height="48" preserveAspectRatio="xMidYMid slice" xlink:href="${im.outlier}"/><rect x="1328" y="110" width="80" height="48" fill="none" stroke="#d7b448"/><text class="small" x="1447" y="127" text-anchor="middle" font-weight="700">Outlier</text><text class="small" x="1447" y="144" text-anchor="middle" font-weight="700">mask</text><path d="M1486 134H1542V178" fill="none" stroke="#243640" stroke-width="2.2" marker-end="url(#a-dark)"/>

    <rect x="1320" y="303" width="210" height="313" rx="6" fill="#ffffff" fill-opacity="0.72" stroke="#c8d9c1"/>
    <text class="label" x="1425" y="332" text-anchor="middle" fill="#24634d">Language branch</text>
    <image x="1360" y="348" width="130" height="76" preserveAspectRatio="xMidYMid slice" clip-path="url(#p2)" xlink:href="${im.language}"/><rect x="1360" y="348" width="130" height="76" fill="none" stroke="#a9c59f"/><text class="tiny" x="1425" y="440" text-anchor="middle">Rasterized language</text>
    <path d="M1425 445V453" fill="none" stroke="#d63d45" stroke-width="2.2" marker-end="url(#a-red)"/><rect x="1372" y="460" width="106" height="52" rx="6" fill="#fff" stroke="#3f5968" stroke-width="1.6"/><text class="label" x="1425" y="491" text-anchor="middle">Language loss</text><path d="M1425 512V523" fill="none" stroke="#d63d45" stroke-width="2.2" marker-end="url(#a-red)"/>
    <image x="1360" y="530" width="130" height="64" preserveAspectRatio="xMidYMid slice" clip-path="url(#t2)" xlink:href="${im.clip}"/><rect x="1360" y="530" width="130" height="64" fill="none" stroke="#a9c59f"/><text class="tiny" x="1425" y="610" text-anchor="middle">CLIP feature map</text>

    <rect x="1545" y="303" width="210" height="313" rx="6" fill="#ffffff" fill-opacity="0.72" stroke="#c8d9c1"/>
    <text class="label" x="1650" y="332" text-anchor="middle" fill="#24634d">RGB branch</text>
    <image x="1585" y="348" width="130" height="76" preserveAspectRatio="xMidYMid slice" clip-path="url(#p3)" xlink:href="${im.rgb}"/><rect x="1585" y="348" width="130" height="76" fill="none" stroke="#a9c59f"/><text class="tiny" x="1650" y="440" text-anchor="middle">Rendered RGB</text>
    <path d="M1650 445V453" fill="none" stroke="#d63d45" stroke-width="2.2" marker-end="url(#a-red)"/><rect x="1597" y="460" width="106" height="52" rx="6" fill="#fff" stroke="#3f5968" stroke-width="1.6"/><text class="label" x="1650" y="491" text-anchor="middle">RGB loss</text><path d="M1650 512V523" fill="none" stroke="#d63d45" stroke-width="2.2" marker-end="url(#a-red)"/>
    <image x="1585" y="530" width="130" height="64" preserveAspectRatio="xMidYMid slice" clip-path="url(#t3)" xlink:href="${im.rgb}"/><rect x="1585" y="530" width="130" height="64" fill="none" stroke="#a9c59f"/><text class="tiny" x="1650" y="610" text-anchor="middle">Ground-truth RGB</text>
  </g>

  <g id="connections" inkscape:groupmode="layer" inkscape:label="Corrected pipeline connections">
    <path d="M267 348H302V174H321" fill="none" stroke="#243640" stroke-width="2.5" marker-end="url(#a-dark)"/>
    <path d="M747 272H846" fill="none" stroke="#243640" stroke-width="2.5" marker-end="url(#a-dark)"/>
    <path d="M1250 550H1288V217H1312" fill="none" stroke="#243640" stroke-width="2.5" marker-end="url(#a-dark)"/>
    <path d="M1288 292H1348V386H1352" fill="none" stroke="#243640" stroke-width="2.5" marker-end="url(#a-dark)"/><path d="M1348 292H1573V386H1577" fill="none" stroke="#243640" stroke-width="2.5" marker-end="url(#a-dark)"/>
    <text class="tiny" x="1272" y="301" text-anchor="middle" transform="rotate(-90 1272 301)">rasterize</text>
    <path d="M337 404H320V98H1690V166" fill="none" stroke="#e87518" stroke-width="2.8" marker-end="url(#a-orange)"/><rect x="1192" y="87" width="42" height="22" rx="4" fill="#fff"/><text x="1213" y="103" text-anchor="middle" fill="#a84f0b" font-size="16" font-weight="700">Y′</text>
    <path d="M791 404H820V626H1762V268H1542V261" fill="none" stroke="#087b6a" stroke-width="2.8" marker-end="url(#a-teal)"/><rect x="1192" y="615" width="42" height="22" rx="4" fill="#fff"/><text x="1213" y="631" text-anchor="middle" fill="#087b6a" font-size="16" font-weight="700">W</text>
  </g>
</svg>`;

await fs.writeFile(output, svg, "utf8");
console.log(output);

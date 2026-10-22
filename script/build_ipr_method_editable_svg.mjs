import fs from "node:fs/promises";
import path from "node:path";

const workspace = "D:\\PycharmProjects\\PythonProject\\ILGS_release-main";
const assetDir = path.join(workspace, "outputs", "method_figure_compact_highlight_20261008", "ppt_assets");
const queryDir = "D:\\downloads\\ipr_method_assets\\bench_20261007_203512_313407\\query\\ipr\\2";
const outDir = path.join(workspace, "outputs", "method_figure_compact_highlight_20261008");
const output = path.join(outDir, "IPR_method_editable.svg");

const esc = (value) => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;");

async function dataUri(file) {
  const bytes = await fs.readFile(file);
  const ext = path.extname(file).toLowerCase();
  const mime = ext === ".jpg" || ext === ".jpeg" ? "image/jpeg" : "image/png";
  return `data:${mime};base64,${bytes.toString("base64")}`;
}

const images = {
  rgb: await dataUri(path.join(assetDir, "input_rgb.jpg")),
  noisy: await dataUri(path.join(assetDir, "noisy_identity_map.png")),
  cleanup: await dataUri(path.join(assetDir, "structure_cleanup.png")),
  semantic: await dataUri(path.join(assetDir, "semantic_evidence.png")),
  area: await dataUri(path.join(assetDir, "area_prior.png")),
  reliability: await dataUri(path.join(assetDir, "reliability_map.png")),
  novel: await dataUri(path.join(queryDir, "render_rgb.png")),
  language: await dataUri(path.join(queryDir, "language_latent_rgb.png")),
  identity: await dataUri(path.join(queryDir, "identity_labels.png")),
  similarity: await dataUri(path.join(queryDir, "segment_heatmap.png")),
  official: await dataUri(path.join(assetDir, "official_noisy_prediction.png")),
  ipr: await dataUri(path.join(assetDir, "ipr_refined_prediction.png")),
};

const svg = `<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
     width="1774" height="887" viewBox="0 0 1774 887">
  <title>Identity Pseudo-label Refinement for ILGS</title>
  <desc>Fully editable method diagram. All text, frames, arrows and annotations are SVG vector objects; experimental images are individually embedded image objects.</desc>
  <defs>
    <linearGradient id="greenCircle" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#16987f"/>
      <stop offset="1" stop-color="#006c5e"/>
    </linearGradient>
    <linearGradient id="blueCircle" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#2080c8"/>
      <stop offset="1" stop-color="#07528e"/>
    </linearGradient>
    <linearGradient id="panelBlue" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#f8fcff"/>
      <stop offset="1" stop-color="#edf8fd"/>
    </linearGradient>
    <filter id="softShadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#8fa1ad" flood-opacity="0.18"/>
    </filter>
    <marker id="arrowGreen" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto" markerUnits="strokeWidth">
      <path d="M0,0 L10,5 L0,10 Z" fill="#007d68"/>
    </marker>
    <marker id="arrowYellow" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto" markerUnits="strokeWidth">
      <path d="M0,0 L9,4.5 L0,9 Z" fill="#ffe026"/>
    </marker>
    <marker id="arrowRed" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto" markerUnits="strokeWidth">
      <path d="M0,0 L10,5 L0,10 Z" fill="#c3132d"/>
    </marker>
    <style><![CDATA[
      text { font-family: Arial, Helvetica, sans-serif; }
      .title { font-size: 25px; font-weight: 700; }
      .subtitle { font-size: 19px; font-weight: 700; }
      .label { font-size: 18px; font-weight: 400; }
      .small { font-size: 16px; }
      .caption { font-size: 22px; font-weight: 700; }
      .panel { stroke-width: 2.4; rx: 8; ry: 8; }
      .image-border-red { fill: none; stroke: #c3132d; stroke-width: 4; }
      .image-border-green { fill: none; stroke: #007d68; stroke-width: 4; }
      .image-border-blue { fill: none; stroke: #0b5a92; stroke-width: 3; }
      .green-line { fill: none; stroke: #007d68; stroke-width: 3.2; marker-end: url(#arrowGreen); }
      .green-dash { fill: none; stroke: #007d68; stroke-width: 3.2; stroke-dasharray: 8 6; marker-end: url(#arrowGreen); }
    ]]></style>
  </defs>

  <g id="background" inkscape:groupmode="layer" inkscape:label="Background">
    <rect x="0" y="0" width="1774" height="887" fill="#ffffff"/>
  </g>

  <g id="stage-1" inkscape:groupmode="layer" inkscape:label="1 Input noisy identity labels">
    <rect class="panel" x="18" y="86" width="385" height="714" fill="#fffdfd" stroke="#c3132d" filter="url(#softShadow)"/>
    <circle id="stage1-number-circle" cx="58" cy="122" r="28" fill="#cf0e2c"/>
    <text id="stage1-number" x="58" y="132" text-anchor="middle" fill="#ffffff" font-size="31" font-weight="700">1</text>
    <text id="stage1-title" x="106" y="132" fill="#c3132d" font-size="23" font-weight="700">Input: noisy identity labels</text>

    <image id="stage1-rgb" x="33" y="164" width="356" height="286" preserveAspectRatio="xMidYMid slice" href="${images.rgb}"/>
    <rect class="image-border-red" x="33" y="164" width="356" height="286"/>
    <rect id="rgb-label-bg" x="43" y="178" width="72" height="41" rx="6" fill="#292d30" stroke="#ffffff" stroke-width="4"/>
    <text id="rgb-label" x="79" y="208" text-anchor="middle" fill="#ffffff" font-size="28" font-weight="700">RGB</text>

    <image id="stage1-noisy-label-map" x="33" y="474" width="356" height="269" preserveAspectRatio="none" href="${images.noisy}"/>
    <rect class="image-border-red" x="33" y="474" width="356" height="269"/>

    <rect id="wall-id-label-bg" x="168" y="489" width="117" height="36" rx="5" fill="#a91831" stroke="#ffe026" stroke-width="4"/>
    <text id="wall-id-label" x="226.5" y="515" text-anchor="middle" fill="#ffffff" font-size="21" font-weight="700">ID 6: wall</text>
    <path id="wall-id-arrow" d="M168 507 L137 515" fill="none" stroke="#ffe026" stroke-width="4" marker-end="url(#arrowYellow)"/>

    <rect id="floor-id-label-bg" x="171" y="688" width="126" height="38" rx="5" fill="#a91831" stroke="#ffe026" stroke-width="4"/>
    <text id="floor-id-label" x="234" y="715" text-anchor="middle" fill="#ffffff" font-size="21" font-weight="700">ID 4: floor</text>
    <path id="floor-id-arrow" d="M171 704 L150 679" fill="none" stroke="#ffe026" stroke-width="4" marker-end="url(#arrowYellow)"/>

    <text id="stage1-summary" x="210" y="775" text-anchor="middle" fill="#c3132d" font-size="23" font-weight="700">Background IDs occupy 85.6%</text>
  </g>

  <g id="stage1-to-stage2" inkscape:groupmode="layer" inkscape:label="Arrow 1 to 2">
    <path d="M383 436 L417 436" fill="none" stroke="#c3132d" stroke-width="6" marker-end="url(#arrowRed)"/>
  </g>

  <g id="stage-2" inkscape:groupmode="layer" inkscape:label="2 Estimate pixel reliability">
    <rect class="panel" x="417" y="86" width="526" height="714" fill="#fbfffd" stroke="#007d68" filter="url(#softShadow)"/>
    <circle id="stage2-number-circle" cx="462" cy="122" r="29" fill="url(#greenCircle)"/>
    <text id="stage2-number" x="462" y="133" text-anchor="middle" fill="#ffffff" font-size="31" font-weight="700">2</text>
    <text id="stage2-title" class="title" x="520" y="135" fill="#006e60">IPR: estimate pixel reliability</text>
    <rect id="stage2-inner-panel" x="425" y="165" width="510" height="619" rx="8" fill="#ffffff" stroke="#007d68" stroke-width="2.2"/>

    <text id="cleanup-label" class="label" x="510" y="220" text-anchor="middle">Structure cleanup</text>
    <text id="semantic-label" class="label" x="683" y="220" text-anchor="middle">Semantic evidence</text>
    <text id="area-label" class="label" x="850" y="220" text-anchor="middle">Area prior</text>

    <image id="structure-cleanup-image" x="435" y="241" width="152" height="198" preserveAspectRatio="none" href="${images.cleanup}"/>
    <image id="semantic-evidence-image" x="598" y="241" width="169" height="198" preserveAspectRatio="none" href="${images.semantic}"/>
    <image id="area-prior-image" x="775" y="241" width="153" height="198" preserveAspectRatio="none" href="${images.area}"/>

    <path id="cleanup-to-weight" class="green-line" d="M505 440 L505 472 L671 526"/>
    <path id="semantic-to-weight" class="green-line" d="M681 440 L681 518"/>
    <path id="area-to-weight" class="green-line" d="M853 440 L853 472 L695 526"/>

    <image id="reliability-map-image" x="545" y="527" width="270" height="172" preserveAspectRatio="none" href="${images.reliability}"/>
    <rect class="image-border-green" x="545" y="527" width="270" height="172"/>
    <text id="reliability-map-label" x="680" y="735" text-anchor="middle" fill="#006e60" font-size="27" font-weight="700">Reliability map W(p)</text>
  </g>

  <g id="stage2-to-stage3" inkscape:groupmode="layer" inkscape:label="Arrow 2 to 3">
    <path d="M933 436 L963 436" fill="none" stroke="#007d68" stroke-width="6" marker-end="url(#arrowGreen)"/>
  </g>

  <g id="stage-3" inkscape:groupmode="layer" inkscape:label="3 Confidence-weighted ILGS">
    <rect class="panel" x="955" y="86" width="432" height="714" fill="#ffffff" stroke="#007d68" filter="url(#softShadow)"/>
    <circle id="stage3-number-circle" cx="998" cy="122" r="29" fill="url(#greenCircle)"/>
    <text id="stage3-number" x="998" y="133" text-anchor="middle" fill="#ffffff" font-size="31" font-weight="700">3</text>
    <text id="stage3-title-line1" x="1208" y="117" text-anchor="middle" fill="#075b57" font-size="22" font-weight="700">Confidence-weighted ILGS</text>
    <text id="stage3-title-line2" x="1208" y="146" text-anchor="middle" fill="#075b57" font-size="22" font-weight="700">identity-aware 3D Gaussian field</text>

    <image id="stage3-novel-view" x="1029" y="168" width="299" height="218" preserveAspectRatio="xMidYMid slice" href="${images.novel}"/>
    <text id="novel-view-label" x="1178.5" y="414" text-anchor="middle" fill="#111111" font-size="20">Novel view</text>
    <path id="novel-to-loss" class="green-dash" d="M1171 418 L1171 457"/>

    <rect id="weighted-loss-box" x="986" y="458" width="373" height="80" rx="9" fill="#ffffff" stroke="#007d68" stroke-width="2.5"/>
    <text id="weighted-loss-label" x="1172.5" y="487" text-anchor="middle" fill="#006e60" font-size="20" font-weight="700">3  Weight identity loss:</text>
    <g id="weighted-loss-formula" fill="#111111" font-style="italic">
      <text x="1094" y="520" font-size="24">L</text>
      <text x="1108" y="527" font-size="14">id</text>
      <text x="1124" y="504" font-size="14">IPR</text>
      <text x="1153" y="520" font-size="24">= W(p)L</text>
      <text x="1249" y="527" font-size="14">id</text>
    </g>

    <rect id="stage3-map-panel" x="962" y="553" width="419" height="231" rx="7" fill="#ffffff" stroke="#007d68" stroke-width="2.3"/>
    <text id="language-map-label" class="small" x="1036" y="584" text-anchor="middle">Language feature</text>
    <text id="identity-map-label" class="small" x="1169" y="584" text-anchor="middle">Identity feature</text>
    <text id="similarity-map-label" class="small" x="1306" y="584" text-anchor="middle">Segment similarity</text>
    <image id="language-feature-map" x="974" y="602" width="123" height="131" preserveAspectRatio="none" href="${images.language}"/>
    <image id="identity-feature-map" x="1108" y="602" width="123" height="131" preserveAspectRatio="none" href="${images.identity}"/>
    <image id="segment-similarity-map" x="1244" y="602" width="123" height="131" preserveAspectRatio="none" href="${images.similarity}"/>
    <text id="query-label" x="1171.5" y="769" text-anchor="middle" fill="#111111" font-size="21" font-weight="700">Text query  →  &quot;Portuguese egg tart&quot;</text>
  </g>

  <g id="stage3-to-stage4" inkscape:groupmode="layer" inkscape:label="Arrow 3 to 4">
    <path d="M1375 436 L1407 436" fill="none" stroke="#007d68" stroke-width="6" marker-end="url(#arrowGreen)"/>
  </g>

  <g id="stage-4" inkscape:groupmode="layer" inkscape:label="4 Output cleaner segment">
    <rect class="panel" x="1401" y="86" width="357" height="714" fill="url(#panelBlue)" stroke="#0b5a92" filter="url(#softShadow)"/>
    <circle id="stage4-number-circle" cx="1439" cy="122" r="28" fill="url(#blueCircle)"/>
    <text id="stage4-number" x="1439" y="133" text-anchor="middle" fill="#ffffff" font-size="31" font-weight="700">4</text>
    <text id="stage4-title" x="1602" y="132" text-anchor="middle" fill="#174f84" font-size="23" font-weight="700">Output: cleaner segment</text>

    <text id="official-result-label" x="1579" y="180" text-anchor="middle" fill="#c3132d" font-size="19" font-weight="700">Official ILGS: noisy mask (area 4.68%)</text>
    <image id="official-noisy-mask" x="1418" y="199" width="323" height="232" preserveAspectRatio="none" href="${images.official}"/>
    <rect class="image-border-red" x="1418" y="199" width="323" height="232"/>
    <path id="official-to-ipr-arrow" d="M1579 435 L1579 472" fill="none" stroke="#007d68" stroke-width="4" marker-end="url(#arrowGreen)"/>

    <text id="ipr-result-label" x="1579" y="498" text-anchor="middle" fill="#006e60" font-size="19" font-weight="700">+ IPR: target mask (area 1.08%)</text>
    <image id="ipr-target-mask" x="1418" y="516" width="323" height="216" preserveAspectRatio="none" href="${images.ipr}"/>
    <rect class="image-border-green" x="1418" y="516" width="323" height="216"/>
    <text id="metric-gain" x="1579" y="775" text-anchor="middle" fill="#006e60" font-size="23" font-weight="700">+5.06 mIoU / +5.53 mBIoU</text>
  </g>
</svg>`;

await fs.mkdir(outDir, { recursive: true });
await fs.writeFile(output, svg, "utf8");
console.log(output);

import fs from "node:fs/promises";
import path from "node:path";

const workspace = "D:\\PycharmProjects\\PythonProject\\ILGS_release-main";
const assetDir = path.join(workspace, "outputs", "method_figure_compact_highlight_20261008", "ppt_assets");
const queryDir = "D:\\downloads\\ipr_method_assets\\bench_20261007_203512_313407\\query\\ipr\\2";
const outDir = path.join(workspace, "outputs", "method_figure_compact_highlight_20261008");
const output = path.join(outDir, "IPR_method_gpt_image2_top_pipeline_editable.svg");
const aiEmbeddedOutput = path.join(outDir, "IPR_method_gpt_image2_top_pipeline_AI_embedded.svg");
const aiPackageDir = path.join(outDir, "IPR_method_gpt_image2_top_pipeline_AI_package");
const aiAssetDir = path.join(aiPackageDir, "assets");
const aiLinkedOutput = path.join(aiPackageDir, "IPR_method_gpt_image2_top_pipeline_AI.svg");

async function dataUri(file) {
  const bytes = await fs.readFile(file);
  const ext = path.extname(file).toLowerCase();
  const mime = ext === ".jpg" || ext === ".jpeg" ? "image/jpeg" : "image/png";
  return `data:${mime};base64,${bytes.toString("base64")}`;
}

const sources = {
  rgb: path.join(assetDir, "input_rgb.jpg"),
  noisy: path.join(assetDir, "noisy_identity_map.png"),
  cleanup: path.join(assetDir, "structure_cleanup.png"),
  semantic: path.join(assetDir, "semantic_evidence.png"),
  area: path.join(assetDir, "area_prior.png"),
  reliability: path.join(assetDir, "reliability_map.png"),
  language: path.join(queryDir, "language_latent_rgb.png"),
  identity: path.join(queryDir, "identity_labels.png"),
  similarity: path.join(queryDir, "segment_heatmap.png"),
  official: path.join(assetDir, "official_noisy_prediction.png"),
  ipr: path.join(assetDir, "ipr_refined_prediction.png"),
};
const im = Object.fromEntries(await Promise.all(
  Object.entries(sources).map(async ([key, file]) => [key, await dataUri(file)]),
));

const svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
     width="1776" height="887" viewBox="0 0 1776 887">
  <title>Editable IPR top-pipeline method figure</title>
  <desc>Editable vector reconstruction of the GPT Image 2 layout. Text, panels, arrows, formulas, and all experimental images are independent objects.</desc>
  <defs>
    <filter id="shadow" x="-10%" y="-10%" width="120%" height="125%">
      <feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#71828a" flood-opacity="0.22"/>
    </filter>
    <clipPath id="clip-novel"><rect x="44" y="104" width="375" height="236"/></clipPath>
    <clipPath id="clip-language"><rect x="468" y="141" width="342" height="183"/></clipPath>
    <clipPath id="clip-identity"><rect x="829" y="141" width="347" height="183"/></clipPath>
    <clipPath id="clip-similarity"><rect x="1195" y="141" width="349" height="183"/></clipPath>
    <clipPath id="clip-stage1-rgb"><rect x="54" y="454" width="373" height="168"/></clipPath>
    <clipPath id="clip-stage1-noisy"><rect x="54" y="634" width="373" height="163"/></clipPath>
    <clipPath id="clip-cleanup"><rect x="514" y="486" width="240" height="135"/></clipPath>
    <clipPath id="clip-semantic"><rect x="768" y="486" width="233" height="135"/></clipPath>
    <clipPath id="clip-area"><rect x="1016" y="486" width="239" height="135"/></clipPath>
    <clipPath id="clip-reliability"><rect x="785" y="661" width="196" height="95"/></clipPath>
    <clipPath id="clip-official"><rect x="1335" y="486" width="389" height="140"/></clipPath>
    <clipPath id="clip-ipr"><rect x="1335" y="661" width="389" height="147"/></clipPath>
    <style><![CDATA[
      text { font-family: Arial, Helvetica, sans-serif; }
      .stage-title { font-size: 28px; font-weight: 700; }
      .section-label { font-size: 17px; font-weight: 700; }
      .panel { fill: #ffffff; stroke-width: 3; rx: 8; ry: 8; }
      .thin-panel { fill: #ffffff; stroke: #00705c; stroke-width: 2; rx: 5; ry: 5; }
      .red-border { fill: none; stroke: #d2112d; stroke-width: 4; }
      .green-border { fill: none; stroke: #006f59; stroke-width: 4; }
    ]]></style>
  </defs>

  <g id="background" inkscape:groupmode="layer" inkscape:label="Background">
    <rect x="0" y="0" width="1776" height="887" fill="#ffffff"/>
  </g>

  <g id="stage-3-top" inkscape:groupmode="layer" inkscape:label="3 Confidence-weighted ILGS">
    <rect class="panel" x="24" y="37" width="1558" height="340" stroke="#006f59" filter="url(#shadow)"/>
    <rect id="stage3-number-bg" x="45" y="44" width="70" height="55" rx="6" fill="#00725d"/>
    <text id="stage3-number" x="80" y="85" text-anchor="middle" fill="#ffffff" font-size="40" font-weight="700">3</text>
    <text id="stage3-title" x="133" y="82" fill="#064d41" font-size="38" font-weight="700">Confidence-weighted ILGS identity-aware 3D Gaussian field</text>

    <image id="novel-view-image" x="44" y="104" width="375" height="236" preserveAspectRatio="xMidYMid slice" clip-path="url(#clip-novel)" href="${im.rgb}"/>
    <text id="novel-view-label" x="231.5" y="363" text-anchor="middle" font-size="24" font-weight="700">Novel view</text>
    <path id="novel-view-separator" d="M432 104 L432 371" fill="none" stroke="#3e9b85" stroke-width="2" stroke-dasharray="8 7"/>

    <rect id="feature-map-panel" class="thin-panel" x="450" y="99" width="1113" height="246"/>
    <text id="language-feature-label" class="section-label" x="639" y="132" text-anchor="middle">Language feature</text>
    <text id="identity-feature-label" class="section-label" x="1003" y="132" text-anchor="middle">Identity feature</text>
    <text id="segment-similarity-label" class="section-label" x="1370" y="132" text-anchor="middle">Segment similarity</text>
    <image id="language-feature-image" x="468" y="141" width="342" height="183" preserveAspectRatio="none" clip-path="url(#clip-language)" href="${im.language}"/>
    <image id="identity-feature-image" x="829" y="141" width="347" height="183" preserveAspectRatio="none" clip-path="url(#clip-identity)" href="${im.identity}"/>
    <image id="segment-similarity-image" x="1195" y="141" width="349" height="183" preserveAspectRatio="none" clip-path="url(#clip-similarity)" href="${im.similarity}"/>
    <text id="text-query" x="1008" y="362" text-anchor="middle" font-size="25" font-weight="700">Text query  →  &quot;Portuguese egg tart&quot;</text>
  </g>

  <g id="weighted-loss" inkscape:groupmode="layer" inkscape:label="Weight identity loss">
    <path id="loss-arrow-top-line" d="M1582 145 L1659 145 L1659 209" fill="none" stroke="#006f59" stroke-width="3" stroke-linecap="square" stroke-linejoin="miter"/>
    <polygon id="loss-arrow-top-head" points="1648,208 1670,208 1659,228" fill="#006f59"/>
    <text id="loss-title" x="1594" y="262" fill="#064d41" font-size="17" font-weight="700">Weight identity loss:</text>
    <text id="loss-formula" x="1595" y="300" fill="#064d41" font-size="23" font-style="italic">Lᵢdᴵᴾᴿ = W(p)Lᵢd</text>
  </g>

  <g id="stage-1-input" inkscape:groupmode="layer" inkscape:label="1 Input noisy identity labels">
    <rect class="panel" x="24" y="397" width="438" height="464" stroke="#d2112d" filter="url(#shadow)"/>
    <rect id="stage1-number-bg" x="29" y="405" width="55" height="44" rx="3" fill="#d2112d"/>
    <text id="stage1-number" x="56.5" y="439" text-anchor="middle" fill="#ffffff" font-size="33" font-weight="700">1</text>
    <text id="stage1-title" x="100" y="438" fill="#d2112d" font-size="26" font-weight="700">Input: noisy identity labels</text>

    <image id="stage1-rgb-image" x="54" y="454" width="373" height="168" preserveAspectRatio="none" clip-path="url(#clip-stage1-rgb)" href="${im.rgb}"/>
    <rect class="red-border" x="54" y="454" width="373" height="168"/>
    <rect id="rgb-label-bg" x="63" y="462" width="72" height="37" rx="4" fill="#292d30" stroke="#ffffff" stroke-width="3"/>
    <text id="rgb-label" x="99" y="489" text-anchor="middle" fill="#ffffff" font-size="24" font-weight="700">RGB</text>

    <image id="stage1-noisy-map" x="54" y="634" width="373" height="163" preserveAspectRatio="none" clip-path="url(#clip-stage1-noisy)" href="${im.noisy}"/>
    <rect class="red-border" x="54" y="634" width="373" height="163"/>
    <rect id="wall-label-bg" x="182" y="638" width="105" height="31" rx="4" fill="#d2112d" stroke="#ffe225" stroke-width="3"/>
    <text id="wall-label" x="234.5" y="661" text-anchor="middle" fill="#ffffff" font-size="17" font-weight="700">ID 6: wall</text>
    <path id="wall-label-arrow-line" d="M182 654 L166 661" fill="none" stroke="#ffe225" stroke-width="3"/>
    <polygon id="wall-label-arrow-head" points="169,651 156,665 174,667" fill="#ffe225"/>
    <rect id="floor-label-bg" x="198" y="766" width="112" height="29" rx="4" fill="#d2112d" stroke="#ffe225" stroke-width="3"/>
    <text id="floor-label" x="254" y="787" text-anchor="middle" fill="#ffffff" font-size="17" font-weight="700">ID 4: floor</text>
    <path id="floor-label-arrow-line" d="M198 779 L181 775" fill="none" stroke="#ffe225" stroke-width="3"/>
    <polygon id="floor-label-arrow-head" points="181,767 170,772 178,783" fill="#ffe225"/>
    <text id="stage1-summary" x="243" y="837" text-anchor="middle" fill="#d2112d" font-size="21" font-weight="700">Background IDs occupy 85.6%</text>
  </g>

  <g id="stage-2-ipr" inkscape:groupmode="layer" inkscape:label="2 Estimate pixel reliability">
    <rect class="panel" x="484" y="397" width="801" height="464" stroke="#006f59" filter="url(#shadow)"/>
    <rect id="stage2-number-bg" x="490" y="405" width="62" height="44" rx="3" fill="#006f59"/>
    <text id="stage2-number" x="521" y="439" text-anchor="middle" fill="#ffffff" font-size="33" font-weight="700">2</text>
    <text id="stage2-title" x="573" y="438" fill="#064d41" font-size="27" font-weight="700">IPR: estimate pixel reliability</text>

    <rect id="stage2-inner" class="thin-panel" x="503" y="451" width="762" height="349"/>
    <text id="cleanup-label" class="section-label" x="634" y="477" text-anchor="middle">Structure cleanup</text>
    <text id="semantic-label" class="section-label" x="883" y="477" text-anchor="middle">Semantic evidence</text>
    <text id="area-label" class="section-label" x="1135" y="477" text-anchor="middle">Area prior</text>

    <image id="cleanup-image" x="514" y="486" width="240" height="135" preserveAspectRatio="none" clip-path="url(#clip-cleanup)" href="${im.cleanup}"/>
    <image id="semantic-image" x="768" y="486" width="233" height="135" preserveAspectRatio="none" clip-path="url(#clip-semantic)" href="${im.semantic}"/>
    <image id="area-image" x="1016" y="486" width="239" height="135" preserveAspectRatio="none" clip-path="url(#clip-area)" href="${im.area}"/>

    <path id="cleanup-to-reliability" d="M625 625 L625 640 L873 657" fill="none" stroke="#006f59" stroke-width="2.5" stroke-linecap="square" stroke-linejoin="miter"/>
    <path id="semantic-to-reliability" d="M883 625 L883 657" fill="none" stroke="#006f59" stroke-width="2.5"/>
    <path id="area-to-reliability" d="M1139 625 L1139 640 L893 657" fill="none" stroke="#006f59" stroke-width="2.5" stroke-linecap="square" stroke-linejoin="miter"/>
    <polygon id="evidence-to-reliability-head" points="872,649 894,649 883,669" fill="#006f59"/>

    <image id="reliability-map-image" x="785" y="661" width="196" height="95" preserveAspectRatio="none" clip-path="url(#clip-reliability)" href="${im.reliability}"/>
    <rect class="green-border" x="785" y="661" width="196" height="95"/>
    <text id="reliability-label" x="883" y="785" text-anchor="middle" font-size="20" font-weight="700">Reliability map W(p)</text>

    <rect id="process-strip" x="503" y="812" width="762" height="41" rx="4" fill="#c7edc4" stroke="#55a865" stroke-width="2"/>
    <text id="process-strip-text" x="884" y="840" text-anchor="middle" fill="#0b2519" font-size="20" font-weight="700">preserve identity anchors  →  estimate W(p)  →  suppress noisy pixels</text>

    <path id="ipr-to-top-line" d="M886 397 L886 386" fill="none" stroke="#006f59" stroke-width="4"/>
    <polygon id="ipr-to-top-head" points="875,386 897,386 886,366" fill="#006f59"/>
  </g>

  <g id="stage-4-output" inkscape:groupmode="layer" inkscape:label="4 Output cleaner segment">
    <rect class="panel" x="1307" y="397" width="443" height="464" stroke="#174f84" fill="#f4fbff" filter="url(#shadow)"/>
    <rect id="stage4-number-bg" x="1313" y="405" width="62" height="44" rx="3" fill="#174f84"/>
    <text id="stage4-number" x="1344" y="439" text-anchor="middle" fill="#ffffff" font-size="33" font-weight="700">4</text>
    <text id="stage4-title" x="1393" y="438" fill="#174f84" font-size="27" font-weight="700">Output: cleaner segment</text>

    <text id="official-label" x="1528.5" y="477" text-anchor="middle" fill="#d2112d" font-size="18" font-weight="700">Official ILGS: noisy mask (area 4.68%)</text>
    <image id="official-image" x="1335" y="486" width="389" height="140" preserveAspectRatio="none" clip-path="url(#clip-official)" href="${im.official}"/>
    <rect class="red-border" x="1335" y="486" width="389" height="140"/>

    <text id="ipr-label" x="1528.5" y="653" text-anchor="middle" fill="#006f59" font-size="18" font-weight="700">+ IPR: target mask (area 1.08%)</text>
    <image id="ipr-image" x="1335" y="661" width="389" height="147" preserveAspectRatio="none" clip-path="url(#clip-ipr)" href="${im.ipr}"/>
    <rect class="green-border" x="1335" y="661" width="389" height="147"/>
    <text id="metric-gain" x="1528.5" y="839" text-anchor="middle" fill="#174f84" font-size="23" font-weight="700">+5.06 mIoU / +5.53 mBIoU</text>
  </g>

  <g id="main-flow-arrows" inkscape:groupmode="layer" inkscape:label="Main flow arrows">
    <path id="stage1-stage2-arrow-line" d="M427 551 L464 551" fill="none" stroke="#d2112d" stroke-width="5"/>
    <polygon id="stage1-stage2-arrow-head" points="462,535 486,551 462,567" fill="#d2112d"/>
    <path id="stage2-stage4-arrow-line" d="M1264 551 L1288 551" fill="none" stroke="#006f59" stroke-width="5"/>
    <polygon id="stage2-stage4-arrow-head" points="1286,535 1310,551 1286,567" fill="#006f59"/>
    <path id="loss-arrow-output-front" d="M1659 317 L1659 378" fill="none" stroke="#006f59" stroke-width="3"/>
    <polygon id="loss-arrow-output-head" points="1648,376 1670,376 1659,397" fill="#006f59"/>
  </g>
</svg>`;

await fs.mkdir(outDir, { recursive: true });

// Keep standard SVG 2 `href` data URIs so Inkscape and browsers treat every
// raster panel as part of this single self-contained document.
const embeddedCompat = svg;
await fs.writeFile(output, embeddedCompat, "utf8");
await fs.writeFile(aiEmbeddedOutput, embeddedCompat, "utf8");

// Also provide a conventional linked-assets package. This is the most stable
// Illustrator workflow and lets users relink or embed images from Links panel.
await fs.mkdir(aiAssetDir, { recursive: true });
const linkedNames = {};
for (const [key, file] of Object.entries(sources)) {
  const name = `${key}${path.extname(file).toLowerCase()}`;
  linkedNames[key] = `assets/${name}`;
  await fs.copyFile(file, path.join(aiAssetDir, name));
}
let linkedSvg = svg;
for (const [key, uri] of Object.entries(im)) {
  linkedSvg = linkedSvg.replaceAll(uri, linkedNames[key]);
}
linkedSvg = linkedSvg.replace(
  / href="(assets\/[^"]+)"/g,
  ' xlink:href="$1"',
);
await fs.writeFile(aiLinkedOutput, linkedSvg, "utf8");

console.log(JSON.stringify({ output, aiEmbeddedOutput, aiLinkedOutput, aiAssetDir }, null, 2));

import fs from "node:fs/promises";
import path from "node:path";
import { execFileSync } from "node:child_process";

const workspace = "D:\\PycharmProjects\\PythonProject\\ILGS_release-main";
const outDir = path.join(workspace, "outputs", "pipeline_system_gpt_image2_20261009");
const assetDir = path.join(outDir, "source_assets");
const output = path.join(outDir, "ILGS_IPR_system_pipeline_editable.svg");

const source = {
  rgb: "D:\\downloads\\ipr_noise_examples_20261008\\blue_sofa\\best\\rgb.png",
  view2: path.join(workspace, "dataset", "3dovs", "blue_sofa", "images", "27.jpg"),
  identity: "D:\\downloads\\ipr_noise_examples_20261008\\blue_sofa\\best\\identity_ids_labeled.png",
  flagged: "D:\\downloads\\ipr_noise_examples_20261008\\blue_sofa\\best\\large_region_highlight.png",
  confidence: "D:\\downloads\\ipr_noise_examples_20261008\\blue_sofa\\best\\ipr_confidence.png",
  recovery: "D:\\downloads\\seed0_cases_v2\\fig_3dovs_recovery.png",
  layout: "C:\\Users\\hp\\.codex\\generated_images\\019e6412-dcce-7710-90c5-d9c2607741f1\\exec-0691a679-3ed9-47a2-bf67-3147b32478b3.png",
};

await fs.mkdir(assetDir, { recursive: true });
for (const [key, file] of Object.entries(source)) {
  await fs.copyFile(file, path.join(assetDir, `${key}${path.extname(file).toLowerCase()}`));
}

execFileSync("powershell.exe", [
  "-NoProfile",
  "-ExecutionPolicy", "Bypass",
  "-File", path.join(workspace, "script", "crop_ipr_pipeline_recovery.ps1"),
  "-Source", source.recovery,
  "-OutputDir", assetDir,
], { stdio: "inherit" });

async function dataUri(file) {
  const bytes = await fs.readFile(file);
  const ext = path.extname(file).toLowerCase();
  const mime = ext === ".jpg" || ext === ".jpeg" ? "image/jpeg" : "image/png";
  return `data:${mime};base64,${bytes.toString("base64")}`;
}

const rasterSource = {
  rgb: source.rgb,
  view2: source.view2,
  identity: source.identity,
  flagged: source.flagged,
  confidence: source.confidence,
  baseline: path.join(assetDir, "blue_sofa_controlled_ilgs.png"),
  ipr: path.join(assetDir, "blue_sofa_ipr.png"),
};

const im = Object.fromEntries(await Promise.all(
  Object.entries(rasterSource)
    .map(async ([key, file]) => [key, await dataUri(file)]),
));

const svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
     width="1800" height="920" viewBox="0 0 1800 920">
  <title>ILGS-IPR system pipeline</title>
  <desc>Editable system-level pipeline using the 3D-OVS blue_sofa scene. Raster evidence is embedded; all labels, arrows, equations, and panel geometry remain editable.</desc>
  <metadata>
    Layout concept: GPT Image 2, then reconstructed as editable SVG.
    Scene assets: 3D-OVS blue_sofa, frame 25; recovery example: sunglasses, view 4.
    Final IPR uses structure cleanup, OpenCLIP semantic evidence, and a large-region prior without a per-view visibility multiplier.
  </metadata>
  <defs>
    <marker id="arrow-blue" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto" markerUnits="strokeWidth">
      <path d="M0,0 L10,5 L0,10 z" fill="#2f5f8f"/>
    </marker>
    <marker id="arrow-amber" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto" markerUnits="strokeWidth">
      <path d="M0,0 L10,5 L0,10 z" fill="#d97706"/>
    </marker>
    <marker id="arrow-teal" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto" markerUnits="strokeWidth">
      <path d="M0,0 L10,5 L0,10 z" fill="#087d68"/>
    </marker>
    <clipPath id="clip-s1-rear"><rect x="96" y="164" width="238" height="164" rx="5"/></clipPath>
    <clipPath id="clip-s1-front"><rect x="44" y="205" width="268" height="184" rx="5"/></clipPath>
    <clipPath id="clip-s1-id"><rect x="43" y="456" width="312" height="234" rx="4"/></clipPath>
    <clipPath id="clip-flagged"><rect x="412" y="222" width="205" height="154" rx="4"/></clipPath>
    <clipPath id="clip-conf"><rect x="641" y="222" width="205" height="154" rx="4"/></clipPath>
    <clipPath id="clip-train-rgb"><rect x="899" y="201" width="190" height="143" rx="4"/></clipPath>
    <clipPath id="clip-train-id"><rect x="1101" y="201" width="190" height="143" rx="4"/></clipPath>
    <style><![CDATA[
      text { font-family: Arial, Helvetica, sans-serif; letter-spacing: 0; }
      .math { font-family: Cambria Math, STIX Two Math, Times New Roman, serif; font-style: italic; }
      .panel { fill: #ffffff; stroke-width: 2.2; }
      .stage { font-size: 22px; font-weight: 700; }
      .label { font-size: 15px; font-weight: 700; }
      .body { font-size: 13px; }
      .small { font-size: 11.5px; }
      .tiny { font-size: 10px; }
    ]]></style>
  </defs>

  <g id="background" inkscape:groupmode="layer" inkscape:label="Background and title">
    <rect width="1800" height="920" fill="#ffffff"/>
    <text x="30" y="47" fill="#14364d" font-size="34" font-weight="700">ILGS with Identity-Preserving Reliability (IPR)</text>
    <text x="31" y="74" fill="#587184" font-size="15.5">A system-level view: estimate reliability offline, weight identity supervision during training, and keep text-query inference unchanged</text>
    <path d="M28 88 H1772" stroke="#d5e0e8" stroke-width="1.5"/>
  </g>

  <g id="flow-arrows" inkscape:groupmode="layer" inkscape:label="Main flow arrows">
    <path d="M372 426 H389" fill="none" stroke="#2f5f8f" stroke-width="4" marker-end="url(#arrow-blue)"/>
    <path d="M860 426 H877" fill="none" stroke="#d97706" stroke-width="4" marker-end="url(#arrow-amber)"/>
    <path d="M1308 426 H1325" fill="none" stroke="#087d68" stroke-width="4" marker-end="url(#arrow-teal)"/>
  </g>

  <g id="stage-1" inkscape:groupmode="layer" inkscape:label="1 Inputs">
    <rect class="panel" x="24" y="104" width="348" height="670" rx="9" stroke="#3f6f9f" fill="#f9fbfd"/>
    <circle cx="58" cy="139" r="24" fill="#255e93"/>
    <text x="58" y="148" text-anchor="middle" fill="#ffffff" font-size="26" font-weight="700">1</text>
    <text class="stage" x="94" y="147" fill="#174b78">Inputs</text>

    <image x="96" y="164" width="238" height="164" preserveAspectRatio="xMidYMid slice" clip-path="url(#clip-s1-rear)" xlink:href="${im.view2}"/>
    <rect x="96" y="164" width="238" height="164" rx="5" fill="none" stroke="#bed0df" stroke-width="1.5"/>
    <image x="44" y="205" width="268" height="184" preserveAspectRatio="xMidYMid slice" clip-path="url(#clip-s1-front)" xlink:href="${im.rgb}"/>
    <rect x="44" y="205" width="268" height="184" rx="5" fill="none" stroke="#3f6f9f" stroke-width="2"/>
    <rect x="53" y="214" width="77" height="26" rx="4" fill="#243746" fill-opacity="0.92"/>
    <text x="91.5" y="233" text-anchor="middle" fill="#ffffff" font-size="13" font-weight="700">MULTI-VIEW</text>
    <text class="label" x="198" y="413" text-anchor="middle" fill="#174b78">RGB images + calibrated cameras</text>

    <path d="M198 424 V445" fill="none" stroke="#3f6f9f" stroke-width="2.5" marker-end="url(#arrow-blue)"/>
    <image x="43" y="456" width="312" height="234" preserveAspectRatio="xMidYMid slice" clip-path="url(#clip-s1-id)" xlink:href="${im.identity}"/>
    <rect x="43" y="456" width="312" height="234" rx="4" fill="none" stroke="#d14454" stroke-width="2.2"/>
    <rect x="54" y="467" width="104" height="25" rx="4" fill="#b91c32"/>
    <text x="106" y="485" text-anchor="middle" fill="#ffffff" font-size="12.5" font-weight="700">NOISY LABELS</text>
    <text class="label" x="198" y="716" text-anchor="middle" fill="#b91c32">Identity supervision Y<tspan baseline-shift="sub" font-size="10">t</tspan></text>
    <text class="small" x="198" y="739" text-anchor="middle" fill="#637789">same identity vocabulary is retained</text>
  </g>

  <g id="stage-2" inkscape:groupmode="layer" inkscape:label="2 Offline IPR reliability">
    <rect class="panel" x="392" y="104" width="468" height="670" rx="9" stroke="#dc7a10" fill="#fffdf9"/>
    <circle cx="426" cy="139" r="24" fill="#d97706"/>
    <text x="426" y="148" text-anchor="middle" fill="#ffffff" font-size="26" font-weight="700">2</text>
    <text class="stage" x="462" y="147" fill="#b85e00">Offline IPR</text>
    <text class="small" x="840" y="145" text-anchor="end" fill="#9a5a13">no view-visibility multiplier</text>

    <g id="ipr-evidence-strip" inkscape:label="Reliability evidence">
      <rect x="411" y="168" width="128" height="37" rx="5" fill="#f5f8fb" stroke="#b7c8d7"/>
      <text class="small" x="475" y="191" text-anchor="middle" fill="#28485f" font-weight="700">Local coherence</text>
      <rect x="547" y="168" width="128" height="37" rx="5" fill="#eef9f5" stroke="#8fcbbd"/>
      <text class="small" x="611" y="191" text-anchor="middle" fill="#086c5a" font-weight="700">OpenCLIP semantics</text>
      <rect x="683" y="168" width="159" height="37" rx="5" fill="#fff3e3" stroke="#e8b66f"/>
      <text class="small" x="762.5" y="191" text-anchor="middle" fill="#a55a05" font-weight="700">Large-region prior</text>
    </g>

    <text class="label" x="514.5" y="216" text-anchor="middle" fill="#b91c32">Flag unreliable ID regions</text>
    <image x="412" y="222" width="205" height="154" preserveAspectRatio="xMidYMid slice" clip-path="url(#clip-flagged)" xlink:href="${im.flagged}"/>
    <rect x="412" y="222" width="205" height="154" rx="4" fill="none" stroke="#d14454" stroke-width="1.7"/>
    <text class="label" x="743.5" y="216" text-anchor="middle" fill="#087d68">Estimate pixel reliability</text>
    <image x="641" y="222" width="205" height="154" preserveAspectRatio="xMidYMid slice" clip-path="url(#clip-conf)" xlink:href="${im.confidence}"/>
    <rect x="641" y="222" width="205" height="154" rx="4" fill="none" stroke="#087d68" stroke-width="1.7"/>
    <path d="M619 299 H632" fill="none" stroke="#d97706" stroke-width="3" marker-end="url(#arrow-amber)"/>
    <text class="tiny" x="514.5" y="395" text-anchor="middle" fill="#b91c32">ID 4 covers 85.7% of the frame</text>
    <text class="tiny" x="743.5" y="395" text-anchor="middle" fill="#087d68">continuous confidence, not relabeling</text>

    <g id="ipr-funnel" inkscape:label="Reliability funnel">
      <path d="M475 420 H779 L735 474 H519 Z" fill="#fff1da" stroke="#dc7a10" stroke-width="1.8"/>
      <text class="body" x="627" y="445" text-anchor="middle" fill="#9a5500" font-weight="700">combine pixel evidence with object weight</text>
      <text class="small" x="627" y="463" text-anchor="middle" fill="#816347">trusted 1.00  ·  low semantic 0.65  ·  large mixed 0.35</text>
      <path d="M627 476 V500" fill="none" stroke="#d97706" stroke-width="2.6" marker-end="url(#arrow-amber)"/>
    </g>

    <rect x="430" y="510" width="394" height="105" rx="7" fill="#ffffff" stroke="#dc7a10" stroke-width="1.8"/>
    <text class="label" x="627" y="536" text-anchor="middle" fill="#9a5500">Pixel confidence</text>
    <text class="math" x="627" y="577" text-anchor="middle" fill="#18384c" font-size="25">
      <tspan>W</tspan><tspan baseline-shift="sub" font-size="15">t</tspan><tspan baseline-shift="baseline">(x) = clip(C</tspan><tspan baseline-shift="sub" font-size="15">t</tspan><tspan baseline-shift="baseline">(x) × w</tspan><tspan baseline-shift="sub" font-size="15">i</tspan><tspan baseline-shift="baseline">, 0.05, 1)</tspan>
    </text>
    <text class="small" x="627" y="600" text-anchor="middle" fill="#667b8b">low confidence suppresses supervision; identity indices are preserved</text>

    <rect x="430" y="637" width="394" height="91" rx="7" fill="#f2f8f5" stroke="#8fcbbd" stroke-width="1.4"/>
    <text class="label" x="627" y="665" text-anchor="middle" fill="#087d68">Offline outputs</text>
    <text class="body" x="627" y="692" text-anchor="middle" fill="#28485f">cleaned labels Y′<tspan baseline-shift="sub" font-size="9">t</tspan><tspan baseline-shift="baseline">  +  confidence map W</tspan><tspan baseline-shift="sub" font-size="9">t</tspan><tspan baseline-shift="baseline">(x)</tspan></text>
    <text class="small" x="627" y="713" text-anchor="middle" fill="#637789">computed once before ILGS optimization</text>
  </g>

  <g id="stage-3" inkscape:groupmode="layer" inkscape:label="3 Confidence-weighted ILGS training">
    <rect class="panel" x="880" y="104" width="428" height="670" rx="9" stroke="#159177" fill="#f9fdfb"/>
    <circle cx="914" cy="139" r="24" fill="#087d68"/>
    <text x="914" y="148" text-anchor="middle" fill="#ffffff" font-size="26" font-weight="700">3</text>
    <text class="stage" x="950" y="147" fill="#075f51">Weighted ILGS training</text>

    <text class="small" x="994" y="190" text-anchor="middle" fill="#29495f" font-weight="700">Rendered RGB</text>
    <text class="small" x="1196" y="190" text-anchor="middle" fill="#29495f" font-weight="700">Rendered identity feature</text>
    <image x="899" y="201" width="190" height="143" preserveAspectRatio="xMidYMid slice" clip-path="url(#clip-train-rgb)" xlink:href="${im.rgb}"/>
    <rect x="899" y="201" width="190" height="143" rx="4" fill="none" stroke="#86c8b8" stroke-width="1.5"/>
    <image x="1101" y="201" width="190" height="143" preserveAspectRatio="xMidYMid slice" clip-path="url(#clip-train-id)" xlink:href="${im.identity}"/>
    <rect x="1101" y="201" width="190" height="143" rx="4" fill="none" stroke="#86c8b8" stroke-width="1.5"/>
    <circle cx="1095" cy="272.5" r="17" fill="#ffffff" stroke="#159177" stroke-width="1.6"/>
    <text x="1095" y="281" text-anchor="middle" fill="#075f51" font-size="24" font-weight="700">+</text>
    <rect x="899" y="358" width="392" height="59" rx="6" fill="#edf8f4" stroke="#8fcbbd" stroke-width="1.3"/>
    <text class="label" x="1095" y="382" text-anchor="middle" fill="#075f51">Identity-aware 3D Gaussian field</text>
    <text class="small" x="1095" y="403" text-anchor="middle" fill="#5e7788">joint appearance, language, and identity optimization</text>
    <text class="small" x="1095" y="440" text-anchor="middle" fill="#087d68">only the 2D identity-classification term is reweighted</text>

    <g id="loss-inputs" inkscape:label="Loss inputs">
      <rect x="907" y="462" width="111" height="46" rx="6" fill="#f4f8fb" stroke="#b8c9d6"/>
      <text class="small" x="962.5" y="481" text-anchor="middle" fill="#29495f">cleaned label</text>
      <text class="math" x="962.5" y="499" text-anchor="middle" fill="#17364a" font-size="17">Y′<tspan baseline-shift="sub" font-size="11">t</tspan></text>
      <rect x="1039" y="462" width="111" height="46" rx="6" fill="#fff8e9" stroke="#e5bc72"/>
      <text class="small" x="1094.5" y="481" text-anchor="middle" fill="#7e5b18">validity mask</text>
      <text class="math" x="1094.5" y="499" text-anchor="middle" fill="#17364a" font-size="17">M<tspan baseline-shift="sub" font-size="11">t</tspan><tspan baseline-shift="baseline">(x)</tspan></text>
      <rect x="1171" y="462" width="111" height="46" rx="6" fill="#eef9f5" stroke="#8fcbbd"/>
      <text class="small" x="1226.5" y="481" text-anchor="middle" fill="#086c5a">IPR weight</text>
      <text class="math" x="1226.5" y="499" text-anchor="middle" fill="#17364a" font-size="17">W<tspan baseline-shift="sub" font-size="11">t</tspan><tspan baseline-shift="baseline">(x)</tspan></text>
    </g>

    <path d="M1095 512 V531" fill="none" stroke="#087d68" stroke-width="2.6" marker-end="url(#arrow-teal)"/>
    <rect x="900" y="542" width="390" height="147" rx="7" fill="#ffffff" stroke="#159177" stroke-width="1.8"/>
    <text class="label" x="1095" y="566" text-anchor="middle" fill="#075f51">Confidence-weighted identity loss</text>
    <text class="math" x="944" y="624" fill="#17364a" font-size="25">
      <tspan>L</tspan><tspan baseline-shift="sub" font-size="15">cls</tspan><tspan baseline-shift="super" font-size="15">IPR</tspan><tspan baseline-shift="baseline"> =</tspan>
    </text>
    <text class="math" x="1125" y="600" text-anchor="middle" fill="#17364a" font-size="16">
      <tspan>∑</tspan><tspan baseline-shift="sub" font-size="10">x</tspan><tspan baseline-shift="baseline"> M</tspan><tspan baseline-shift="sub" font-size="10">t</tspan><tspan baseline-shift="baseline">(x) W</tspan><tspan baseline-shift="sub" font-size="10">t</tspan><tspan baseline-shift="baseline">(x) CE(p</tspan><tspan baseline-shift="sub" font-size="10">t</tspan><tspan baseline-shift="baseline">(x), Y′</tspan><tspan baseline-shift="sub" font-size="10">t</tspan><tspan baseline-shift="baseline">(x))</tspan>
    </text>
    <path d="M1007 615 H1274" stroke="#17364a" stroke-width="1.6"/>
    <text class="math" x="1140" y="646" text-anchor="middle" fill="#17364a" font-size="16">
      <tspan>∑</tspan><tspan baseline-shift="sub" font-size="10">x</tspan><tspan baseline-shift="baseline"> M</tspan><tspan baseline-shift="sub" font-size="10">t</tspan><tspan baseline-shift="baseline">(x) W</tspan><tspan baseline-shift="sub" font-size="10">t</tspan><tspan baseline-shift="baseline">(x) + ε</tspan>
    </text>
    <text x="1095" y="669" text-anchor="middle" fill="#637789" font-size="10.5">RGB reconstruction and language-feature loss stay unchanged</text>
    <text x="1095" y="684" text-anchor="middle" fill="#637789" font-size="10.5">3D identity-aware semantic regularization stays unchanged</text>

    <rect x="900" y="708" width="390" height="41" rx="6" fill="#e9f6f1" stroke="#8fcbbd"/>
    <text class="body" x="1095" y="734" text-anchor="middle" fill="#075f51" font-weight="700">Down-weight uncertain pixels; preserve trustworthy identity anchors</text>
  </g>

  <g id="stage-4" inkscape:groupmode="layer" inkscape:label="4 Unchanged inference">
    <rect class="panel" x="1328" y="104" width="448" height="670" rx="9" stroke="#326cac" fill="#f9fbfe"/>
    <circle cx="1362" cy="139" r="24" fill="#1f5b96"/>
    <text x="1362" y="148" text-anchor="middle" fill="#ffffff" font-size="26" font-weight="700">4</text>
    <text class="stage" x="1398" y="147" fill="#174b78">Unchanged inference</text>

    <rect x="1352" y="169" width="400" height="64" rx="8" fill="#ffffff" stroke="#8db2da" stroke-width="1.5"/>
    <text class="small" x="1372" y="190" fill="#5b7388">TEXT QUERY</text>
    <text x="1552" y="216" text-anchor="middle" fill="#174b78" font-size="22" font-weight="700">“sunglasses”</text>
    <path d="M1552 236 V258" fill="none" stroke="#326cac" stroke-width="2.8" marker-end="url(#arrow-blue)"/>

    <rect x="1348" y="272" width="191" height="37" rx="5" fill="#c9434f"/>
    <text class="label" x="1443.5" y="296" text-anchor="middle" fill="#ffffff">Controlled ILGS</text>
    <rect x="1565" y="272" width="191" height="37" rx="5" fill="#0b8d73"/>
    <text class="label" x="1660.5" y="296" text-anchor="middle" fill="#ffffff">ILGS + IPR</text>

    <g id="baseline-crop" inkscape:label="Blue sofa baseline prediction crop">
      <image x="1348" y="316" width="191" height="144" preserveAspectRatio="none" xlink:href="${im.baseline}"/>
      <rect x="1348" y="316" width="191" height="144" fill="none" stroke="#c9434f" stroke-width="2.2"/>
    </g>
    <g id="ipr-crop" inkscape:label="Blue sofa IPR prediction crop">
      <image x="1565" y="316" width="191" height="144" preserveAspectRatio="none" xlink:href="${im.ipr}"/>
      <rect x="1565" y="316" width="191" height="144" fill="none" stroke="#0b8d73" stroke-width="2.2"/>
    </g>
    <path d="M1543 388 H1557" fill="none" stroke="#087d68" stroke-width="3" marker-end="url(#arrow-teal)"/>
    <text class="label" x="1443.5" y="486" text-anchor="middle" fill="#b91c32">IoU 0.012</text>
    <text class="label" x="1660.5" y="486" text-anchor="middle" fill="#087d68">IoU 0.945</text>
    <text class="small" x="1552" y="512" text-anchor="middle" fill="#60778a">same query, same progressive mask expanding</text>

    <rect x="1352" y="538" width="400" height="101" rx="7" fill="#eef7ff" stroke="#9dbedf" stroke-width="1.4"/>
    <text class="small" x="1552" y="562" text-anchor="middle" fill="#4c6e8b">BLUE_SOFA · THREE SEEDS</text>
    <text x="1552" y="594" text-anchor="middle" fill="#174b78" font-size="23" font-weight="700">+17.45 mIoU  /  +18.20 mBIoU</text>
    <text class="small" x="1552" y="620" text-anchor="middle" fill="#60778a">72.11 → 89.56  /  66.97 → 85.17</text>

    <rect x="1352" y="661" width="400" height="78" rx="7" fill="#ffffff" stroke="#c2d3e3"/>
    <text class="label" x="1552" y="688" text-anchor="middle" fill="#174b78">No inference-time module is added</text>
    <text class="small" x="1552" y="712" text-anchor="middle" fill="#60778a">IPR improves the learned identity field during training</text>
  </g>

  <g id="evidence-strip" inkscape:groupmode="layer" inkscape:label="Three-seed evidence summary">
    <rect x="24" y="797" width="1752" height="96" rx="9" fill="#f7fafc" stroke="#c5d4df" stroke-width="1.5"/>
    <text x="50" y="827" fill="#14364d" font-size="14" font-weight="700">THREE-SEED EVIDENCE</text>
    <path d="M220 813 V878" stroke="#cbd8e1" stroke-width="1.5"/>

    <rect x="252" y="817" width="88" height="34" rx="5" fill="#e7f0fa"/>
    <text x="296" y="839" text-anchor="middle" fill="#174b78" font-size="14" font-weight="700">LERF</text>
    <text x="362" y="841" fill="#14364d" font-size="18" font-weight="700">75.89 → 79.63 mIoU</text>
    <text x="571" y="841" fill="#087d68" font-size="18" font-weight="700">+3.74</text>
    <text x="362" y="868" fill="#60778a" font-size="14">71.25 → 74.46 mBIoU</text>
    <text x="571" y="868" fill="#087d68" font-size="14" font-weight="700">+3.21</text>

    <path d="M676 813 V878" stroke="#cbd8e1" stroke-width="1.5"/>
    <rect x="708" y="817" width="105" height="34" rx="5" fill="#e4f5ef"/>
    <text x="760.5" y="839" text-anchor="middle" fill="#075f51" font-size="14" font-weight="700">3D-OVS</text>
    <text x="835" y="841" fill="#14364d" font-size="18" font-weight="700">82.01 → 87.07 mIoU</text>
    <text x="1044" y="841" fill="#087d68" font-size="18" font-weight="700">+5.06</text>
    <text x="835" y="868" fill="#60778a" font-size="14">75.69 → 81.22 mBIoU</text>
    <text x="1044" y="868" fill="#087d68" font-size="14" font-weight="700">+5.53</text>

    <path d="M1149 813 V878" stroke="#cbd8e1" stroke-width="1.5"/>
    <text x="1182" y="834" fill="#14364d" font-size="14" font-weight="700">Controlled comparison</text>
    <text x="1182" y="858" fill="#60778a" font-size="13">same split · same seeds · same backbone · same inference</text>
    <text x="1182" y="879" fill="#087d68" font-size="13" font-weight="700">The only change is reliability-weighted identity supervision.</text>
  </g>
</svg>
`;

await fs.writeFile(output, svg, "utf8");
console.log(output);

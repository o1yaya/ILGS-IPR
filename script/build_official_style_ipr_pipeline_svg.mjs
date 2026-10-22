import fs from "node:fs/promises";
import path from "node:path";
import { execFileSync } from "node:child_process";

const workspace = "D:\\PycharmProjects\\PythonProject\\ILGS_release-main";
const outDir = path.join(workspace, "outputs", "pipeline_official_style_gpt_image2_20261009");
const assetDir = path.join(outDir, "source_assets");
const output = path.join(outDir, "ILGS_IPR_official_style_pipeline_editable.svg");

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
     width="1800" height="810" viewBox="0 0 1800 810">
  <title>Compact ILGS pipeline with Identity-Preserving Reliability</title>
  <desc>Editable GPT Image 2 layout with a horizontal IPR module above the identity-aware language Gaussian field. The outlier mask is integrated into the identity optimization branch.</desc>
  <metadata>All raster assets are embedded. Text, arrows, borders, and module diagrams remain editable SVG objects.</metadata>
  <defs>
    <marker id="arrow-black" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L9,4.5 L0,9 z" fill="#101820"/></marker>
    <marker id="arrow-orange" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L9,4.5 L0,9 z" fill="#ea7b19"/></marker>
    <marker id="arrow-teal" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L9,4.5 L0,9 z" fill="#087d68"/></marker>
    <marker id="arrow-red" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L9,4.5 L0,9 z" fill="#dd2e35"/></marker>
    <clipPath id="data-rgb"><rect x="48" y="116" width="228" height="140" rx="4"/></clipPath>
    <clipPath id="data-id"><rect x="48" y="338" width="228" height="140" rx="4"/></clipPath>
    <clipPath id="data-clip"><rect x="48" y="560" width="228" height="140" rx="4"/></clipPath>
    <clipPath id="opt-id-a"><rect x="1220" y="145" width="160" height="112" rx="3"/></clipPath>
    <clipPath id="opt-id-b"><rect x="1595" y="145" width="160" height="112" rx="3"/></clipPath>
    <clipPath id="opt-lang-a"><rect x="1220" y="365" width="160" height="112" rx="3"/></clipPath>
    <clipPath id="opt-lang-b"><rect x="1595" y="365" width="160" height="112" rx="3"/></clipPath>
    <clipPath id="opt-rgb-a"><rect x="1220" y="585" width="160" height="112" rx="3"/></clipPath>
    <clipPath id="opt-rgb-b"><rect x="1595" y="585" width="160" height="112" rx="3"/></clipPath>
    <style><![CDATA[
      text { font-family: Arial, Helvetica, sans-serif; letter-spacing: 0; }
      .heading { font-size: 25px; font-weight: 700; }
      .subheading { font-size: 16px; font-weight: 700; }
      .label { font-size: 14px; font-weight: 700; }
      .small { font-size: 12px; }
      .panel { stroke-width: 1.8; }
    ]]></style>
  </defs>

  <g id="background" inkscape:groupmode="layer" inkscape:label="Background">
    <rect width="1800" height="810" fill="#ffffff"/>
  </g>

  <g id="panels" inkscape:groupmode="layer" inkscape:label="Section panels">
    <rect class="panel" x="20" y="45" width="285" height="720" rx="10" fill="#f4f5f6" stroke="#e2e5e8"/>
    <rect class="panel" x="320" y="45" width="860" height="720" rx="10" fill="#eef6ff" stroke="#d7e5f2"/>
    <rect x="335" y="65" width="830" height="245" rx="9" fill="#fff9f2" stroke="#ea7b19" stroke-width="2.2"/>
    <rect class="panel" x="1195" y="45" width="585" height="720" rx="10" fill="#eef8e9" stroke="#d7e8cf"/>
  </g>

  <g id="data-preprocessing" inkscape:groupmode="layer" inkscape:label="1 Data preprocessing">
    <text class="heading" x="162" y="85" text-anchor="middle" fill="#111820">Data preprocessing</text>
    <image x="48" y="116" width="228" height="140" preserveAspectRatio="xMidYMid slice" clip-path="url(#data-rgb)" xlink:href="${im.rgb}"/>
    <rect x="48" y="116" width="228" height="140" rx="4" fill="none" stroke="#c9d1d8"/>
    <text class="label" x="162" y="280" text-anchor="middle">RGB images</text>
    <image x="48" y="338" width="228" height="140" preserveAspectRatio="xMidYMid slice" clip-path="url(#data-id)" xlink:href="${im.identity}"/>
    <rect x="48" y="338" width="228" height="140" rx="4" fill="none" stroke="#c9d1d8"/>
    <text class="label" x="162" y="502" text-anchor="middle">Identity labels</text>
    <image x="48" y="560" width="228" height="140" preserveAspectRatio="xMidYMid slice" clip-path="url(#data-clip)" xlink:href="${im.clip}"/>
    <rect x="48" y="560" width="228" height="140" rx="4" fill="none" stroke="#c9d1d8"/>
    <text class="label" x="162" y="724" text-anchor="middle">CLIP features</text>
  </g>

  <g id="ipr" inkscape:groupmode="layer" inkscape:label="2 IPR reliability module">
    <rect x="355" y="54" width="112" height="45" rx="7" fill="#ea7b19"/>
    <text x="411" y="85" text-anchor="middle" fill="#ffffff" font-size="25" font-weight="700">IPR</text>
    <rect x="360" y="112" width="565" height="177" rx="7" fill="#ffffff" stroke="#efad70" stroke-dasharray="6 4"/>

    <text class="subheading" x="442" y="139" text-anchor="middle" fill="#9f4f08">Cleanup</text>
    <image x="375" y="151" width="134" height="105" preserveAspectRatio="xMidYMid slice" xlink:href="${im.cleanup}"/>
    <rect x="375" y="151" width="134" height="105" fill="none" stroke="#efad70"/>

    <text class="subheading" x="632" y="139" text-anchor="middle" fill="#9f4f08">Semantic reliability</text>
    <image x="565" y="151" width="134" height="105" preserveAspectRatio="xMidYMid slice" xlink:href="${im.semantic}"/>
    <rect x="565" y="151" width="134" height="105" fill="none" stroke="#efad70"/>

    <text class="subheading" x="822" y="139" text-anchor="middle" fill="#9f4f08">Area prior</text>
    <image x="755" y="151" width="134" height="105" preserveAspectRatio="xMidYMid slice" xlink:href="${im.area}"/>
    <rect x="755" y="151" width="134" height="105" fill="none" stroke="#efad70"/>

    <circle cx="537" cy="204" r="13" fill="#ffffff" stroke="#ea7b19" stroke-width="1.8"/>
    <text x="537" y="212" text-anchor="middle" fill="#b65d0b" font-size="22" font-weight="700">+</text>
    <circle cx="727" cy="204" r="13" fill="#ffffff" stroke="#ea7b19" stroke-width="1.8"/>
    <text x="727" y="212" text-anchor="middle" fill="#b65d0b" font-size="22" font-weight="700">+</text>
    <path d="M889 204 H935" fill="none" stroke="#ea7b19" stroke-width="2.6" marker-end="url(#arrow-orange)"/>

    <line x1="944" y1="112" x2="944" y2="289" stroke="#efc89f"/>
    <image x="965" y="145" width="88" height="72" preserveAspectRatio="xMidYMid slice" xlink:href="${im.clean}"/>
    <rect x="965" y="145" width="88" height="72" fill="none" stroke="#ea7b19"/>
    <text class="small" x="1009" y="243" text-anchor="middle" fill="#713a08">Clean labels Y′</text>
    <image x="1068" y="145" width="88" height="72" preserveAspectRatio="xMidYMid slice" xlink:href="${im.reliability}"/>
    <rect x="1068" y="145" width="88" height="72" fill="none" stroke="#087d68"/>
    <text class="small" x="1112" y="243" text-anchor="middle" fill="#075f51">Reliability W</text>
  </g>

  <g id="gaussian-field" inkscape:groupmode="layer" inkscape:label="3 Identity-aware language Gaussians">
    <text class="heading" x="750" y="347" text-anchor="middle" fill="#16364c">Identity-aware language Gaussians</text>
    <image x="370" y="374" width="500" height="350" preserveAspectRatio="xMidYMid meet" xlink:href="${im.gaussian}"/>
    <rect x="370" y="374" width="500" height="350" fill="none" stroke="#bdd3e5"/>

    <path d="M890 445 C930 418 965 418 1003 445" fill="none" stroke="#245fdb" stroke-width="2.2"/>
    <ellipse cx="927" cy="424" rx="30" ry="12" fill="none" stroke="#245fdb" stroke-width="2.2" transform="rotate(18 927 424)"/>
    <ellipse cx="990" cy="424" rx="31" ry="12" fill="none" stroke="#dc3038" stroke-width="2.2" transform="rotate(-20 990 424)"/>
    <text x="960" y="477" text-anchor="middle" font-size="22">⋮</text>

    <rect x="920" y="505" width="220" height="178" rx="7" fill="#ffffff" stroke="#18232d" stroke-width="1.6"/>
    <rect x="921" y="506" width="218" height="58" fill="#f3f5f6"/>
    <rect x="921" y="564" width="218" height="58" fill="#e8f3ff"/>
    <rect x="921" y="622" width="218" height="60" fill="#fff0b7"/>
    <text class="label" x="1030" y="541" text-anchor="middle">appearance</text>
    <text class="label" x="1030" y="599" text-anchor="middle">language</text>
    <text class="label" x="1030" y="657" text-anchor="middle">identity</text>
  </g>

  <g id="optimization" inkscape:groupmode="layer" inkscape:label="4 Optimization branches">
    <text class="heading" x="1220" y="85" fill="#20351e">Optimization</text>
    <image x="1220" y="145" width="160" height="112" preserveAspectRatio="xMidYMid slice" clip-path="url(#opt-id-a)" xlink:href="${im.identity}"/>
    <rect x="1220" y="145" width="160" height="112" fill="none" stroke="#b8cfad"/>
    <text class="small" x="1300" y="278" text-anchor="middle">Rasterized identity</text>
    <rect x="1435" y="165" width="125" height="72" rx="7" fill="#ffffff" stroke="#111820" stroke-width="1.8"/>
    <text class="label" x="1498" y="195" text-anchor="middle">Weighted</text>
    <text class="label" x="1498" y="217" text-anchor="middle">identity loss</text>
    <image x="1595" y="145" width="160" height="112" preserveAspectRatio="xMidYMid slice" clip-path="url(#opt-id-b)" xlink:href="${im.clean}"/>
    <rect x="1595" y="145" width="160" height="112" fill="none" stroke="#b8cfad"/>
    <text class="small" x="1675" y="278" text-anchor="middle">Clean identity labels</text>
    <path d="M1380 201 H1423" fill="none" stroke="#dd2e35" stroke-width="2.6" marker-end="url(#arrow-red)"/>
    <path d="M1595 201 H1572" fill="none" stroke="#dd2e35" stroke-width="2.6" marker-end="url(#arrow-red)"/>

    <image x="1220" y="365" width="160" height="112" preserveAspectRatio="xMidYMid slice" clip-path="url(#opt-lang-a)" xlink:href="${im.language}"/>
    <rect x="1220" y="365" width="160" height="112" fill="none" stroke="#b8cfad"/>
    <text class="small" x="1300" y="498" text-anchor="middle">Rasterized language</text>
    <rect x="1435" y="385" width="125" height="72" rx="7" fill="#ffffff" stroke="#111820" stroke-width="1.8"/>
    <text class="label" x="1498" y="429" text-anchor="middle">Language loss</text>
    <image x="1595" y="365" width="160" height="112" preserveAspectRatio="xMidYMid slice" clip-path="url(#opt-lang-b)" xlink:href="${im.clip}"/>
    <rect x="1595" y="365" width="160" height="112" fill="none" stroke="#b8cfad"/>
    <text class="small" x="1675" y="498" text-anchor="middle">CLIP feature map</text>
    <path d="M1380 421 H1423" fill="none" stroke="#dd2e35" stroke-width="2.6" marker-end="url(#arrow-red)"/>
    <path d="M1595 421 H1572" fill="none" stroke="#dd2e35" stroke-width="2.6" marker-end="url(#arrow-red)"/>

    <image x="1220" y="585" width="160" height="112" preserveAspectRatio="xMidYMid slice" clip-path="url(#opt-rgb-a)" xlink:href="${im.rgb}"/>
    <rect x="1220" y="585" width="160" height="112" fill="none" stroke="#b8cfad"/>
    <text class="small" x="1300" y="718" text-anchor="middle">Rendered RGB</text>
    <rect x="1435" y="605" width="125" height="72" rx="7" fill="#ffffff" stroke="#111820" stroke-width="1.8"/>
    <text class="label" x="1498" y="649" text-anchor="middle">RGB loss</text>
    <image x="1595" y="585" width="160" height="112" preserveAspectRatio="xMidYMid slice" clip-path="url(#opt-rgb-b)" xlink:href="${im.rgb}"/>
    <rect x="1595" y="585" width="160" height="112" fill="none" stroke="#b8cfad"/>
    <text class="small" x="1675" y="718" text-anchor="middle">Ground-truth RGB</text>
    <path d="M1380 641 H1423" fill="none" stroke="#dd2e35" stroke-width="2.6" marker-end="url(#arrow-red)"/>
    <path d="M1595 641 H1572" fill="none" stroke="#dd2e35" stroke-width="2.6" marker-end="url(#arrow-red)"/>
  </g>

  <g id="outlier" inkscape:groupmode="layer" inkscape:label="Outlier mask integrated into identity loss">
    <rect x="1430" y="98" width="135" height="55" rx="6" fill="#fff6d9" stroke="#d9bc51" stroke-width="1.4"/>
    <image x="1438" y="106" width="48" height="37" preserveAspectRatio="xMidYMid slice" xlink:href="${im.outlier}"/>
    <rect x="1438" y="106" width="48" height="37" fill="none" stroke="#d9bc51"/>
    <text class="small" x="1524" y="121" text-anchor="middle" font-weight="700">Outlier</text>
    <text class="small" x="1524" y="137" text-anchor="middle" font-weight="700">mask</text>
    <path d="M1498 153 V159" fill="none" stroke="#101820" stroke-width="2.3" marker-end="url(#arrow-black)"/>
  </g>

  <g id="connections" inkscape:groupmode="layer" inkscape:label="Pipeline connections">
    <path d="M276 408 H312 V204 H360" fill="none" stroke="#101820" stroke-width="2.5" marker-end="url(#arrow-black)"/>
    <path d="M276 186 H312 V548 H358" fill="none" stroke="#101820" stroke-width="2.5" marker-end="url(#arrow-black)"/>
    <path d="M276 630 H342 V742 H900 V594 H908" fill="none" stroke="#101820" stroke-width="2.5" marker-end="url(#arrow-black)"/>

    <path d="M1140 594 H1183 V201 H1208" fill="none" stroke="#101820" stroke-width="2.5" marker-end="url(#arrow-black)"/>
    <path d="M1183 421 H1208" fill="none" stroke="#101820" stroke-width="2.5" marker-end="url(#arrow-black)"/>
    <path d="M1183 641 H1208" fill="none" stroke="#101820" stroke-width="2.5" marker-end="url(#arrow-black)"/>

    <path d="M1009 145 V112 H1415 V79 H1675 V133" fill="none" stroke="#ea7b19" stroke-width="3" marker-end="url(#arrow-orange)"/>
    <text x="1635" y="73" text-anchor="middle" fill="#b65d0b" font-size="17" font-weight="700">Y′</text>

    <path d="M1156 181 H1174 V320 H1498 V249" fill="none" stroke="#087d68" stroke-width="3" marker-end="url(#arrow-teal)"/>
    <text x="1288" y="312" text-anchor="middle" fill="#075f51" font-size="17" font-weight="700">W</text>
  </g>
</svg>
`;

await fs.writeFile(output, svg, "utf8");
console.log(output);

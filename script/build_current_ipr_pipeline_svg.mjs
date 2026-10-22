import fs from "node:fs/promises";
import path from "node:path";

const workspace = "D:\\PycharmProjects\\PythonProject\\ILGS_release-main";
const outDir = path.join(workspace, "outputs", "pipeline_current_method_gpt_image2_20261009");
const assetDir = path.join(outDir, "source_assets");
const output = path.join(outDir, "ILGS_IPR_current_pipeline_editable.svg");

async function dataUri(file) {
  const bytes = await fs.readFile(file);
  const ext = path.extname(file).toLowerCase();
  const mime = ext === ".jpg" || ext === ".jpeg" ? "image/jpeg" : "image/png";
  return `data:${mime};base64,${bytes.toString("base64")}`;
}

const files = {
  rgb: "input_rgb.jpg",
  novel: "render_rgb.png",
  noisy: "noisy_identity_map.png",
  clean: "structure_cleanup.png",
  semantic: "semantic_evidence.png",
  area: "area_prior.png",
  reliability: "reliability_map.png",
  identity: "identity_labels.png",
  language: "language_latent_rgb.png",
  similarity: "segment_heatmap.png",
  official: "official_noisy_prediction.png",
  ipr: "ipr_refined_prediction.png",
};

const im = Object.fromEntries(await Promise.all(
  Object.entries(files).map(async ([key, name]) => [key, await dataUri(path.join(assetDir, name))]),
));

const svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
     width="1920" height="1080" viewBox="0 0 1920 1080">
  <title>Current ILGS-IPR pipeline</title>
  <desc>Editable method figure aligned with the final no-visibility IPR configuration and three-seed LERF and 3D-OVS experiments.</desc>
  <defs>
    <clipPath id="c-s1-rgb"><rect x="35" y="176" width="270" height="184"/></clipPath>
    <clipPath id="c-s1-label"><rect x="35" y="411" width="270" height="198"/></clipPath>
    <clipPath id="c-noisy"><rect x="360" y="231" width="148" height="142"/></clipPath>
    <clipPath id="c-clean"><rect x="545" y="231" width="148" height="142"/></clipPath>
    <clipPath id="c-semantic"><rect x="735" y="231" width="211" height="118"/></clipPath>
    <clipPath id="c-area"><rect x="958" y="231" width="106" height="118"/></clipPath>
    <clipPath id="c-reliability"><rect x="370" y="520" width="308" height="205"/></clipPath>
    <clipPath id="c-s3-label"><rect x="1130" y="196" width="340" height="190"/></clipPath>
    <clipPath id="c-s3-conf"><rect x="1130" y="503" width="340" height="164"/></clipPath>
    <clipPath id="c-novel"><rect x="1525" y="223" width="355" height="184"/></clipPath>
    <clipPath id="c-official"><rect x="1525" y="458" width="355" height="121"/></clipPath>
    <clipPath id="c-ipr"><rect x="1525" y="624" width="355" height="121"/></clipPath>
    <style><![CDATA[
      text { font-family: Arial, Helvetica, sans-serif; }
      .panel { fill: #ffffff; stroke-width: 2.5; }
      .inner { fill: #ffffff; stroke-width: 1.5; }
      .stage-title { font-size: 23px; font-weight: 700; }
      .section-title { font-size: 17px; font-weight: 700; }
      .label { font-size: 15px; font-weight: 700; }
      .small { font-size: 13px; }
      .tiny { font-size: 11px; }
      .formula { font-family: Georgia, 'Times New Roman', serif; font-style: italic; }
    ]]></style>
  </defs>

  <g id="background-title" inkscape:groupmode="layer" inkscape:label="Background and title">
    <rect x="0" y="0" width="1920" height="1080" fill="#ffffff"/>
    <text x="34" y="51" fill="#17324d" font-size="39" font-weight="700">ILGS with Identity-Preserving Reliability (IPR)</text>
    <text x="36" y="81" fill="#45627f" font-size="19">Estimate reliability before optimization; preserve identity anchors; keep the ILGS backbone and inference unchanged</text>
    <path d="M24 98 H1896" stroke="#cbd8e5" stroke-width="2"/>
  </g>

  <g id="main-connectors" inkscape:groupmode="layer" inkscape:label="Main flow arrows">
    <path d="M320 407 H330" stroke="#d4173f" stroke-width="5" fill="none"/>
    <polygon points="329,393 347,407 329,421" fill="#d4173f"/>
    <path d="M1095 407 H1105" stroke="#00785f" stroke-width="5" fill="none"/>
    <polygon points="1104,393 1122,407 1104,421" fill="#00785f"/>
    <path d="M1490 407 H1500" stroke="#2463b5" stroke-width="5" fill="none"/>
    <polygon points="1499,393 1517,407 1499,421" fill="#2463b5"/>
  </g>

  <g id="stage-1-inputs" inkscape:groupmode="layer" inkscape:label="1 ILGS inputs">
    <rect class="panel" x="20" y="111" width="300" height="674" rx="8" ry="8" stroke="#d4173f"/>
    <rect x="28" y="119" width="48" height="44" rx="4" fill="#d4173f"/>
    <text x="52" y="152" text-anchor="middle" fill="#ffffff" font-size="31" font-weight="700">1</text>
    <text class="stage-title" x="89" y="149" fill="#c91337">ILGS inputs</text>

    <image x="35" y="176" width="270" height="184" preserveAspectRatio="xMidYMid slice" clip-path="url(#c-s1-rgb)" href="${im.rgb}"/>
    <rect x="35" y="176" width="270" height="184" fill="none" stroke="#d4dce5" stroke-width="1.5"/>
    <rect x="43" y="184" width="62" height="27" rx="3" fill="#28323a" stroke="#ffffff" stroke-width="2"/>
    <text x="74" y="204" text-anchor="middle" fill="#ffffff" font-size="15" font-weight="700">RGB</text>
    <text class="label" x="170" y="383" text-anchor="middle" fill="#17324d">Multi-view training images</text>

    <image x="35" y="411" width="270" height="198" preserveAspectRatio="none" clip-path="url(#c-s1-label)" href="${im.noisy}"/>
    <rect x="35" y="411" width="270" height="198" fill="none" stroke="#d4173f" stroke-width="2.5"/>
    <text class="label" x="170" y="632" text-anchor="middle" fill="#c91337">Original identity labels Y_t</text>
    <text class="small" x="170" y="652" text-anchor="middle" fill="#68788a">noisy but identity-indexed</text>

    <rect x="35" y="681" width="127" height="72" rx="6" fill="#f7f9fc" stroke="#b8c7d8" stroke-width="1.5"/>
    <text class="label" x="98.5" y="710" text-anchor="middle" fill="#17324d">SfM cameras</text>
    <text class="small" x="98.5" y="734" text-anchor="middle" fill="#5f7186">shared ILGS input</text>
    <rect x="178" y="681" width="127" height="72" rx="6" fill="#f7f9fc" stroke="#b8c7d8" stroke-width="1.5"/>
    <text class="label" x="241.5" y="710" text-anchor="middle" fill="#17324d">Query vocabulary</text>
    <text class="small" x="241.5" y="734" text-anchor="middle" fill="#5f7186">OpenCLIP text</text>
  </g>

  <g id="stage-2-ipr" inkscape:groupmode="layer" inkscape:label="2 IPR reliability estimation">
    <rect class="panel" x="335" y="111" width="760" height="674" rx="8" ry="8" stroke="#00785f"/>
    <rect x="343" y="119" width="48" height="44" rx="4" fill="#00785f"/>
    <text x="367" y="152" text-anchor="middle" fill="#ffffff" font-size="31" font-weight="700">2</text>
    <text class="stage-title" x="406" y="149" fill="#075b4c">IPR reliability estimation</text>
    <text x="1077" y="148" text-anchor="end" fill="#00785f" font-size="14" font-weight="700">no extra visibility multiplier</text>

    <rect class="inner" x="350" y="176" width="360" height="284" rx="6" ry="6" stroke="#7cc6b4"/>
    <rect x="359" y="184" width="46" height="31" rx="4" fill="#0b7d67"/>
    <text x="382" y="206" text-anchor="middle" fill="#ffffff" font-size="15" font-weight="700">2.1</text>
    <text class="section-title" x="417" y="205" fill="#17324d">Local structure cleanup</text>
    <text class="small" x="417" y="224" fill="#00785f">relabel tiny components with existing neighboring IDs</text>

    <image x="360" y="231" width="148" height="142" preserveAspectRatio="none" clip-path="url(#c-noisy)" href="${im.noisy}"/>
    <rect x="360" y="231" width="148" height="142" fill="none" stroke="#d4173f" stroke-width="1.5"/>
    <image x="545" y="231" width="148" height="142" preserveAspectRatio="none" clip-path="url(#c-clean)" href="${im.clean}"/>
    <rect x="545" y="231" width="148" height="142" fill="none" stroke="#00785f" stroke-width="1.5"/>
    <path d="M513 302 H532" stroke="#00785f" stroke-width="3"/>
    <polygon points="530,293 543,302 530,311" fill="#00785f"/>
    <text class="small" x="434" y="394" text-anchor="middle" fill="#c91337">noisy labels Y_t</text>
    <text class="small" x="619" y="394" text-anchor="middle" fill="#00785f">cleaned labels Y'_t</text>

    <text class="label" x="530" y="421" text-anchor="middle" fill="#17324d">Base confidence C_t</text>
    <rect x="365" y="430" width="99" height="23" rx="4" fill="#fff2f4" stroke="#ef9cac"/>
    <text class="tiny" x="414.5" y="446" text-anchor="middle" fill="#9d2440">tiny components x0.25</text>
    <rect x="472" y="430" width="103" height="23" rx="4" fill="#f2f8fc" stroke="#a9bfd1"/>
    <text class="tiny" x="523.5" y="446" text-anchor="middle" fill="#355b77">ID boundaries x0.65</text>
    <rect x="583" y="430" width="111" height="23" rx="4" fill="#fff9ec" stroke="#e9c66c"/>
    <text class="tiny" x="638.5" y="446" text-anchor="middle" fill="#916a12">area outliers x0.5</text>

    <rect class="inner" x="720" y="176" width="360" height="284" rx="6" ry="6" stroke="#7cc6b4"/>
    <rect x="729" y="184" width="46" height="31" rx="4" fill="#0b7d67"/>
    <text x="752" y="206" text-anchor="middle" fill="#ffffff" font-size="15" font-weight="700">2.2</text>
    <text class="section-title" x="787" y="205" fill="#17324d">Object reliability</text>
    <text class="small" x="787" y="224" fill="#00785f">semantic S_i + large-region G_i; no view-visibility term</text>

    <image x="735" y="231" width="211" height="118" preserveAspectRatio="none" clip-path="url(#c-semantic)" href="${im.semantic}"/>
    <rect x="735" y="231" width="211" height="118" fill="none" stroke="#b8c7d8" stroke-width="1.5"/>
    <image x="958" y="231" width="106" height="118" preserveAspectRatio="none" clip-path="url(#c-area)" href="${im.area}"/>
    <rect x="958" y="231" width="106" height="118" fill="none" stroke="#d4173f" stroke-width="1.5"/>
    <text class="small" x="840.5" y="369" text-anchor="middle" fill="#17324d">masked OpenCLIP crops</text>
    <text class="small" x="1011" y="369" text-anchor="middle" fill="#17324d">component ratios</text>

    <rect x="735" y="387" width="329" height="62" rx="4" fill="#f8fbfa" stroke="#acd7cc" stroke-width="1.2"/>
    <text class="tiny" x="899.5" y="402" text-anchor="middle" fill="#536878">mutually exclusive object weight w_i</text>
    <path d="M844 408 V444 M954 408 V444" stroke="#d7e4df"/>
    <text class="tiny" x="789" y="423" text-anchor="middle" fill="#17324d">trusted</text>
    <text class="small" x="789" y="442" text-anchor="middle" font-weight="700" fill="#00785f">1.00</text>
    <text class="tiny" x="899" y="423" text-anchor="middle" fill="#17324d">low semantic</text>
    <text class="small" x="899" y="442" text-anchor="middle" font-weight="700" fill="#b66b00">0.65</text>
    <text class="tiny" x="1009" y="423" text-anchor="middle" fill="#17324d">large mixed</text>
    <text class="small" x="1009" y="442" text-anchor="middle" font-weight="700" fill="#c91337">0.35</text>

    <rect class="inner" x="350" y="474" width="730" height="290" rx="6" ry="6" stroke="#40af94" fill="#f5fbf8"/>
    <text class="section-title" x="369" y="503" fill="#075b4c">Pixel confidence map</text>
    <image x="370" y="520" width="308" height="205" preserveAspectRatio="none" clip-path="url(#c-reliability)" href="${im.reliability}"/>
    <rect x="370" y="520" width="308" height="205" fill="none" stroke="#00785f" stroke-width="2"/>

    <rect x="700" y="516" width="360" height="88" rx="6" fill="#ffffff" stroke="#7cc6b4" stroke-width="1.5"/>
    <text x="880" y="546" text-anchor="middle" fill="#17324d" font-size="15" font-weight="700">Combine pixel and object evidence</text>
    <text class="formula" x="880" y="579" text-anchor="middle" fill="#075b4c" font-size="19">W_t(x) = clamp(C_t(x) x w_i, 0.05, 1.00)</text>

    <rect x="700" y="620" width="360" height="105" rx="6" fill="#ffffff" stroke="#7cc6b4" stroke-width="1.5"/>
    <text x="880" y="646" text-anchor="middle" fill="#17324d" font-size="14" font-weight="700">Identity preservation</text>
    <text class="small" x="880" y="672" text-anchor="middle" fill="#36596e">Semantic evidence estimates reliability</text>
    <text class="small" x="880" y="694" text-anchor="middle" fill="#36596e">It does not replace identity labels</text>
    <text class="small" x="880" y="716" text-anchor="middle" fill="#00785f" font-weight="700">ID vocabulary stays unchanged</text>
  </g>

  <g id="stage-3-training" inkscape:groupmode="layer" inkscape:label="3 Confidence-weighted ILGS training">
    <rect class="panel" x="1110" y="111" width="380" height="674" rx="8" ry="8" stroke="#2463b5" fill="#f5f9ff"/>
    <rect x="1118" y="119" width="48" height="44" rx="4" fill="#2463b5"/>
    <text x="1142" y="152" text-anchor="middle" fill="#ffffff" font-size="31" font-weight="700">3</text>
    <text x="1181" y="143" fill="#1b559c" font-size="20" font-weight="700">Confidence-weighted</text>
    <text x="1181" y="165" fill="#1b559c" font-size="20" font-weight="700">ILGS training</text>

    <text class="label" x="1300" y="188" text-anchor="middle" fill="#17324d">Cleaned identity anchors Y'_t</text>
    <image x="1130" y="196" width="340" height="190" preserveAspectRatio="none" clip-path="url(#c-s3-label)" href="${im.identity}"/>
    <rect x="1130" y="196" width="340" height="190" fill="none" stroke="#8ab4e5" stroke-width="1.5"/>

    <text x="1300" y="414" text-anchor="middle" fill="#17324d" font-size="28" font-weight="700">x</text>
    <rect x="1130" y="425" width="340" height="55" rx="5" fill="#ffffff" stroke="#8ab4e5" stroke-width="1.5"/>
    <text class="label" x="1300" y="449" text-anchor="middle" fill="#17324d">Dynamic valid mask M_t(x)</text>
    <text class="small" x="1300" y="469" text-anchor="middle" fill="#5f7186">official CE outlier filtering retained</text>

    <text x="1300" y="499" text-anchor="middle" fill="#17324d" font-size="28" font-weight="700">x</text>
    <image x="1130" y="503" width="340" height="164" preserveAspectRatio="none" clip-path="url(#c-s3-conf)" href="${im.reliability}"/>
    <rect x="1130" y="503" width="340" height="164" fill="none" stroke="#2463b5" stroke-width="1.5"/>
    <text class="label" x="1300" y="687" text-anchor="middle" fill="#1b559c">IPR confidence W_t(x)</text>

    <rect x="1130" y="700" width="340" height="53" rx="5" fill="#ffffff" stroke="#8ab4e5" stroke-width="1.5"/>
    <text class="formula" x="1300" y="720" text-anchor="middle" fill="#17324d" font-size="13">L_cls^IPR =</text>
    <text class="formula" x="1300" y="743" text-anchor="middle" fill="#17324d" font-size="12.5">sum M_t W_t CE / (sum M_t W_t + epsilon)</text>
    <text class="tiny" x="1300" y="772" text-anchor="middle" fill="#2463b5" font-weight="700">RGB + language features + 3D semantic regularization unchanged</text>
  </g>

  <g id="stage-4-inference" inkscape:groupmode="layer" inkscape:label="4 Inference unchanged">
    <rect class="panel" x="1505" y="111" width="395" height="674" rx="8" ry="8" stroke="#2463b5" fill="#f8fbff"/>
    <rect x="1513" y="119" width="48" height="44" rx="4" fill="#174f84"/>
    <text x="1537" y="152" text-anchor="middle" fill="#ffffff" font-size="31" font-weight="700">4</text>
    <text class="stage-title" x="1576" y="149" fill="#174f84">Inference unchanged</text>

    <rect x="1525" y="176" width="355" height="36" rx="5" fill="#ffffff" stroke="#9ebee0" stroke-width="1.5"/>
    <text class="label" x="1702.5" y="200" text-anchor="middle" fill="#174f84">Text query: "Portuguese egg tart"</text>
    <image x="1525" y="223" width="355" height="184" preserveAspectRatio="xMidYMid slice" clip-path="url(#c-novel)" href="${im.novel}"/>
    <rect x="1525" y="223" width="355" height="184" fill="none" stroke="#9ebee0" stroke-width="1.5"/>
    <text class="small" x="1702.5" y="428" text-anchor="middle" fill="#174f84">progressive mask expanding</text>

    <text class="label" x="1702.5" y="451" text-anchor="middle" fill="#c91337">Controlled ILGS: noisy segment</text>
    <image x="1525" y="458" width="355" height="121" preserveAspectRatio="none" clip-path="url(#c-official)" href="${im.official}"/>
    <rect x="1525" y="458" width="355" height="121" fill="none" stroke="#d4173f" stroke-width="2.5"/>

    <path d="M1702 586 V604" stroke="#00785f" stroke-width="3"/>
    <polygon points="1694,602 1710,602 1702,614" fill="#00785f"/>
    <text class="label" x="1702.5" y="618" text-anchor="middle" fill="#00785f">ILGS + IPR: target segment</text>
    <image x="1525" y="624" width="355" height="121" preserveAspectRatio="none" clip-path="url(#c-ipr)" href="${im.ipr}"/>
    <rect x="1525" y="624" width="355" height="121" fill="none" stroke="#00785f" stroke-width="2.5"/>
    <text x="1702.5" y="771" text-anchor="middle" fill="#174f84" font-size="17" font-weight="700">3D-OVS: +5.06 mIoU / +5.53 mBIoU</text>
  </g>

  <g id="loss-path" inkscape:groupmode="layer" inkscape:label="Identity supervision path">
    <rect x="20" y="804" width="1075" height="251" rx="8" ry="8" fill="#ffffff" stroke="#d4173f" stroke-width="2"/>
    <text x="35" y="831" fill="#c91337" font-size="17" font-weight="700">Identity-supervision path</text>

    <rect x="40" y="855" width="205" height="116" rx="6" fill="#f5f8fc" stroke="#b8c7d8" stroke-width="1.5"/>
    <text class="label" x="142.5" y="883" text-anchor="middle" fill="#17324d">Rendered logits p_t</text>
    <text class="label" x="142.5" y="907" text-anchor="middle" fill="#17324d">Cleaned labels Y'_t</text>
    <text class="formula" x="142.5" y="948" text-anchor="middle" fill="#17324d" font-size="20">CE(p_t(x), Y'_t(x))</text>

    <path d="M245 913 H273" stroke="#5f7186" stroke-width="3"/>
    <polygon points="271,904 284,913 271,922" fill="#5f7186"/>
    <rect x="284" y="855" width="174" height="116" rx="6" fill="#fff9ec" stroke="#e3ba4f" stroke-width="1.5"/>
    <text class="label" x="371" y="884" text-anchor="middle" fill="#8a6411">Dynamic CE filter</text>
    <text class="formula" x="371" y="925" text-anchor="middle" fill="#8a6411" font-size="25">M_t(x)</text>
    <text class="small" x="371" y="951" text-anchor="middle" fill="#6e7680">hard exclusion</text>

    <path d="M458 913 H486" stroke="#b66b00" stroke-width="3"/>
    <polygon points="484,904 497,913 484,922" fill="#b66b00"/>
    <rect x="497" y="855" width="174" height="116" rx="6" fill="#f2fbf7" stroke="#66bca7" stroke-width="1.5"/>
    <text class="label" x="584" y="884" text-anchor="middle" fill="#00785f">IPR confidence</text>
    <text class="formula" x="584" y="925" text-anchor="middle" fill="#00785f" font-size="25">W_t(x)</text>
    <text class="small" x="584" y="951" text-anchor="middle" fill="#536878">soft reliability weight</text>

    <path d="M671 913 H699" stroke="#00785f" stroke-width="3"/>
    <polygon points="697,904 710,913 697,922" fill="#00785f"/>
    <circle cx="744" cy="913" r="34" fill="#ffffff" stroke="#71839a" stroke-width="2"/>
    <text x="744" y="925" text-anchor="middle" fill="#17324d" font-size="38">x</text>
    <path d="M778 913 H805" stroke="#00785f" stroke-width="3"/>
    <polygon points="803,904 816,913 803,922" fill="#00785f"/>

    <rect x="816" y="850" width="258" height="126" rx="6" fill="#f2fbf7" stroke="#66bca7" stroke-width="1.5"/>
    <text class="label" x="945" y="879" text-anchor="middle" fill="#00785f">Confidence-weighted identity loss</text>
    <text class="formula" x="945" y="914" text-anchor="middle" fill="#17324d" font-size="17">sum M_t W_t CE</text>
    <path d="M866 927 H1024" stroke="#17324d" stroke-width="1.5"/>
    <text class="formula" x="945" y="951" text-anchor="middle" fill="#17324d" font-size="17">sum M_t W_t + epsilon</text>

    <text x="557.5" y="1018" text-anchor="middle" fill="#17324d" font-size="17" font-weight="700">IPR preserves identity anchors and changes only their contribution to the 2D identity loss</text>
  </g>

  <g id="experimental-evidence" inkscape:groupmode="layer" inkscape:label="Experimental evidence">
    <rect x="1110" y="804" width="790" height="251" rx="8" ry="8" fill="#f8fbff" stroke="#2463b5" stroke-width="2"/>
    <text x="1126" y="831" fill="#174f84" font-size="17" font-weight="700">Experimental evidence: three seeds per scene</text>

    <rect x="1128" y="850" width="355" height="176" rx="6" fill="#ffffff" stroke="#9ebee0" stroke-width="1.5"/>
    <text class="label" x="1305.5" y="875" text-anchor="middle" fill="#174f84">LERF: 3 scenes x 3 seeds</text>
    <text class="small" x="1150" y="904" fill="#5f7186">method</text><text class="small" x="1350" y="904" text-anchor="middle" fill="#5f7186">mIoU</text><text class="small" x="1443" y="904" text-anchor="middle" fill="#5f7186">mBIoU</text>
    <path d="M1142 913 H1469" stroke="#c7d5e3"/>
    <text class="small" x="1150" y="938" fill="#17324d">controlled ILGS</text><text class="small" x="1350" y="938" text-anchor="middle" fill="#17324d">75.89</text><text class="small" x="1443" y="938" text-anchor="middle" fill="#17324d">71.25</text>
    <rect x="1142" y="948" width="327" height="30" fill="#e7f6f1"/>
    <text class="small" x="1150" y="969" fill="#00785f" font-weight="700">ILGS + IPR</text><text class="small" x="1350" y="969" text-anchor="middle" fill="#00785f" font-weight="700">79.63</text><text class="small" x="1443" y="969" text-anchor="middle" fill="#00785f" font-weight="700">74.46</text>
    <text class="small" x="1305.5" y="1007" text-anchor="middle" fill="#00785f" font-weight="700">gain: +3.74 mIoU / +3.21 mBIoU</text>

    <rect x="1500" y="850" width="382" height="176" rx="6" fill="#ffffff" stroke="#9ebee0" stroke-width="1.5"/>
    <text class="label" x="1691" y="875" text-anchor="middle" fill="#174f84">3D-OVS: 10 scenes x 3 seeds</text>
    <text class="small" x="1522" y="904" fill="#5f7186">method</text><text class="small" x="1733" y="904" text-anchor="middle" fill="#5f7186">mIoU</text><text class="small" x="1836" y="904" text-anchor="middle" fill="#5f7186">mBIoU</text>
    <path d="M1514 913 H1868" stroke="#c7d5e3"/>
    <text class="small" x="1522" y="938" fill="#17324d">controlled ILGS</text><text class="small" x="1733" y="938" text-anchor="middle" fill="#17324d">82.01</text><text class="small" x="1836" y="938" text-anchor="middle" fill="#17324d">75.69</text>
    <rect x="1514" y="948" width="354" height="30" fill="#e7f6f1"/>
    <text class="small" x="1522" y="969" fill="#00785f" font-weight="700">ILGS + IPR</text><text class="small" x="1733" y="969" text-anchor="middle" fill="#00785f" font-weight="700">87.07</text><text class="small" x="1836" y="969" text-anchor="middle" fill="#00785f" font-weight="700">81.22</text>
    <text class="small" x="1691" y="1007" text-anchor="middle" fill="#00785f" font-weight="700">gain: +5.06 mIoU / +5.53 mBIoU</text>
  </g>
</svg>`;

await fs.mkdir(outDir, { recursive: true });
await fs.writeFile(output, svg, "utf8");
console.log(JSON.stringify({ output }, null, 2));

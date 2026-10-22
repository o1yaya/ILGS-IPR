import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';

const require = createRequire(import.meta.url);
const deps = 'C:/Users/hp/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const sharp = require(`${deps}/sharp`);

const root = 'D:/PycharmProjects/PythonProject/ILGS_release-main';
const sourceDir = path.join(root, 'outputs/method_figure_pipeline_gpt_image2_20261009/source_assets');
const figureDir = 'D:/wlxy/ilgs/文章图';
const assetDir = path.join(figureDir, 'current_ipr_assets');
const inkscape = 'E:/Inkscape/bin/inkscape.com';
await fs.mkdir(assetDir, { recursive: true });

const files = {
  rgb: path.join(sourceDir, 'input_rgb.jpg'),
  noisy: path.join(sourceDir, 'noisy_identity_map.png'),
  cleaned: path.join(sourceDir, 'structure_cleanup.png'),
  reliability: path.join(sourceDir, 'reliability_map.png'),
};

async function prepareImage(input, output, width, height) {
  const metadata = await sharp(input).metadata();
  const trimX = Math.max(2, Math.round(metadata.width * 0.003));
  const trimY = Math.max(2, Math.round(metadata.height * 0.003));
  await sharp(input)
    .extract({
      left: trimX,
      top: trimY,
      width: metadata.width - trimX * 2,
      height: metadata.height - trimY * 2,
    })
    .resize(width, height, { fit: 'cover', position: 'centre' })
    .png({ compressionLevel: 9 })
    .toFile(output);
  return fs.readFile(output);
}

const prepared = {
  rgb: await prepareImage(files.rgb, path.join(assetDir, 'teaser_rgb.png'), 1000, 750),
  noisy: await prepareImage(files.noisy, path.join(assetDir, 'teaser_noisy_mask.png'), 1200, 900),
  cleaned: await prepareImage(files.cleaned, path.join(assetDir, 'teaser_cleaned_mask.png'), 900, 675),
  reliability: await prepareImage(files.reliability, path.join(assetDir, 'teaser_reliability.png'), 900, 675),
};

const dataUri = bytes => `data:image/png;base64,${bytes.toString('base64')}`;
const svgPath = path.join(figureDir, 'mask_noise_teaser_current_ipr.svg');
const pngPath = path.join(figureDir, 'mask_noise_teaser_current_ipr.png');
const pdfPath = path.join(figureDir, 'mask_noise_teaser_current_ipr.pdf');

const svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
     width="1440" height="560" viewBox="0 0 1440 560">
  <title>Mask-noise motivation figure for ILGS-IPR</title>
  <desc>Editable introduction figure emphasizing background-dominated identities, boundary fragments and mixed regions in noisy identity masks, followed by cleaned labels and a reliability map.</desc>
  <defs>
    <clipPath id="clip-rgb"><rect x="34" y="102" width="292" height="219" rx="5"/></clipPath>
    <clipPath id="clip-noisy"><rect x="382" y="76" width="526" height="395" rx="5"/></clipPath>
    <clipPath id="clip-clean"><rect x="954" y="118" width="214" height="161" rx="5"/></clipPath>
    <clipPath id="clip-weight"><rect x="1192" y="118" width="214" height="161" rx="5"/></clipPath>
    <marker id="arrow-dark" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 Z" fill="#29343b"/>
    </marker>
    <marker id="arrow-red" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
      <path d="M0,0 L7,3.5 L0,7 Z" fill="#c7283e"/>
    </marker>
  </defs>

  <rect width="1440" height="560" fill="#ffffff"/>

  <g id="panel-a" inkscape:label="RGB context">
    <text x="34" y="50" font-family="Arial, Helvetica, sans-serif" font-size="30" font-weight="700" fill="#20262d">a</text>
    <text x="72" y="50" font-family="Arial, Helvetica, sans-serif" font-size="25" font-weight="700" fill="#20262d">Training view</text>
    <rect x="24" y="76" width="312" height="395" rx="8" fill="#f3f6f8"/>
    <image id="rgb-context" x="34" y="102" width="292" height="219" preserveAspectRatio="xMidYMid slice"
           clip-path="url(#clip-rgb)" xlink:href="${dataUri(prepared.rgb)}"/>
    <text x="180" y="361" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="20" fill="#45515a">RGB image</text>
    <text x="180" y="402" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="18" fill="#68747d">Automatic identity tracks</text>
    <path d="M116 425 H244" stroke="#29343b" stroke-width="2" marker-end="url(#arrow-dark)"/>
  </g>

  <g id="panel-b" inkscape:label="Noisy identity mask">
    <text x="370" y="50" font-family="Arial, Helvetica, sans-serif" font-size="30" font-weight="700" fill="#20262d">b</text>
    <text x="408" y="50" font-family="Arial, Helvetica, sans-serif" font-size="25" font-weight="700" fill="#c7283e">Noisy identity mask</text>
    <rect x="370" y="64" width="550" height="435" rx="8" fill="#fff6f4"/>
    <image id="noisy-mask" x="382" y="76" width="526" height="395" preserveAspectRatio="xMidYMid slice"
           clip-path="url(#clip-noisy)" xlink:href="${dataUri(prepared.noisy)}"/>

    <ellipse cx="609" cy="257" rx="33" ry="55" fill="none" stroke="#c7283e" stroke-width="3" stroke-dasharray="8 6"/>
    <ellipse cx="799" cy="285" rx="66" ry="45" fill="none" stroke="#c7283e" stroke-width="3" stroke-dasharray="8 6"/>
    <rect x="393" y="88" width="194" height="34" rx="4" fill="#ffffff" fill-opacity="0.94"/>
    <text x="490" y="111" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="17" font-weight="700" fill="#c7283e">Background IDs dominate</text>
    <path d="M587 108 C625 110 646 132 650 170" fill="none" stroke="#c7283e" stroke-width="2" marker-end="url(#arrow-red)"/>

    <rect x="392" y="420" width="160" height="34" rx="4" fill="#ffffff" fill-opacity="0.94"/>
    <text x="472" y="443" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="17" font-weight="700" fill="#c7283e">Boundary fragments</text>
    <path d="M552 432 C585 412 603 355 609 317" fill="none" stroke="#c7283e" stroke-width="2" marker-end="url(#arrow-red)"/>

    <rect x="718" y="420" width="178" height="34" rx="4" fill="#ffffff" fill-opacity="0.94"/>
    <text x="807" y="443" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="17" font-weight="700" fill="#c7283e">Spurious ID fragments</text>
    <path d="M807 419 C807 384 803 349 800 333" fill="none" stroke="#c7283e" stroke-width="2" marker-end="url(#arrow-red)"/>
    <text x="645" y="528" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="20" font-weight="700" fill="#c7283e">Wall and floor IDs occupy 85.6% of the mask</text>
  </g>

  <path d="M928 278 H946" stroke="#29343b" stroke-width="2.2" marker-end="url(#arrow-dark)"/>

  <g id="panel-c" inkscape:label="IPR outputs">
    <text x="946" y="50" font-family="Arial, Helvetica, sans-serif" font-size="30" font-weight="700" fill="#20262d">c</text>
    <text x="984" y="50" font-family="Arial, Helvetica, sans-serif" font-size="25" font-weight="700" fill="#087f6e">Reliability-guided supervision</text>
    <rect x="946" y="64" width="470" height="435" rx="8" fill="#f2f8f5"/>

    <image id="cleaned-mask" x="954" y="118" width="214" height="161" preserveAspectRatio="xMidYMid slice"
           clip-path="url(#clip-clean)" xlink:href="${dataUri(prepared.cleaned)}"/>
    <image id="reliability-map" x="1192" y="118" width="214" height="161" preserveAspectRatio="xMidYMid slice"
           clip-path="url(#clip-weight)" xlink:href="${dataUri(prepared.reliability)}"/>
    <text x="1061" y="105" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="18" font-weight="700" fill="#20262d">Cleaned labels Ỹ</text>
    <text x="1299" y="105" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="18" font-weight="700" fill="#20262d">Reliability W(p)</text>

    <path d="M1168 198 H1184" stroke="#087f6e" stroke-width="2" marker-end="url(#arrow-dark)"/>
    <rect x="980" y="324" width="402" height="82" rx="6" fill="#ffffff"/>
    <circle cx="1014" cy="352" r="9" fill="#ffe26a"/>
    <text x="1034" y="359" font-family="Arial, Helvetica, sans-serif" font-size="18" fill="#354148">Preserve reliable identity anchors</text>
    <circle cx="1014" cy="383" r="9" fill="#717b75"/>
    <text x="1034" y="390" font-family="Arial, Helvetica, sans-serif" font-size="18" fill="#354148">Downweight uncertain pixels</text>
    <text x="1181" y="449" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="19" font-weight="700" fill="#087f6e">Cleaner supervision for the identity loss</text>
  </g>
</svg>`;

await fs.writeFile(svgPath, svg, 'utf8');
execFileSync(inkscape, [svgPath, '--export-type=png', `--export-filename=${pngPath}`, '--export-dpi=300', '--export-area-page'], { stdio: 'inherit' });
execFileSync(inkscape, [svgPath, '--export-type=pdf', `--export-filename=${pdfPath}`, '--export-area-page'], { stdio: 'inherit' });

console.log(JSON.stringify({ svgPath, pngPath, pdfPath }, null, 2));

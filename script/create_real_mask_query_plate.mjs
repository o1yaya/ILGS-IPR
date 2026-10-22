import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';

const require = createRequire(import.meta.url);
const deps = 'C:/Users/hp/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const sharp = require(`${deps}/sharp`);

const ACCENT_RED = '#B2182B';
const CONTROL_BLUE = '#2166AC';
const IPR_GREEN = '#1B7837';
const BLACK = '#222222';

const sourceRoot = 'D:/downloads/blue_sofa_real_figure_assets_20261018_extracted/blue_sofa_real_figure_assets_20261018';
const figureDir = 'D:/wlxy/ilgs/文章图';
const provenanceDir = path.join(figureDir, 'real_blue_sofa_figure_assets');
const inkscape = 'E:/Inkscape/bin/inkscape.com';
const outputs = {
  svg: path.join(figureDir, 'mask_noise_teaser_current_ipr.svg'),
  png: path.join(figureDir, 'mask_noise_teaser_current_ipr.png'),
  pdf: path.join(figureDir, 'mask_noise_teaser_current_ipr.pdf'),
};

const workWidth = 1000;
const workHeight = 750;
const panelWidth = 420;
const panelHeight = 196;

const rows = [
  {
    slug: 'pig_doll',
    line1: 'Text query:',
    line2: '"squirrel pig doll"',
    view: 2,
    stem: '13',
    query: 'a squirrel pig doll',
    officialIou: 0.940,
    iprIou: 0.991,
  },
  {
    slug: 'speaker',
    line1: 'Text query:',
    line2: '"JBL speaker"',
    view: 2,
    stem: '13',
    query: 'a JBL bluetooth speaker',
    officialIou: 0.970,
    iprIou: 0.971,
  },
  {
    slug: 'controller',
    line1: 'Text query:',
    line2: '"aircon controller"',
    view: 3,
    stem: '24',
    query: 'an aircon controller',
    officialIou: 0.521,
    iprIou: 0.890,
  },
];

await fs.mkdir(provenanceDir, { recursive: true });

async function locateRgb(viewDir) {
  for (const name of ['rgb.jpg', 'rgb.jpeg', 'rgb.png']) {
    const candidate = path.join(viewDir, name);
    try {
      await fs.access(candidate);
      return candidate;
    } catch {
      // Try the next supported extension.
    }
  }
  throw new Error(`RGB image is missing in ${viewDir}`);
}

async function loadRgb(file) {
  const { data, info } = await sharp(file)
    .resize(workWidth, workHeight, { fit: 'fill' })
    .removeAlpha()
    .raw()
    .toBuffer({ resolveWithObject: true });
  return { data, channels: info.channels };
}

async function loadMask(file) {
  const { data } = await sharp(file)
    .resize(workWidth, workHeight, { fit: 'fill', kernel: 'nearest' })
    .greyscale()
    .raw()
    .toBuffer({ resolveWithObject: true });
  const mask = new Uint8Array(workWidth * workHeight);
  for (let i = 0; i < mask.length; i += 1) mask[i] = data[i] >= 128 ? 1 : 0;
  return mask;
}

function unionMasks(...masks) {
  const result = new Uint8Array(workWidth * workHeight);
  for (let i = 0; i < result.length; i += 1) {
    for (const mask of masks) {
      if (mask[i]) {
        result[i] = 1;
        break;
      }
    }
  }
  return result;
}

function bounds(mask) {
  let minX = workWidth;
  let minY = workHeight;
  let maxX = -1;
  let maxY = -1;
  for (let y = 0; y < workHeight; y += 1) {
    for (let x = 0; x < workWidth; x += 1) {
      if (!mask[y * workWidth + x]) continue;
      minX = Math.min(minX, x);
      minY = Math.min(minY, y);
      maxX = Math.max(maxX, x);
      maxY = Math.max(maxY, y);
    }
  }
  if (maxX < 0) throw new Error('An exported prediction mask is empty.');
  return { minX, minY, maxX, maxY };
}

function cropFor(maskBounds) {
  const aspect = panelWidth / panelHeight;
  let width = Math.max(240, (maskBounds.maxX - maskBounds.minX + 1) * 1.30);
  let height = Math.max(165, (maskBounds.maxY - maskBounds.minY + 1) * 1.30);
  if (width / height < aspect) width = height * aspect;
  else height = width / aspect;
  width = Math.min(width, workWidth);
  height = Math.min(height, workHeight);
  const cx = (maskBounds.minX + maskBounds.maxX) / 2;
  const cy = (maskBounds.minY + maskBounds.maxY) / 2;
  let left = Math.round(cx - width / 2);
  let top = Math.round(cy - height / 2);
  left = Math.max(0, Math.min(workWidth - Math.round(width), left));
  top = Math.max(0, Math.min(workHeight - Math.round(height), top));
  return { left, top, width: Math.round(width), height: Math.round(height) };
}

function queryView(rgb, gtMask) {
  const rgba = Buffer.alloc(workWidth * workHeight * 4);
  for (let i = 0; i < gtMask.length; i += 1) {
    const p = i * rgb.channels;
    const q = i * 4;
    const r = rgb.data[p];
    const g = rgb.data[p + 1];
    const b = rgb.data[p + 2];
    if (gtMask[i]) {
      rgba[q] = Math.round(r * 0.74 + 255 * 0.26);
      rgba[q + 1] = Math.round(g * 0.74 + 195 * 0.26);
      rgba[q + 2] = Math.round(b * 0.74 + 40 * 0.26);
    } else {
      const lum = 0.299 * r + 0.587 * g + 0.114 * b;
      rgba[q] = Math.round(lum * 0.30 + 10);
      rgba[q + 1] = Math.round(lum * 0.38 + 25);
      rgba[q + 2] = Math.round(lum * 0.47 + 40);
    }
    rgba[q + 3] = 255;
  }
  return rgba;
}

function binaryView(mask) {
  const rgba = Buffer.alloc(workWidth * workHeight * 4);
  for (let i = 0; i < mask.length; i += 1) {
    const q = i * 4;
    const value = mask[i] ? 255 : 4;
    rgba[q] = value;
    rgba[q + 1] = value;
    rgba[q + 2] = value;
    rgba[q + 3] = 255;
  }
  return rgba;
}

async function writeCrop(buffer, crop, output) {
  await sharp(buffer, { raw: { width: workWidth, height: workHeight, channels: 4 } })
    .extract(crop)
    .resize(panelWidth, panelHeight, { fit: 'fill', kernel: 'nearest' })
    .png({ compressionLevel: 9 })
    .toFile(output);
  return fs.readFile(output);
}

function mappedBox(box, crop, x, y) {
  const sx = panelWidth / crop.width;
  const sy = panelHeight / crop.height;
  const left = x + Math.max(2, (box.minX - crop.left) * sx - 6);
  const top = y + Math.max(2, (box.minY - crop.top) * sy - 6);
  const width = Math.min(panelWidth - (left - x) - 2, (box.maxX - box.minX + 1) * sx + 12);
  const height = Math.min(panelHeight - (top - y) - 2, (box.maxY - box.minY + 1) * sy + 12);
  return { left, top, width, height };
}

const prepared = [];
for (const row of rows) {
  const viewDir = path.join(sourceRoot, `view_${row.view}_${row.stem}`);
  const queryDir = path.join(viewDir, row.query);
  const rgbPath = await locateRgb(viewDir);
  const gtPath = path.join(queryDir, 'ground_truth.png');
  const officialPath = path.join(queryDir, 'official_ilgs.png');
  const iprPath = path.join(queryDir, 'ipr.png');

  const rgb = await loadRgb(rgbPath);
  const gt = await loadMask(gtPath);
  const official = await loadMask(officialPath);
  const ipr = await loadMask(iprPath);
  const crop = cropFor(bounds(unionMasks(gt, official, ipr)));
  const gtBox = bounds(gt);

  const rowDir = path.join(provenanceDir, row.slug);
  await fs.mkdir(rowDir, { recursive: true });
  await fs.copyFile(rgbPath, path.join(rowDir, path.basename(rgbPath)));
  await fs.copyFile(gtPath, path.join(rowDir, 'ground_truth.png'));
  await fs.copyFile(officialPath, path.join(rowDir, 'official_ilgs.png'));
  await fs.copyFile(iprPath, path.join(rowDir, 'ipr.png'));

  const queryPath = path.join(rowDir, 'query_highlight.png');
  const officialCropPath = path.join(rowDir, 'official_crop.png');
  const iprCropPath = path.join(rowDir, 'ipr_crop.png');
  const queryBytes = await writeCrop(queryView(rgb, gt), crop, queryPath);
  const officialBytes = await writeCrop(binaryView(official), crop, officialCropPath);
  const iprBytes = await writeCrop(binaryView(ipr), crop, iprCropPath);

  prepared.push({
    ...row,
    box: mappedBox(gtBox, crop, 0, 0),
    queryBytes,
    officialBytes,
    iprBytes,
  });
}

await fs.writeFile(
  path.join(provenanceDir, 'selection_manifest.json'),
  JSON.stringify({ sourceRoot, rows }, null, 2),
  'utf8',
);

const dataUri = bytes => `data:image/png;base64,${bytes.toString('base64')}`;
const image = (id, x, y, bytes) => `
  <image id="${id}" x="${x}" y="${y}" width="${panelWidth}" height="${panelHeight}"
         preserveAspectRatio="none" xlink:href="${dataUri(bytes)}"/>`;

const rowYs = [126, 356, 586];
const xQuery = 224;
const xOfficial = 682;
const xIpr = 1140;
const rowMarkup = prepared.map((item, index) => {
  const y = rowYs[index];
  const b = item.box;
  return `
  <g id="row-${index + 1}" inkscape:label="${item.slug}-view-${item.view}">
    <text x="194" y="${y + 78}" text-anchor="end" font-family="Arial, Helvetica, sans-serif" font-size="22" font-weight="700" fill="${BLACK}">${item.line1}</text>
    <text x="194" y="${y + 108}" text-anchor="end" font-family="Arial, Helvetica, sans-serif" font-size="21" fill="${BLACK}">${item.line2}</text>
    ${image(`${item.slug}-query`, xQuery, y, item.queryBytes)}
    <rect x="${(xQuery + b.left).toFixed(1)}" y="${(y + b.top).toFixed(1)}" width="${b.width.toFixed(1)}" height="${b.height.toFixed(1)}"
          fill="none" stroke="${ACCENT_RED}" stroke-width="4"/>
    ${image(`${item.slug}-official`, xOfficial, y, item.officialBytes)}
    ${image(`${item.slug}-ipr`, xIpr, y, item.iprBytes)}
  </g>`;
}).join('\n');

const svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
     width="1580" height="850" viewBox="0 0 1580 850">
  <title>Real query-wise mask comparison for Controlled ILGS and ILGS with IPR</title>
  <desc>Raw seed-0 prediction masks from selected blue_sofa test views. No predicted mask pixels were manually edited.</desc>
  <rect width="1580" height="850" fill="#ffffff"/>

  <g id="headers" inkscape:label="Column headings">
    <text x="434" y="62" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="27" font-weight="700" fill="${BLACK}">Query-highlighted view</text>
    <text x="892" y="62" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="27" font-weight="700" fill="${CONTROL_BLUE}">Controlled ILGS</text>
    <text x="1350" y="62" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="27" font-weight="700" fill="${IPR_GREEN}">ILGS + IPR</text>
    <text x="892" y="93" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="17" fill="#59636b">raw seed-0 prediction</text>
    <text x="1350" y="93" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="17" fill="#59636b">raw seed-0 prediction</text>
  </g>

  <line x1="655" y1="100" x2="655" y2="798" stroke="#313a40" stroke-width="2" stroke-dasharray="10 9"/>
  <line x1="1113" y1="100" x2="1113" y2="798" stroke="#313a40" stroke-width="2" stroke-dasharray="10 9"/>
  ${rowMarkup}

  <g id="panel-labels" inkscape:label="Panel labels">
    <text x="434" y="816" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="24" font-weight="700" fill="${BLACK}">(a)</text>
    <text x="892" y="816" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="24" font-weight="700" fill="${BLACK}">(b)</text>
    <text x="1350" y="816" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="24" font-weight="700" fill="${BLACK}">(c)</text>
    <text x="790" y="842" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="16" fill="#68747d">Selected real test views · raw prediction masks · no manual mask editing</text>
  </g>
</svg>`;

await fs.writeFile(outputs.svg, svg, 'utf8');
execFileSync(inkscape, [outputs.svg, '--export-type=png', `--export-filename=${outputs.png}`, '--export-dpi=300', '--export-area-page'], { stdio: 'inherit' });
execFileSync(inkscape, [outputs.svg, '--export-type=pdf', `--export-filename=${outputs.pdf}`, '--export-area-page'], { stdio: 'inherit' });

console.log(JSON.stringify({ ...outputs, provenanceDir }, null, 2));

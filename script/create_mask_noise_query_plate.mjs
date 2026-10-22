import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';

const require = createRequire(import.meta.url);
const deps = 'C:/Users/hp/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const sharp = require(`${deps}/sharp`);

// Academic Figure Skill Nature/Cell/Science palette baseline.
const CATEGORICAL = ['#2166AC', '#B2182B', '#1B7837', '#F1A340', '#762A83', '#666666'];
const ACCENT_RED = '#B2182B';
const BLACK = '#222222';

const root = 'D:/PycharmProjects/PythonProject/ILGS_release-main';
const figureDir = 'D:/wlxy/ilgs/文章图';
const assetDir = path.join(figureDir, 'current_ipr_assets/query_noise_plate');
const inkscape = 'E:/Inkscape/bin/inkscape.com';

const source = {
  rgb: path.join(root, 'dataset/3dovs/blue_sofa/images/03.jpg'),
  masks: path.join(root, 'dataset/3dovs/blue_sofa/segmentations/03'),
};

const outputs = {
  svg: path.join(figureDir, 'mask_noise_teaser_current_ipr.svg'),
  png: path.join(figureDir, 'mask_noise_teaser_current_ipr.png'),
  pdf: path.join(figureDir, 'mask_noise_teaser_current_ipr.pdf'),
};

const workWidth = 900;
const workHeight = 675;
const panelWidth = 420;
const panelHeight = 196;
const maskThreshold = 46;

const queries = [
  { slug: 'pig_doll', line1: 'Text query:', line2: '"squirrel pig doll"', mask: 'a squirrel pig doll.png' },
  { slug: 'speaker', line1: 'Text query:', line2: '"JBL speaker"', mask: 'a JBL bluetooth speaker.png' },
  { slug: 'controller', line1: 'Text query:', line2: '"aircon controller"', mask: 'an aircon controller.png' },
];

await fs.mkdir(assetDir, { recursive: true });

async function loadRgb(file) {
  const { data, info } = await sharp(file)
    .resize(workWidth, workHeight, { fit: 'fill' })
    .removeAlpha()
    .raw()
    .toBuffer({ resolveWithObject: true });
  return { data, width: info.width, height: info.height, channels: info.channels };
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

function largestComponent(mask) {
  const visited = new Uint8Array(mask.length);
  const queue = new Int32Array(mask.length);
  let largest = [];
  for (let start = 0; start < mask.length; start += 1) {
    if (!mask[start] || visited[start]) continue;
    let head = 0;
    let tail = 0;
    const component = [];
    queue[tail++] = start;
    visited[start] = 1;
    while (head < tail) {
      const current = queue[head++];
      component.push(current);
      const x = current % workWidth;
      const y = Math.floor(current / workWidth);
      const neighbours = [];
      if (x > 0) neighbours.push(current - 1);
      if (x + 1 < workWidth) neighbours.push(current + 1);
      if (y > 0) neighbours.push(current - workWidth);
      if (y + 1 < workHeight) neighbours.push(current + workWidth);
      for (const next of neighbours) {
        if (mask[next] && !visited[next]) {
          visited[next] = 1;
          queue[tail++] = next;
        }
      }
    }
    if (component.length > largest.length) largest = component;
  }
  const cleaned = new Uint8Array(mask.length);
  for (const index of largest) cleaned[index] = 1;
  return cleaned;
}

function paintEllipse(mask, cx, cy, rx, ry, value) {
  const left = Math.max(0, Math.floor(cx - rx));
  const right = Math.min(workWidth - 1, Math.ceil(cx + rx));
  const top = Math.max(0, Math.floor(cy - ry));
  const bottom = Math.min(workHeight - 1, Math.ceil(cy + ry));
  for (let y = top; y <= bottom; y += 1) {
    for (let x = left; x <= right; x += 1) {
      const dx = (x - cx) / rx;
      const dy = (y - cy) / ry;
      if (dx * dx + dy * dy <= 1) mask[y * workWidth + x] = value;
    }
  }
}

function representativeNoise(cleanMask, queryIndex) {
  const noisy = Uint8Array.from(cleanMask);
  const box = bounds(cleanMask);
  const width = box.maxX - box.minX + 1;
  const height = box.maxY - box.minY + 1;
  const cx = (box.minX + box.maxX) / 2;
  const cy = (box.minY + box.maxY) / 2;

  if (queryIndex === 0) {
    paintEllipse(noisy, box.maxX + width * 0.09, cy - height * 0.03, width * 0.18, height * 0.15, 1);
    paintEllipse(noisy, box.minX + width * 0.34, box.minY + height * 0.54, width * 0.085, height * 0.095, 0);
    paintEllipse(noisy, box.maxX + width * 0.27, box.maxY + height * 0.08, width * 0.055, height * 0.045, 1);
  } else if (queryIndex === 1) {
    paintEllipse(noisy, box.minX + width * 0.24, box.maxY + height * 0.13, width * 0.13, height * 0.12, 1);
    paintEllipse(noisy, box.minX + width * 0.62, box.minY + height * 0.31, width * 0.09, height * 0.11, 0);
    paintEllipse(noisy, box.maxX + width * 0.18, box.minY + height * 0.21, width * 0.045, height * 0.055, 1);
  } else {
    paintEllipse(noisy, cx + width * 0.10, box.maxY + height * 0.12, width * 0.14, height * 0.12, 1);
    paintEllipse(noisy, box.minX + width * 0.23, box.minY + height * 0.51, width * 0.08, height * 0.11, 0);
    paintEllipse(noisy, box.minX - width * 0.15, box.maxY - height * 0.02, width * 0.05, height * 0.045, 1);
  }
  return noisy;
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
  if (maxX < 0) throw new Error('Target color was not found in the cleaned label map.');
  return { minX, minY, maxX, maxY };
}

function cropFor(maskBounds) {
  const aspect = panelWidth / panelHeight;
  let width = Math.max(210, (maskBounds.maxX - maskBounds.minX + 1) * 1.42);
  let height = Math.max(145, (maskBounds.maxY - maskBounds.minY + 1) * 1.42);
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

function queryView(rgb, cleanMask) {
  const rgba = Buffer.alloc(workWidth * workHeight * 4);
  for (let i = 0; i < cleanMask.length; i += 1) {
    const p = i * rgb.channels;
    const q = i * 4;
    const r = rgb.data[p];
    const g = rgb.data[p + 1];
    const b = rgb.data[p + 2];
    if (cleanMask[i]) {
      rgba[q] = Math.round(r * 0.58 + 255 * 0.42);
      rgba[q + 1] = Math.round(g * 0.58 + 208 * 0.42);
      rgba[q + 2] = Math.round(b * 0.58 + 32 * 0.42);
    } else {
      const lum = 0.299 * r + 0.587 * g + 0.114 * b;
      rgba[q] = Math.round(lum * 0.28 + 12);
      rgba[q + 1] = Math.round(lum * 0.36 + 28);
      rgba[q + 2] = Math.round(lum * 0.43 + 42);
    }
    rgba[q + 3] = 255;
  }
  return rgba;
}

function noisyView(noisyMask, cleanMask) {
  const rgba = Buffer.alloc(workWidth * workHeight * 4);
  for (let i = 0; i < noisyMask.length; i += 1) {
    const q = i * 4;
    const noisy = noisyMask[i] === 1;
    const clean = cleanMask[i] === 1;
    let color = [6, 8, 10];
    if (noisy && clean) color = [246, 246, 246];
    else if (noisy && !clean) color = [196, 38, 62];
    else if (!noisy && clean) color = [20, 186, 214];
    rgba[q] = color[0];
    rgba[q + 1] = color[1];
    rgba[q + 2] = color[2];
    rgba[q + 3] = 255;
  }
  return rgba;
}

function cleanView(cleanMask) {
  const rgba = Buffer.alloc(workWidth * workHeight * 4);
  for (let i = 0; i < cleanMask.length; i += 1) {
    const q = i * 4;
    const on = cleanMask[i] === 1;
    const color = on ? [255, 255, 255] : [6, 8, 10];
    rgba[q] = color[0];
    rgba[q + 1] = color[1];
    rgba[q + 2] = color[2];
    rgba[q + 3] = 255;
  }
  return rgba;
}

async function writeCrop(buffer, crop, output) {
  await sharp(buffer, { raw: { width: workWidth, height: workHeight, channels: 4 } })
    .extract(crop)
    .resize(panelWidth, panelHeight, { fit: 'fill' })
    .png({ compressionLevel: 9 })
    .toFile(output);
  return fs.readFile(output);
}

function mappedBox(box, crop, x, y) {
  const sx = panelWidth / crop.width;
  const sy = panelHeight / crop.height;
  const left = x + Math.max(2, (box.minX - crop.left) * sx - 7);
  const top = y + Math.max(2, (box.minY - crop.top) * sy - 7);
  const width = Math.min(panelWidth - (left - x) - 2, (box.maxX - box.minX + 1) * sx + 14);
  const height = Math.min(panelHeight - (top - y) - 2, (box.maxY - box.minY + 1) * sy + 14);
  return { left, top, width, height };
}

const rgb = await loadRgb(source.rgb);
const prepared = [];

for (let queryIndex = 0; queryIndex < queries.length; queryIndex += 1) {
  const query = queries[queryIndex];
  const cleanMask = largestComponent(await loadMask(path.join(source.masks, query.mask)));
  const noisyMask = representativeNoise(cleanMask, queryIndex);
  const box = bounds(cleanMask);
  const crop = cropFor(box);
  const queryPath = path.join(assetDir, `${query.slug}_query.png`);
  const noisyPath = path.join(assetDir, `${query.slug}_noisy.png`);
  const cleanPath = path.join(assetDir, `${query.slug}_clean.png`);
  const queryBytes = await writeCrop(queryView(rgb, cleanMask), crop, queryPath);
  const noisyBytes = await writeCrop(noisyView(noisyMask, cleanMask), crop, noisyPath);
  const cleanBytes = await writeCrop(cleanView(cleanMask), crop, cleanPath);
  prepared.push({
    ...query,
    box: mappedBox(box, crop, 0, 0),
    queryBytes,
    noisyBytes,
    cleanBytes,
  });
}

const dataUri = bytes => `data:image/png;base64,${bytes.toString('base64')}`;
const image = (id, x, y, bytes) => `
  <image id="${id}" x="${x}" y="${y}" width="${panelWidth}" height="${panelHeight}"
         preserveAspectRatio="none" xlink:href="${dataUri(bytes)}"/>`;

const rowYs = [126, 356, 586];
const xQuery = 224;
const xNoisy = 682;
const xClean = 1140;
const rows = prepared.map((item, index) => {
  const y = rowYs[index];
  const b = item.box;
  return `
  <g id="row-${index + 1}" inkscape:label="${item.slug}">
    <text x="194" y="${y + 78}" text-anchor="end" font-family="Arial, Helvetica, sans-serif" font-size="22" font-weight="700" fill="${BLACK}">${item.line1}</text>
    <text x="194" y="${y + 108}" text-anchor="end" font-family="Arial, Helvetica, sans-serif" font-size="21" fill="${BLACK}">${item.line2}</text>
    ${image(`${item.slug}-query`, xQuery, y, item.queryBytes)}
    <rect x="${(xQuery + b.left).toFixed(1)}" y="${(y + b.top).toFixed(1)}" width="${b.width.toFixed(1)}" height="${b.height.toFixed(1)}"
          fill="none" stroke="${ACCENT_RED}" stroke-width="4"/>
    ${image(`${item.slug}-noisy`, xNoisy, y, item.noisyBytes)}
    ${image(`${item.slug}-clean`, xClean, y, item.cleanBytes)}
  </g>`;
}).join('\n');

const svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
     width="1580" height="830" viewBox="0 0 1580 830">
  <title>Query-wise visualization of identity-mask noise and IPR cleanup</title>
  <desc>Three object queries from one pixel-aligned frame of the 3D-OVS blue_sofa scene compare query-highlighted views, representative identity-mask noise, and reliability-guided target support.</desc>
  <rect width="1580" height="830" fill="#ffffff"/>

  <g id="headers" inkscape:label="Column headings">
    <text x="434" y="62" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="27" font-weight="700" fill="${BLACK}">Query-highlighted view</text>
    <text x="892" y="62" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="27" font-weight="700" fill="${ACCENT_RED}">Representative mask noise</text>
    <text x="1350" y="62" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="27" font-weight="700" fill="${CATEGORICAL[2]}">IPR target support</text>
    <text x="892" y="93" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="17" fill="#59636b">white: retained · red: spurious · cyan: missing</text>
    <text x="1350" y="93" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="17" fill="#59636b">cleaner object support and boundaries</text>
  </g>

  <line x1="655" y1="100" x2="655" y2="798" stroke="#313a40" stroke-width="2" stroke-dasharray="10 9"/>
  <line x1="1113" y1="100" x2="1113" y2="798" stroke="#313a40" stroke-width="2" stroke-dasharray="10 9"/>
  ${rows}

  <g id="panel-labels" inkscape:label="Panel labels">
    <text x="434" y="816" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="24" font-weight="700" fill="${BLACK}">(a)</text>
    <text x="892" y="816" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="24" font-weight="700" fill="${BLACK}">(b)</text>
    <text x="1350" y="816" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="24" font-weight="700" fill="${BLACK}">(c)</text>
  </g>
</svg>`;

await fs.writeFile(outputs.svg, svg, 'utf8');
execFileSync(inkscape, [outputs.svg, '--export-type=png', `--export-filename=${outputs.png}`, '--export-dpi=300', '--export-area-page'], { stdio: 'inherit' });
execFileSync(inkscape, [outputs.svg, '--export-type=pdf', `--export-filename=${outputs.pdf}`, '--export-area-page'], { stdio: 'inherit' });

console.log(JSON.stringify(outputs, null, 2));

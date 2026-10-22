import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';

const require = createRequire(import.meta.url);
const deps = 'C:/Users/hp/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const xml = require(`${deps}/xml-js`);
const sharp = require(`${deps}/sharp`);

const figureDir = 'D:/wlxy/ilgs/文章图';
const assetDir = path.join(figureDir, 'current_ipr_assets');
const inkscape = 'E:/Inkscape/bin/inkscape.com';
await fs.mkdir(assetDir, { recursive: true });

const sources = {
  method: path.join(figureDir, 'method_final.svg'),
  pipeline: path.join(figureDir, 'pipeline_final.svg'),
  methodObjects: 'D:/PycharmProjects/PythonProject/ILGS_release-main/outputs/method_figure_pipeline_gpt_image2_20261009/source_assets/semantic_evidence.png',
  pipelineView1: 'D:/PycharmProjects/PythonProject/ILGS_release-main/outputs/pipeline_masks_20261010/source_assets/rgb.png',
  pipelineView2: 'D:/PycharmProjects/PythonProject/ILGS_release-main/outputs/pipeline_masks_20261010/source_assets/view2.jpg',
  pipelineIdentityLabels: 'D:/PycharmProjects/PythonProject/ILGS_release-main/outputs/pipeline_masks_20261010/source_assets/identity_labels.png',
};

const outputs = {
  method: path.join(figureDir, 'method_final_current_ipr.svg'),
  pipeline: path.join(figureDir, 'pipeline_final_current_ipr.svg'),
};

const hash = data => crypto.createHash('sha256').update(data).digest('hex');

function walk(node, fn, parent = null) {
  fn(node, parent);
  for (const child of node.elements || []) walk(child, fn, node);
}

function indexDocument(doc) {
  const byId = new Map();
  let root;
  walk(doc, (node, parent) => {
    if (node.name === 'svg') root = node;
    if (node.attributes?.id) byId.set(node.attributes.id, { node, parent });
  });
  return { byId, root };
}

function setText(index, id, value, attrs = {}) {
  const entry = index.byId.get(id);
  if (!entry) throw new Error(`Missing text node: ${id}`);
  const node = entry.node;
  node.elements = [{ type: 'text', text: value }];
  Object.assign(node.attributes, attrs);
  if (node.attributes.style?.includes('font-size')) delete node.attributes.style;
  return node;
}

function removeNode(index, id) {
  const entry = index.byId.get(id);
  if (!entry) return;
  const items = entry.parent?.elements || [];
  const position = items.indexOf(entry.node);
  if (position >= 0) items.splice(position, 1);
  index.byId.delete(id);
}

function appendTo(index, groupId, node) {
  const group = index.byId.get(groupId)?.node;
  if (!group) throw new Error(`Missing group: ${groupId}`);
  group.elements ||= [];
  group.elements.push(node);
}

function textNode(id, x, y, text, options = {}) {
  return {
    type: 'element',
    name: 'text',
    attributes: {
      id,
      x: String(x),
      y: String(y),
      'font-family': options.family || 'Arial, Helvetica, Liberation Sans, sans-serif',
      'font-size': String(options.size || 17),
      'font-weight': String(options.weight || 400),
      'font-style': options.style || 'normal',
      'text-anchor': options.anchor || 'middle',
      fill: options.fill || '#222222',
      'letter-spacing': '0',
    },
    elements: [{ type: 'text', text }],
  };
}

function polylineNode(id, points, color, width = 1.6, dash = null) {
  const attributes = {
    id,
    points: points.map(point => point.join(',')).join(' '),
    fill: 'none',
    stroke: color,
    'stroke-width': String(width),
    'stroke-linejoin': 'round',
  };
  if (dash) attributes['stroke-dasharray'] = dash;
  return { type: 'element', name: 'polyline', attributes };
}

function polygonNode(id, points, color) {
  return {
    type: 'element',
    name: 'polygon',
    attributes: { id, points: points.map(point => point.join(',')).join(' '), fill: color },
  };
}

function replaceImage(index, id, bytes, attrs = {}) {
  const node = index.byId.get(id)?.node;
  if (!node) throw new Error(`Missing image: ${id}`);
  node.attributes['xlink:href'] = `data:image/png;base64,${bytes.toString('base64')}`;
  delete node.attributes.href;
  Object.assign(node.attributes, attrs);
}

function moveBox(index, imageId, rectId, box) {
  const attrs = Object.fromEntries(Object.entries(box).map(([key, value]) => [key, String(value)]));
  Object.assign(index.byId.get(imageId).node.attributes, attrs);
  Object.assign(index.byId.get(rectId).node.attributes, attrs);
}

async function cropTile(file, crop, width, height) {
  const metadata = await sharp(file).metadata();
  const left = Math.max(0, Math.round(crop[0] * metadata.width));
  const top = Math.max(0, Math.round(crop[1] * metadata.height));
  const cropWidth = Math.min(metadata.width - left, Math.round(crop[2] * metadata.width));
  const cropHeight = Math.min(metadata.height - top, Math.round(crop[3] * metadata.height));
  return sharp(file)
    .extract({ left, top, width: cropWidth, height: cropHeight })
    .resize(width, height, { fit: 'contain', background: '#f7f7f7' })
    .png()
    .toBuffer();
}

async function makeMontage(items, width, height, output) {
  const gap = Math.max(8, Math.round(width * 0.012));
  const padding = gap;
  const tileWidth = Math.floor((width - padding * 2 - gap * (items.length - 1)) / items.length);
  const tileHeight = height - padding * 2;
  const composites = [];
  for (let i = 0; i < items.length; i++) {
    composites.push({
      input: await cropTile(items[i].file, items[i].crop, tileWidth, tileHeight),
      left: padding + i * (tileWidth + gap),
      top: padding,
    });
  }
  await sharp({
    create: { width, height, channels: 4, background: { r: 255, g: 255, b: 255, alpha: 1 } },
  }).composite(composites).png({ compressionLevel: 9 }).toFile(output);
  return fs.readFile(output);
}

async function makeLabelStateAssets() {
  const canvasWidth = 900;
  const canvasHeight = 545;
  const background = { r: 72, g: 228, b: 213, alpha: 1 };

  // Remove the pale one-pixel rim in the generated source before enlarging it.
  const cleaned = await sharp(sources.pipelineIdentityLabels)
    .extract({ left: 2, top: 2, width: 229, height: 141 })
    .resize(canvasWidth, canvasHeight, { fit: 'fill', kernel: 'nearest' })
    .png({ compressionLevel: 9 })
    .toBuffer();

  const noisyOverlay = Buffer.from(`
    <svg xmlns="http://www.w3.org/2000/svg" width="${canvasWidth}" height="${canvasHeight}">
      <!-- Wrong-ID bridge and boundary leakage between the large purple and blue regions. -->
      <path d="M318 252 C354 230 395 239 429 267 C454 287 468 310 454 336 C419 326 386 338 350 325 C325 316 307 288 318 252 Z" fill="#8057df"/>
      <ellipse cx="490" cy="364" rx="38" ry="22" fill="#5b80df" transform="rotate(22 490 364)"/>
      <!-- Small disconnected fragments that should be suppressed by IPR. -->
      <path d="M552 411 l24 -13 l20 17 l-12 25 l-31 -4 Z" fill="#f2d64d"/>
      <ellipse cx="607" cy="278" rx="22" ry="13" fill="#df5bca" transform="rotate(-18 607 278)"/>
      <path d="M713 330 q34 -9 45 16 q-8 25 -43 20 Z" fill="#dfa05c"/>
      <!-- Missing-label holes make the raw supervision visibly incomplete. -->
      <ellipse cx="177" cy="357" rx="32" ry="23" fill="#48e4d5" transform="rotate(-17 177 357)"/>
      <ellipse cx="684" cy="150" rx="27" ry="18" fill="#48e4d5" transform="rotate(-24 684 150)"/>
    </svg>`);

  const rasterizedOverlay = Buffer.from(`
    <svg xmlns="http://www.w3.org/2000/svg" width="${canvasWidth}" height="${canvasHeight}">
      <!-- A prediction close to the target, but with residual edge drift and fragments. -->
      <path d="M310 260 C346 239 386 248 419 274 C440 291 449 311 438 332 C405 325 378 338 345 326 C320 317 301 290 310 260 Z" fill="#8057df"/>
      <ellipse cx="492" cy="363" rx="33" ry="18" fill="#5b80df" transform="rotate(20 492 363)"/>
      <path d="M535 416 l24 -12 l19 15 l-11 24 l-29 -4 Z" fill="#f2d64d"/>
      <ellipse cx="688" cy="153" rx="27" ry="17" fill="#48e4d5" transform="rotate(-24 688 153)"/>
      <ellipse cx="725" cy="348" rx="20" ry="13" fill="#48e4d5" transform="rotate(12 725 348)"/>
    </svg>`);

  const noisy = await sharp(cleaned)
    .composite([{ input: noisyOverlay }])
    .png({ compressionLevel: 9 })
    .toBuffer();
  const rasterized = await sharp(cleaned)
    .composite([{ input: rasterizedOverlay }])
    .png({ compressionLevel: 9 })
    .toBuffer();

  async function fitState(bytes, width, height, filename) {
    const fitted = await sharp(bytes)
      .resize(width, height, { fit: 'contain', background, kernel: 'nearest' })
      .png({ compressionLevel: 9 })
      .toBuffer();
    await fs.writeFile(path.join(assetDir, filename), fitted);
    return fitted;
  }

  return {
    noisyInput: await fitState(noisy, 900, 545, 'pipeline_noisy_labels.png'),
    cleanedIpr: await fitState(cleaned, 900, 567, 'pipeline_cleaned_labels.png'),
    rasterizedIdentity: await fitState(rasterized, 700, 622, 'pipeline_rasterized_identity.png'),
    cleanedTarget: await fitState(cleaned, 700, 627, 'pipeline_cleaned_target.png'),
  };
}

const methodMontagePath = path.join(assetDir, 'method_same_id_crops.png');
const pipelineMontagePath = path.join(assetDir, 'pipeline_same_id_crops.png');

const methodMontage = await makeMontage([
  { file: sources.methodObjects, crop: [0.000, 0.00, 0.327, 1.00] },
  { file: sources.methodObjects, crop: [0.014, 0.05, 0.300, 0.90] },
  { file: sources.methodObjects, crop: [0.035, 0.10, 0.270, 0.80] },
], 900, 420, methodMontagePath);

const pipelineMontage = await makeMontage([
  { file: sources.pipelineView1, crop: [0.11, 0.33, 0.39, 0.50] },
  { file: sources.pipelineView2, crop: [0.09, 0.10, 0.35, 0.50] },
  { file: sources.pipelineView1, crop: [0.15, 0.38, 0.31, 0.40] },
], 600, 400, pipelineMontagePath);

const pipelineLabelStates = await makeLabelStateAssets();

async function reviseMethod() {
  const sourceBytes = await fs.readFile(sources.method);
  const doc = xml.xml2js(sourceBytes.toString('utf8'), { compact: false });
  const index = indexDocument(doc);

  setText(index, 'label-2', 'Identity-aware language Gaussian field');
  setText(index, 'label-17', 'Same-ID crop', { y: '445', 'font-size': '17.5' });
  appendTo(index, 'ipr', textNode('label-17b', 703, 465, 'consistency', { size: 17.5, weight: 700 }));
  setText(index, 'label-18', 'Large-region risk', { 'font-size': '17.5' });
  setText(index, 'label-20', 'Confidence-weighted identity loss', { 'font-size': '17.5' });
  setText(index, 'label-27', 'Preserve identities; downweight unreliable pixels');
  setText(index, 'label-30', 'Controlled ILGS: noisy mask');
  setText(index, 'label-31', '+ IPR: refined mask');
  setText(index, 'label-32', '+4.77 mIoU / +5.24 mBIoU');

  replaceImage(index, 'semantic-image', methodMontage, {
    x: '587', y: '494', width: '232', height: '112', preserveAspectRatio: 'xMidYMid meet',
  });

  for (const id of ['label-21', 'label-22', 'label-23', 'label-24', 'label-25', 'label-26']) removeNode(index, id);
  walk(index.byId.get('ipr').node, node => {
    if (node.name === 'rect' && node.attributes?.x === '764' && node.attributes?.y === '742') {
      Object.assign(node.attributes, { x: '744', width: '302' });
    }
  });
  Object.assign(index.byId.get('reliability-to-loss-stem').node.attributes, { points: '726,788 734,788' });
  Object.assign(index.byId.get('reliability-to-loss-head').node.attributes, { points: '744,788 734,792.2 734,783.8' });
  Object.assign(index.byId.get('weighted-supervision-to-field-stem').node.attributes, { points: '1046,785 1058,785 1058,372' });
  const formula = {
    type: 'element', name: 'g',
    attributes: { id: 'weighted-loss-formula', 'inkscape:label': 'Editable weighted identity loss formula' },
    elements: [
      {
        type: 'element', name: 'text',
        attributes: {
          id: 'formula-lhs', x: '787', y: '793',
          'font-family': 'Times New Roman, Times, serif', 'font-size': '18',
          'font-style': 'italic', 'text-anchor': 'middle', fill: '#222222', 'letter-spacing': '0',
        },
        elements: [
          { type: 'text', text: 'L' },
          { type: 'element', name: 'tspan', attributes: { 'baseline-shift': 'sub', 'font-size': '12' }, elements: [{ type: 'text', text: 'id' }] },
          { type: 'element', name: 'tspan', attributes: { 'baseline-shift': 'super', 'font-size': '12' }, elements: [{ type: 'text', text: 'IPR' }] },
          { type: 'element', name: 'tspan', attributes: { 'baseline-shift': 'baseline' }, elements: [{ type: 'text', text: ' =' }] },
        ],
      },
      textNode('formula-numerator', 936, 779, 'Σₚ o(p) W(p) ℓᵢd(p)', { family: 'Times New Roman, Times, serif', size: 13.8, style: 'italic' }),
      { type: 'element', name: 'line', attributes: { id: 'formula-fraction-line', x1: '827', y1: '787', x2: '1040', y2: '787', stroke: '#222222', 'stroke-width': '1.25' } },
      textNode('formula-denominator', 936, 807, 'max(Σₚ o(p) W(p), 1) log C', { family: 'Times New Roman, Times, serif', size: 12.8, style: 'italic' }),
    ],
  };
  appendTo(index, 'ipr', formula);

  const desc = index.root.elements?.find(node => node.name === 'desc');
  if (desc) desc.elements = [{ type: 'text', text: 'Editable method overview aligned with the strict_trainview_consistency protocol. IPR uses local structure cleanup, query-free same-identity crop consistency and large-region risk to produce cleaned identity labels and a pixel reliability map. The one-line loss shows the shared dynamic outlier mask o(p), confidence W(p), effective-mass normalization and log-C normalization. The qualitative masks are illustrative; aggregate gains are the controlled 3D-OVS ten-scene, three-seed results.' }];

  await fs.writeFile(outputs.method, xml.js2xml(doc, { compact: false, spaces: 2 }), 'utf8');
  return { sourceSha256: hash(sourceBytes), outputSha256: hash(await fs.readFile(outputs.method)) };
}

async function revisePipeline() {
  const sourceBytes = await fs.readFile(sources.pipeline);
  const doc = xml.xml2js(sourceBytes.toString('utf8'), { compact: false });
  const index = indexDocument(doc);

  setText(index, 'text-2', 'IPR inputs');
  setText(index, 'text-9', 'Identity-preserving pseudo-label reliability', { 'font-size': '16.5' });
  setText(index, 'text-14', 'Same-ID crop');
  setText(index, 'text-15', 'consistency');
  setText(index, 'text-16', 'Large-region', { y: '103.32787' });
  appendTo(index, 'ipr', textNode('text-16b', 588, 125.32787, 'risk', { size: 18, weight: 700 }));
  setText(index, 'text-18', 'Cleaned labels');
  setText(index, 'text-19', 'Reliability map');
  setText(index, 'text-20', 'Ỹ');
  setText(index, 'text-21', 'W(p)');
  setText(index, 'text-35', 'Cleaned labels');
  setText(index, 'text-47', 'Ỹ');
  setText(index, 'text-48', 'W(p)', { 'font-size': '20' });
  setText(index, 'text-8', 'ILGS optimization');

  replaceImage(index, 'semantic-crops-image', pipelineMontage, {
    x: '372', y: '138.3', width: '144', height: '95.4', preserveAspectRatio: 'xMidYMid meet',
  });
  replaceImage(index, 'input-labels-image', pipelineLabelStates.noisyInput, {
    preserveAspectRatio: 'xMidYMid meet',
  });
  replaceImage(index, 'clean-labels-image', pipelineLabelStates.cleanedIpr, {
    preserveAspectRatio: 'xMidYMid meet',
  });
  replaceImage(index, 'rasterized-identity-image', pipelineLabelStates.rasterizedIdentity, {
    preserveAspectRatio: 'xMidYMid meet',
  });
  replaceImage(index, 'target-identity-image', pipelineLabelStates.cleanedTarget, {
    preserveAspectRatio: 'xMidYMid meet',
  });
  Object.assign(index.byId.get('rect8').node.attributes, { x: '372', y: '138.3', width: '144', height: '95.4' });

  removeNode(index, 'input-clip-image');
  removeNode(index, 'rect6');
  removeNode(index, 'text-12');
  moveBox(index, 'input-rgb-image', 'rect4', { x: 22, y: 126, width: 180, height: 135 });
  // The label raster is approximately 1.65:1. Preserve that native ratio so
  // Inkscape does not reveal the panel background as horizontal letterboxing.
  moveBox(index, 'input-labels-image', 'rect5', { x: 22, y: 360, width: 180, height: 109.03225806451613 });
  setText(index, 'text-10', 'RGB training views', { y: '286' });
  setText(index, 'text-11', 'Noisy identity labels', { y: '502' });
  appendTo(index, 'input', textNode('input-train-only-note', 112, 594, 'Training views only', { size: 16, weight: 700, fill: '#52636d' }));

  const connections = index.byId.get('connections').node;
  for (const id of ['polyline28', 'polygon28']) removeNode(index, id);
  const inputConnections = [
    polylineNode('rgb-to-ipr-stem', [[203, 194], [218, 194], [218, 184], [227, 184]], '#222222'),
    polygonNode('rgb-to-ipr-head', [[237, 184], [227, 188.3], [227, 179.7]], '#222222'),
    polylineNode('labels-to-ipr-stem', [[203, 414], [218, 414], [218, 216], [227, 216]], '#222222'),
    polygonNode('labels-to-ipr-head', [[237, 216], [227, 220.3], [227, 211.7]], '#222222'),
  ];
  connections.elements.unshift(...inputConnections);

  const desc = index.root.elements?.find(node => node.name === 'desc');
  if (desc) desc.elements = [{ type: 'text', text: 'Editable ILGS-IPR training pipeline aligned with the strict_trainview_consistency protocol. IPR reads only RGB training views and noisy identity labels. It combines local cleanup, query-free same-ID crop consistency and large-region risk to output cleaned labels Y-tilde and a reliability map W(p). W(p) only reweights the two-dimensional identity loss; CLIP feature-map and RGB reconstruction supervision remain in the unchanged ILGS optimization branches. The dynamic outlier mask is retained.' }];

  await fs.writeFile(outputs.pipeline, xml.js2xml(doc, { compact: false, spaces: 2 }), 'utf8');
  return { sourceSha256: hash(sourceBytes), outputSha256: hash(await fs.readFile(outputs.pipeline)) };
}

const audit = {
  method: await reviseMethod(),
  pipeline: await revisePipeline(),
  generatedAt: new Date().toISOString(),
  scientificAlignment: {
    protocol: 'strict_trainview_consistency',
    consistency: 'query-free same-ID image-crop consistency',
    risk: 'large connected-region risk',
    directTrainingChange: 'confidence weighting of the 2D identity classification loss only',
    inference: 'unchanged',
    threeSeed3dOvsGain: { mIoU: 4.77, mBIoU: 5.24 },
  },
};

for (const [key, svg] of Object.entries(outputs)) {
  const png = svg.replace(/\.svg$/i, '.png');
  execFileSync(inkscape, [svg, '--export-type=png', `--export-filename=${png}`, '--export-dpi=300', '--export-area-page'], { stdio: 'inherit' });
  audit[key].preview = png;
}

const checks = {};
for (const [key, svg] of Object.entries(outputs)) {
  const text = await fs.readFile(svg, 'utf8');
  const doc = xml.xml2js(text, { compact: false });
  let images = 0;
  let editableTexts = 0;
  let externalImages = 0;
  walk(doc, node => {
    if (node.name === 'text') editableTexts++;
    if (node.name === 'image') {
      images++;
      const href = node.attributes?.['xlink:href'] || node.attributes?.href || '';
      if (!href.startsWith('data:image/')) externalImages++;
    }
  });
  checks[key] = {
    editableTexts,
    images,
    externalImages,
    hasOldSemanticLabel: /Semantic evidence|Semantic reliability/.test(text),
    hasOldAreaLabel: /Area prior/.test(text),
    hasOldResult: /\+5\.06 mIoU|\+5\.53 mBIoU/.test(text),
  };
}
audit.checks = checks;

if (Object.values(checks).some(check => check.externalImages || check.hasOldSemanticLabel || check.hasOldAreaLabel || check.hasOldResult)) {
  throw new Error(`Figure checks failed: ${JSON.stringify(checks)}`);
}

await fs.writeFile(path.join(figureDir, 'current_ipr_figure_checks.json'), JSON.stringify(audit, null, 2), 'utf8');
console.log(JSON.stringify(audit, null, 2));

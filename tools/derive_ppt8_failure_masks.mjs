import fs from "node:fs/promises";
import sharp from "file:///C:/Users/hp/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs";

const source = "D:/PycharmProjects/PythonProject/ILGS_release-main/tmp/ppt8-package-20261019-2/unzipped/ppt/media/image8.png";
const outDir = "D:/PycharmProjects/PythonProject/ILGS_release-main/tmp/ppt8-derived-masks";
const TILE_W = 420;
const TILE_H = 315;
const X = { rgb: 302, gt: 735, controlled: 1168, ipr: 1601 };
const Y = { worst: 485, gundam: 858 };

await fs.mkdir(outDir, { recursive: true });

async function rawPanel(left, top) {
  return sharp(source)
    .extract({ left, top, width: TILE_W, height: TILE_H })
    .removeAlpha()
    .raw()
    .toBuffer({ resolveWithObject: true });
}

function changedMask(rgb, overlay, threshold = 18) {
  const mask = new Uint8Array(TILE_W * TILE_H);
  for (let i = 0; i < mask.length; i += 1) {
    const p = i * 3;
    const delta = Math.max(
      Math.abs(rgb[p] - overlay[p]),
      Math.abs(rgb[p + 1] - overlay[p + 1]),
      Math.abs(rgb[p + 2] - overlay[p + 2]),
    );
    mask[i] = delta >= threshold ? 1 : 0;
  }
  return mask;
}

async function writeBinary(name, mask) {
  const data = Buffer.alloc(TILE_W * TILE_H * 3);
  for (let i = 0; i < mask.length; i += 1) {
    const p = i * 3;
    const value = mask[i] ? 245 : 42;
    data[p] = value;
    data[p + 1] = value;
    data[p + 2] = value;
  }
  await sharp(data, { raw: { width: TILE_W, height: TILE_H, channels: 3 } })
    .png()
    .toFile(`${outDir}/${name}.png`);
}

async function writeErrors(name, gt, pred) {
  const data = Buffer.alloc(TILE_W * TILE_H * 3);
  for (let i = 0; i < gt.length; i += 1) {
    const p = i * 3;
    let color = [42, 47, 54];
    if (gt[i] && pred[i]) color = [40, 167, 69];
    else if (!gt[i] && pred[i]) color = [220, 53, 69];
    else if (gt[i] && !pred[i]) color = [47, 115, 184];
    data[p] = color[0];
    data[p + 1] = color[1];
    data[p + 2] = color[2];
  }
  await sharp(data, { raw: { width: TILE_W, height: TILE_H, channels: 3 } })
    .png()
    .toFile(`${outDir}/${name}.png`);
}

for (const [caseName, top] of Object.entries(Y)) {
  const rgb = (await rawPanel(X.rgb, top)).data;
  const gtOverlay = (await rawPanel(X.gt, top)).data;
  const controlledOverlay = (await rawPanel(X.controlled, top)).data;
  const iprOverlay = (await rawPanel(X.ipr, top)).data;
  const gt = changedMask(rgb, gtOverlay);
  const controlled = changedMask(rgb, controlledOverlay);
  const ipr = changedMask(rgb, iprOverlay);
  await writeBinary(`${caseName}-gt`, gt);
  await writeErrors(`${caseName}-controlled-errors`, gt, controlled);
  await writeErrors(`${caseName}-ipr-errors`, gt, ipr);
}

console.log(JSON.stringify({ outDir }, null, 2));

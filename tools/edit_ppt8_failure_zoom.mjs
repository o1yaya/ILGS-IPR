import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import sharp from "file:///C:/Users/hp/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs";
import {
  FileBlob,
  PresentationFile,
} from "file:///C:/Users/hp/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const source = "D:/wlxy/阅读报告及汇报/ILGS-IPR_研究汇报.pptx";
const sourceFigure = "D:/PycharmProjects/PythonProject/ILGS_release-main/tmp/ppt8-package-20261019-2/unzipped/ppt/media/image8.png";
const workspaceDir = "D:/PycharmProjects/PythonProject/ILGS_release-main";
const skillDir = "C:/Users/hp/.codex/plugins/cache/openai-primary-runtime/presentations/26.1015.12040/skills/presentations";
const runtimePython = "C:/Users/hp/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe";
const runtimeNodeModules = "C:/Users/hp/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules";
const finalPath = `${workspaceDir}/output/presentations/ILGS-IPR_研究汇报_第8页失败案例局部放大_20261019.pptx`;
const stagingDir = `${workspaceDir}/tmp/ppt8-failure-zoom-finalizer`;
const cropDir = `${stagingDir}/crops`;

const GREEN = "#0B7A53";
const BLUE = "#2F73B8";
const RED = "#C43D35";
const ORANGE = "#E67E22";
const DARK = "#263442";
const GREY = "#6B7785";
const LIGHT = "#D9E1E8";
const WHITE = "#FFFFFF";
const FONT = "微软雅黑";

process.env.RUNTIME_NODE_MODULES = runtimeNodeModules;
process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES = runtimeNodeModules;

function addRect(slide, name, position, fill, lineFill = fill, lineWidth = 1, radius = "rounded-sm") {
  return slide.shapes.add({
    name,
    geometry: radius ? "roundRect" : "rect",
    position,
    fill,
    line: { style: "solid", fill: lineFill, width: lineWidth },
    ...(radius ? { borderRadius: radius } : {}),
  });
}

function addText(slide, name, text, position, options = {}) {
  const shape = slide.shapes.add({
    name,
    geometry: "textbox",
    position,
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  shape.text = text;
  shape.text.style = {
    typeface: FONT,
    fontSize: options.fontSize ?? 14,
    bold: options.bold ?? false,
    color: options.color ?? DARK,
    alignment: options.alignment ?? "left",
    verticalAlignment: options.verticalAlignment ?? "middle",
    autoFit: "shrinkText",
    insets: options.insets ?? 1,
  };
  return shape;
}

function addOutline(slide, name, position, color, width = 3) {
  addRect(slide, name, position, "none", color, width, "rounded-sm");
}

function addTag(slide, name, text, position, color) {
  const tag = addRect(slide, name, position, color, color, 1, "rounded-sm");
  tag.text = text;
  tag.text.style = {
    typeface: FONT,
    fontSize: 15,
    bold: true,
    color: WHITE,
    alignment: "center",
    verticalAlignment: "middle",
    autoFit: "shrinkText",
    insets: 2,
  };
}

async function crop(name, region) {
  const out = `${cropDir}/${name}.png`;
  await sharp(sourceFigure)
    .extract(region)
    .resize(360, 360, { fit: "cover", position: "centre" })
    .png()
    .toFile(out);
  return out;
}

async function addImage(slide, imagePath, alt, position) {
  const bytes = await fs.readFile(imagePath);
  slide.images.add({
    blob: bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength),
    contentType: "image/png",
    alt,
    fit: "cover",
    position,
    geometry: "rect",
  });
}

await fs.mkdir(path.dirname(finalPath), { recursive: true });
await fs.mkdir(cropDir, { recursive: true });

const crops = {
  worstGt: await crop("covered-worst-gt", { left: 730, top: 560, width: 230, height: 215 }),
  worstControlled: await crop("covered-worst-controlled", { left: 1150, top: 560, width: 230, height: 215 }),
  worstIpr: await crop("covered-worst-ipr", { left: 1570, top: 560, width: 230, height: 215 }),
  gundamGt: await crop("gundam-gt", { left: 835, top: 900, width: 270, height: 230 }),
  gundamControlled: await crop("gundam-controlled", { left: 1260, top: 900, width: 270, height: 230 }),
  gundamIpr: await crop("gundam-ipr", { left: 1680, top: 900, width: 270, height: 230 }),
};

const presentation = await PresentationFile.importPptx(await FileBlob.load(source));
const slide = presentation.slides.items[7];
if (!slide) throw new Error("Slide 8 was not found");

// Success side: clearly identify the corrected IPR outputs.
addOutline(slide, "Success IPR column", { left: 497, top: 202, width: 125, height: 312 }, GREEN, 3.5);
addTag(slide, "Success tag", "✓  IPR恢复", { left: 506, top: 151, width: 110, height: 26 }, GREEN);
addOutline(slide, "Success target 1", { left: 527, top: 263, width: 34, height: 22 }, GREEN, 2.5);
addOutline(slide, "Success target 2", { left: 539, top: 364, width: 43, height: 28 }, GREEN, 2.5);
addOutline(slide, "Success target 3", { left: 581, top: 465, width: 37, height: 27 }, GREEN, 2.5);

// Failure side: replace the dense overview with source-derived local crops.
addRect(slide, "Failure comparison background", { left: 651, top: 183, width: 574, height: 359 }, WHITE, WHITE, 0, null);
addText(slide, "GT header", "参考掩码", { left: 758, top: 185, width: 110, height: 24 }, { bold: true, color: GREY, alignment: "center" });
addText(slide, "Controlled header", "受控 ILGS", { left: 885, top: 185, width: 110, height: 24 }, { bold: true, color: BLUE, alignment: "center" });
addText(slide, "IPR header", "IPR", { left: 1012, top: 185, width: 110, height: 24 }, { bold: true, color: RED, alignment: "center" });

const row1Y = 214;
const row2Y = 382;
const imageSize = 108;
const xGt = 759;
const xControlled = 886;
const xIpr = 1013;

addText(slide, "Worst case label", "Covered Desk\nGerbera\n最差视角", { left: 654, top: row1Y, width: 94, height: imageSize }, { bold: true, fontSize: 14, color: DARK, alignment: "center" });
await addImage(slide, crops.worstGt, "Ground-truth crop for Covered Desk gerbera worst view", { left: xGt, top: row1Y, width: imageSize, height: imageSize });
await addImage(slide, crops.worstControlled, "Controlled ILGS crop for Covered Desk gerbera worst view", { left: xControlled, top: row1Y, width: imageSize, height: imageSize });
await addImage(slide, crops.worstIpr, "IPR crop for Covered Desk gerbera worst view", { left: xIpr, top: row1Y, width: imageSize, height: imageSize });
addOutline(slide, "Worst GT border", { left: xGt - 1, top: row1Y - 1, width: imageSize + 2, height: imageSize + 2 }, GREY, 2);
addOutline(slide, "Worst controlled border", { left: xControlled - 1, top: row1Y - 1, width: imageSize + 2, height: imageSize + 2 }, BLUE, 3);
addOutline(slide, "Worst IPR border", { left: xIpr - 1, top: row1Y - 1, width: imageSize + 2, height: imageSize + 2 }, RED, 3);
addText(slide, "Worst GT metric", "Reference", { left: xGt, top: 324, width: imageSize, height: 22 }, { fontSize: 13, color: GREY, alignment: "center" });
addText(slide, "Worst controlled metric", "IoU 0.819", { left: xControlled, top: 324, width: imageSize, height: 22 }, { bold: true, fontSize: 14, color: BLUE, alignment: "center" });
addText(slide, "Worst IPR metric", "IoU 0.078", { left: xIpr, top: 324, width: imageSize, height: 22 }, { bold: true, fontSize: 14, color: RED, alignment: "center" });
const delta = addRect(slide, "Worst delta badge", { left: 1134, top: 239, width: 82, height: 62 }, "#FFF1EE", RED, 1.5, "rounded-sm");
delta.text = "ΔIoU\n−0.742";
delta.text.style = { typeface: FONT, fontSize: 15, bold: true, color: RED, alignment: "center", verticalAlignment: "middle", autoFit: "shrinkText", insets: 2 };

addRect(slide, "Failure row divider", { left: 654, top: 363, width: 562, height: 1 }, LIGHT, LIGHT, 0, null);

addText(slide, "Gundam case label", "Sofa\nGundam\n两者均失败", { left: 654, top: row2Y, width: 94, height: imageSize }, { bold: true, fontSize: 14, color: DARK, alignment: "center" });
await addImage(slide, crops.gundamGt, "Ground-truth crop for Sofa Gundam", { left: xGt, top: row2Y, width: imageSize, height: imageSize });
await addImage(slide, crops.gundamControlled, "Controlled ILGS crop for Sofa Gundam", { left: xControlled, top: row2Y, width: imageSize, height: imageSize });
await addImage(slide, crops.gundamIpr, "IPR crop for Sofa Gundam", { left: xIpr, top: row2Y, width: imageSize, height: imageSize });
addOutline(slide, "Gundam GT border", { left: xGt - 1, top: row2Y - 1, width: imageSize + 2, height: imageSize + 2 }, GREY, 2);
addOutline(slide, "Gundam controlled border", { left: xControlled - 1, top: row2Y - 1, width: imageSize + 2, height: imageSize + 2 }, BLUE, 3);
addOutline(slide, "Gundam IPR border", { left: xIpr - 1, top: row2Y - 1, width: imageSize + 2, height: imageSize + 2 }, RED, 3);
addText(slide, "Gundam GT metric", "Reference", { left: xGt, top: 492, width: imageSize, height: 22 }, { fontSize: 13, color: GREY, alignment: "center" });
addText(slide, "Gundam controlled metric", "IoU 0.038", { left: xControlled, top: 492, width: imageSize, height: 22 }, { bold: true, fontSize: 14, color: BLUE, alignment: "center" });
addText(slide, "Gundam IPR metric", "IoU 0.019", { left: xIpr, top: 492, width: imageSize, height: 22 }, { bold: true, fontSize: 14, color: RED, alignment: "center" });
const bothFail = addRect(slide, "Both fail badge", { left: 1134, top: 407, width: 82, height: 62 }, "#FFF1EE", RED, 1.5, "rounded-sm");
bothFail.text = "两者\n均失败";
bothFail.text.style = { typeface: FONT, fontSize: 15, bold: true, color: RED, alignment: "center", verticalAlignment: "middle", autoFit: "shrinkText", insets: 2 };
addText(slide, "Failure crop note", "同一目标局部放大；白色轮廓为 GT 边界", { left: 760, top: 518, width: 360, height: 19 }, { fontSize: 11, color: GREY, alignment: "center" });

const candidatePath = `${stagingDir}/candidate.pptx`;
await (await PresentationFile.exportPptx(presentation)).save(candidatePath);

const sourceBytes = await fs.readFile(source);
const referenceSha256 = crypto.createHash("sha256").update(sourceBytes).digest("hex");
const { finalizePresentation } = await import(pathToFileURL(
  path.join(skillDir, "container_tools/artifact_tool_utils.mjs"),
).href);

const result = await finalizePresentation({
  explicitTotalSlideCount: presentation.slides.items.length,
  requiredNativeTableOwnerSlides: [],
  requiredNativeChartOwnerSlides: [],
  workspaceDir,
  candidatePath,
  finalPath,
  pythonExecutable: runtimePython,
  integrityValidatorPath: path.join(skillDir, "container_tools/inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(skillDir, "container_tools/inspect_presentation_layout_geometry.py"),
  layoutArgs: [
    "--expected-slide-size-emu", "12192000,6858000",
    "--validate-bullet-geometry",
    "--validate-heading-fit",
  ],
  fontPolicy: {
    basis: "reference",
    families: ["微软雅黑", "等线", "Cambria Math"],
    referencePath: source,
    referenceSha256,
  },
  verifyArtifactToolImport: true,
  receiptPath: `${stagingDir}/validation.json`,
});

console.log(JSON.stringify({ finalPath, result }, null, 2));

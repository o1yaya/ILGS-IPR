import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import {
  FileBlob,
  PresentationFile,
} from "file:///C:/Users/hp/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const source = "D:/wlxy/阅读报告及汇报/ILGS-IPR_研究汇报.pptx";
const workspaceDir = "D:/PycharmProjects/PythonProject/ILGS_release-main";
const skillDir = "C:/Users/hp/.codex/plugins/cache/openai-primary-runtime/presentations/26.1015.12040/skills/presentations";
const runtimePython = "C:/Users/hp/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe";
const runtimeNodeModules = "C:/Users/hp/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules";
const maskDir = `${workspaceDir}/tmp/ppt8-derived-masks`;
const finalPath = `${workspaceDir}/output/presentations/ILGS-IPR_研究汇报_第8页误差图优化_20261019.pptx`;
const stagingDir = `${workspaceDir}/tmp/ppt8-error-map-finalizer`;

const GREEN = "#0B7A53";
const TP_GREEN = "#28A745";
const BLUE = "#2F73B8";
const RED = "#DC3545";
const DARK = "#263442";
const GREY = "#6B7785";
const LIGHT = "#D9E1E8";
const WHITE = "#FFFFFF";
const SOFT_RED = "#FFF1EE";
const FONT = "微软雅黑";

process.env.RUNTIME_NODE_MODULES = runtimeNodeModules;
process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES = runtimeNodeModules;

function addRect(slide, name, position, fill, lineFill = fill, lineWidth = 1, rounded = true) {
  return slide.shapes.add({
    name,
    geometry: rounded ? "roundRect" : "rect",
    position,
    fill,
    line: { style: "solid", fill: lineFill, width: lineWidth },
    ...(rounded ? { borderRadius: "rounded-sm" } : {}),
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
  addRect(slide, name, position, "none", color, width, true);
}

function addTag(slide, name, text, position, color) {
  const tag = addRect(slide, name, position, color, color, 1, true);
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

async function addImage(slide, imagePath, alt, position) {
  const bytes = await fs.readFile(imagePath);
  slide.images.add({
    blob: bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength),
    contentType: "image/png",
    alt,
    fit: "contain",
    position,
    geometry: "rect",
  });
}

function addLegendItem(slide, name, x, color, label) {
  addRect(slide, `${name} swatch`, { left: x, top: 512, width: 12, height: 12 }, color, color, 0, false);
  addText(slide, `${name} label`, label, { left: x + 16, top: 506, width: 82, height: 24 }, {
    fontSize: 11,
    color: GREY,
  });
}

await fs.mkdir(path.dirname(finalPath), { recursive: true });
await fs.mkdir(stagingDir, { recursive: true });

const presentation = await PresentationFile.importPptx(await FileBlob.load(source));
const slide = presentation.slides.items[7];
if (!slide) throw new Error("Slide 8 was not found");

// Success side: identify the IPR column and the recovered targets.
addOutline(slide, "Success IPR column", { left: 497, top: 202, width: 125, height: 312 }, GREEN, 3.5);
addTag(slide, "Success tag", "✓  IPR恢复", { left: 506, top: 151, width: 110, height: 26 }, GREEN);
addOutline(slide, "Success target 1", { left: 527, top: 263, width: 34, height: 22 }, GREEN, 2.5);
addOutline(slide, "Success target 2", { left: 539, top: 364, width: 43, height: 28 }, GREEN, 2.5);
addOutline(slide, "Success target 3", { left: 581, top: 465, width: 37, height: 27 }, GREEN, 2.5);

// Failure side: replace RGB overlays with real mask error maps.
addRect(slide, "Failure comparison background", { left: 651, top: 183, width: 574, height: 359 }, WHITE, WHITE, 0, false);

const xLabel = 654;
const xGt = 754;
const xControlled = 879;
const xIpr = 1004;
const xBadge = 1132;
const imageWidth = 112;
const imageHeight = 84;
const row1Y = 220;
const row2Y = 390;

addText(slide, "GT header", "参考掩码", { left: xGt, top: 184, width: imageWidth, height: 28 }, {
  bold: true,
  color: GREY,
  alignment: "center",
});
addText(slide, "Controlled header", "受控 ILGS", { left: xControlled, top: 184, width: imageWidth, height: 28 }, {
  bold: true,
  color: BLUE,
  alignment: "center",
});
addText(slide, "IPR header", "IPR", { left: xIpr, top: 184, width: imageWidth, height: 28 }, {
  bold: true,
  color: RED,
  alignment: "center",
});

addText(slide, "Worst case label", "Covered Desk\nGerbera\n最差视角", { left: xLabel, top: row1Y, width: 92, height: imageHeight }, {
  bold: true,
  fontSize: 13,
  alignment: "center",
});
await addImage(slide, `${maskDir}/worst-gt.png`, "Ground-truth mask for the Covered Desk Gerbera worst view", { left: xGt, top: row1Y, width: imageWidth, height: imageHeight });
await addImage(slide, `${maskDir}/worst-controlled-errors.png`, "Controlled ILGS error map for the Covered Desk Gerbera worst view", { left: xControlled, top: row1Y, width: imageWidth, height: imageHeight });
await addImage(slide, `${maskDir}/worst-ipr-errors.png`, "IPR error map for the Covered Desk Gerbera worst view", { left: xIpr, top: row1Y, width: imageWidth, height: imageHeight });
addOutline(slide, "Worst GT border", { left: xGt - 1, top: row1Y - 1, width: imageWidth + 2, height: imageHeight + 2 }, GREY, 2);
addOutline(slide, "Worst controlled border", { left: xControlled - 1, top: row1Y - 1, width: imageWidth + 2, height: imageHeight + 2 }, BLUE, 2.5);
addOutline(slide, "Worst IPR border", { left: xIpr - 1, top: row1Y - 1, width: imageWidth + 2, height: imageHeight + 2 }, RED, 2.5);
addText(slide, "Worst GT metric", "Reference", { left: xGt, top: 306, width: imageWidth, height: 22 }, { fontSize: 12, color: GREY, alignment: "center" });
addText(slide, "Worst controlled metric", "IoU 0.819", { left: xControlled, top: 306, width: imageWidth, height: 22 }, { bold: true, fontSize: 13, color: BLUE, alignment: "center" });
addText(slide, "Worst IPR metric", "IoU 0.078", { left: xIpr, top: 306, width: imageWidth, height: 22 }, { bold: true, fontSize: 13, color: RED, alignment: "center" });
const delta = addRect(slide, "Worst delta badge", { left: xBadge, top: 229, width: 82, height: 62 }, SOFT_RED, RED, 1.5, true);
delta.text = "ΔIoU\n−0.742";
delta.text.style = { typeface: FONT, fontSize: 15, bold: true, color: RED, alignment: "center", verticalAlignment: "middle", autoFit: "shrinkText", insets: 2 };
addText(slide, "Worst difference note", "IPR 漏选明显", { left: xBadge, top: 294, width: 82, height: 28 }, { bold: true, fontSize: 11, color: RED, alignment: "center" });

addRect(slide, "Failure row divider", { left: 654, top: 361, width: 560, height: 1 }, LIGHT, LIGHT, 0, false);

addText(slide, "Gundam case label", "Sofa\nGundam\n两者均失败", { left: xLabel, top: row2Y, width: 92, height: imageHeight }, {
  bold: true,
  fontSize: 13,
  alignment: "center",
});
await addImage(slide, `${maskDir}/gundam-gt.png`, "Ground-truth mask for the Sofa Gundam case", { left: xGt, top: row2Y, width: imageWidth, height: imageHeight });
await addImage(slide, `${maskDir}/gundam-controlled-errors.png`, "Controlled ILGS error map for the Sofa Gundam case", { left: xControlled, top: row2Y, width: imageWidth, height: imageHeight });
await addImage(slide, `${maskDir}/gundam-ipr-errors.png`, "IPR error map for the Sofa Gundam case", { left: xIpr, top: row2Y, width: imageWidth, height: imageHeight });
addOutline(slide, "Gundam GT border", { left: xGt - 1, top: row2Y - 1, width: imageWidth + 2, height: imageHeight + 2 }, GREY, 2);
addOutline(slide, "Gundam controlled border", { left: xControlled - 1, top: row2Y - 1, width: imageWidth + 2, height: imageHeight + 2 }, BLUE, 2.5);
addOutline(slide, "Gundam IPR border", { left: xIpr - 1, top: row2Y - 1, width: imageWidth + 2, height: imageHeight + 2 }, RED, 2.5);
addText(slide, "Gundam GT metric", "Reference", { left: xGt, top: 476, width: imageWidth, height: 22 }, { fontSize: 12, color: GREY, alignment: "center" });
addText(slide, "Gundam controlled metric", "IoU 0.038", { left: xControlled, top: 476, width: imageWidth, height: 22 }, { bold: true, fontSize: 13, color: BLUE, alignment: "center" });
addText(slide, "Gundam IPR metric", "IoU 0.019", { left: xIpr, top: 476, width: imageWidth, height: 22 }, { bold: true, fontSize: 13, color: RED, alignment: "center" });
const bothFail = addRect(slide, "Both fail badge", { left: xBadge, top: 399, width: 82, height: 62 }, SOFT_RED, RED, 1.5, true);
bothFail.text = "两者\n均失败";
bothFail.text.style = { typeface: FONT, fontSize: 15, bold: true, color: RED, alignment: "center", verticalAlignment: "middle", autoFit: "shrinkText", insets: 2 };
addText(slide, "Both fail note", "结果接近", { left: xBadge, top: 464, width: 82, height: 28 }, { bold: true, fontSize: 11, color: GREY, alignment: "center" });

addLegendItem(slide, "True positive", 777, TP_GREEN, "正确区域");
addLegendItem(slide, "False positive", 880, RED, "误选区域");
addLegendItem(slide, "False negative", 983, BLUE, "漏选区域");

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

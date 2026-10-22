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
const finalPath = `${workspaceDir}/output/presentations/ILGS-IPR_研究汇报_第8页高光优化_v2_20261019.pptx`;
const stagingDir = `${workspaceDir}/tmp/ppt8-highlight-finalizer`;

const GREEN = "#0B7A53";
const RED = "#C43D35";
const WHITE = "#FFFFFF";
const FONT = "微软雅黑";

process.env.RUNTIME_NODE_MODULES = runtimeNodeModules;
process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES = runtimeNodeModules;

function addOutline(slide, name, position, color, width = 3) {
  slide.shapes.add({
    name,
    geometry: "roundRect",
    position,
    fill: "none",
    line: { style: "solid", fill: color, width },
    borderRadius: "rounded-sm",
  });
}

function addTag(slide, name, text, position, color) {
  const tag = slide.shapes.add({
    name,
    geometry: "roundRect",
    position,
    fill: color,
    line: { style: "solid", fill: color, width: 1 },
    borderRadius: "rounded-sm",
  });
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

await fs.mkdir(path.dirname(finalPath), { recursive: true });
await fs.mkdir(stagingDir, { recursive: true });

const presentation = await PresentationFile.importPptx(await FileBlob.load(source));
const slide = presentation.slides.items[7];
if (!slide) throw new Error("Slide 8 was not found");

// Emphasize the output column while leaving the underlying scientific images unchanged.
addOutline(slide, "Success IPR column", { left: 497, top: 202, width: 125, height: 312 }, GREEN, 3.5);
addTag(slide, "Success tag", "✓  IPR恢复", { left: 506, top: 151, width: 110, height: 26 }, GREEN);

addOutline(slide, "Success target 1", { left: 527, top: 263, width: 34, height: 22 }, GREEN, 2.5);
addOutline(slide, "Success target 2", { left: 539, top: 364, width: 43, height: 28 }, GREEN, 2.5);
addOutline(slide, "Success target 3", { left: 581, top: 465, width: 37, height: 27 }, GREEN, 2.5);

addOutline(slide, "Failure IPR column", { left: 1081, top: 202, width: 124, height: 312 }, RED, 3.5);
addTag(slide, "Failure tag", "×  仍有错误", { left: 1090, top: 151, width: 116, height: 26 }, RED);

addOutline(slide, "Failure target 1", { left: 1104, top: 258, width: 43, height: 35 }, RED, 2.5);
addOutline(slide, "Failure target 2", { left: 1104, top: 362, width: 48, height: 39 }, RED, 2.5);
addOutline(slide, "Failure target 3", { left: 1140, top: 456, width: 62, height: 44 }, RED, 2.5);

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
  receiptPath: `${stagingDir}/validation-v2.json`,
});

console.log(JSON.stringify({ finalPath, result }, null, 2));

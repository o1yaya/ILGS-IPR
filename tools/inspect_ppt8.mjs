import fs from "node:fs/promises";
import {
  FileBlob,
  PresentationFile,
} from "file:///C:/Users/hp/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const source = process.argv[2] ?? "D:/wlxy/阅读报告及汇报/ILGS-IPR_研究汇报.pptx";
const outDir = process.argv[3] ?? "D:/PycharmProjects/PythonProject/ILGS_release-main/tmp/ppt8-inspect";

await fs.mkdir(outDir, { recursive: true });
const presentation = await PresentationFile.importPptx(await FileBlob.load(source));
const slide = presentation.slides.items[7];
if (!slide) throw new Error("Slide 8 was not found");

const png = await presentation.export({ slide, format: "png", scale: 2 });
await fs.writeFile(`${outDir}/slide-08-before.png`, new Uint8Array(await png.arrayBuffer()));

const elements = slide.elements.items.map((element, index) => ({
  index,
  id: element.id,
  type: element.type,
  name: element.name,
  position: element.position,
  text: element.type === "shape" ? element.text?.toString?.() : undefined,
  referenceId: element.type === "image" ? element.referenceId : undefined,
}));
await fs.writeFile(
  `${outDir}/slide-08-elements.json`,
  JSON.stringify(elements, null, 2),
  "utf8",
);
console.log(JSON.stringify({
  slides: presentation.slides.items.length,
  slideId: slide.id,
  preview: `${outDir}/slide-08-before.png`,
  elements: `${outDir}/slide-08-elements.json`,
}, null, 2));

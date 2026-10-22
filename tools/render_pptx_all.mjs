import fs from "node:fs/promises";
import {
  FileBlob,
  PresentationFile,
} from "file:///C:/Users/hp/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const source = process.argv[2];
const outDir = process.argv[3];
if (!source || !outDir) throw new Error("Usage: render_pptx_all.mjs <pptx> <output-dir>");

await fs.mkdir(outDir, { recursive: true });
const presentation = await PresentationFile.importPptx(await FileBlob.load(source));
for (const [index, slide] of presentation.slides.items.entries()) {
  const png = await presentation.export({ slide, format: "png", scale: 1.5 });
  const name = `slide-${String(index + 1).padStart(2, "0")}.png`;
  await fs.writeFile(`${outDir}/${name}`, new Uint8Array(await png.arrayBuffer()));
}
const montage = await presentation.export({ format: "webp", montage: true });
await fs.writeFile(`${outDir}/montage.webp`, new Uint8Array(await montage.arrayBuffer()));
console.log(JSON.stringify({ slides: presentation.slides.items.length, outDir }, null, 2));

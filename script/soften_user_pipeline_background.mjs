import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';

const require = createRequire(import.meta.url);
const xml = require('C:/Users/hp/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/xml-js');
const dir = path.resolve('outputs/pipeline_masks_20261010');
const source = path.join(dir, 'ILGS_IPR_pipeline_academic_optimized.svg');
const name = 'ILGS_IPR_pipeline_soft_background';
const target = path.join(dir, `${name}.svg`);
const original = await fs.readFile(source, 'utf8');
const doc = xml.xml2js(original, { compact: false });
const hash = data => crypto.createHash('sha256').update(data).digest('hex');
function visit(node, fn) {
  fn(node);
  for (const child of node.elements || []) visit(child, fn);
}
function protectedContent(root) {
  const values = [];
  visit(root, n => {
    if (n.attributes?.id === 'background') return;
    if (['text','image','path','polygon','polyline'].includes(n.name) && !['polyline3','polyline4'].includes(n.attributes?.id)) values.push(n);
  });
  return hash(JSON.stringify(values));
}
const before = protectedContent(doc);
let background;
visit(doc, n => { if (n.attributes?.id === 'background') background = n; });
if (!background) throw new Error('Background layer not found');
const rectangle = (id,x,y,width,height,fill,rx=7) => ({type:'element',name:'rect',attributes:{id,x:String(x),y:String(y),width:String(width),height:String(height),rx:String(rx),fill,stroke:'none'}});
background.elements = [
  rectangle('page-background',0,0,1440,670,'#ffffff',0),
  rectangle('input-background',8,16,212,638,'#f0f4f8'),
  rectangle('ipr-background',228,16,442,638,'#fff6e9'),
  rectangle('gaussian-background',690,16,244,638,'#f3f1f8'),
  rectangle('optimization-background',954,16,478,638,'#eef6f1'),
];
background.attributes['inkscape:label'] = '01 Soft backgrounds - no borders';
let removedBorders = 0;
visit(doc, n => {
  if (n.name !== 'rect') return;
  const a = n.attributes;
  if (a.stroke && a.stroke !== 'none') removedBorders++;
  a.stroke = 'none';
  a['stroke-width'] = '0';
  if (a.style) a.style = a.style.replace(/(^|;)\s*stroke\s*:[^;]*/g, '$1stroke:none');
  if (a.id === 'rect10') a.fill = '#ffecd1';
  if (a.id === 'rect22') a.fill = '#fff2f1';
  if (['rect25','rect28'].includes(a.id)) a.fill = '#ffffff';
});
const after = protectedContent(doc);
if (before !== after) throw new Error('User content changed outside the background/border scope');
visit(doc, n => {
  if (n.name === 'svg') n.attributes['sodipodi:docname'] = `${name}.svg`;
});
await fs.writeFile(target, xml.js2xml(doc, { compact:false, spaces:2 }), 'utf8');
const inkscape = 'E:/Inkscape/bin/inkscape.com';
execFileSync(inkscape,[target,'--export-type=png',`--export-filename=${path.join(dir,`${name}.png`)}`,'--export-dpi=300'],{stdio:'inherit'});
execFileSync(inkscape,[target,'--export-type=pdf',`--export-filename=${path.join(dir,`${name}.pdf`)}`],{stdio:'inherit'});
if (original !== await fs.readFile(source,'utf8')) throw new Error('Original user file changed');
const audit = {source,target,sourceSha256:hash(original),protectedContentUnchanged:before===after,removedBorders,backgrounds:['#f0f4f8','#fff6e9','#f3f1f8','#eef6f1'],note:'User text, image attributes, positions, transforms and signal connections are preserved. Source SVG is not overwritten.'};
await fs.writeFile(path.join(dir,`${name}_checks.json`),JSON.stringify(audit,null,2));
console.log(JSON.stringify(audit,null,2));

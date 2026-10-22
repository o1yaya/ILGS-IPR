// Academic Figure Skill Asset Confirmation (verified against assets/figures/)
// Existing method schematic -> no matching quantitative template -> native SVG adaptation.
// All 12 embedded source images are preserved byte-for-byte and fitted without cropping.
// Physical typography, semantic colors, vector masters and render QA follow the skill.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';

const require=createRequire(import.meta.url);
const deps='C:/Users/hp/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const xml=require(`${deps}/xml-js`), sharp=require(`${deps}/sharp`);
const dir='D:/wlxy/ilgs/文章图';
const source=path.join(dir,'method.svg');
const output=path.join(dir,'method_optimized');
const original=await fs.readFile(source,'utf8');
const digest=data=>crypto.createHash('sha256').update(data).digest('hex');
const sourceHash=digest(original);
const assets=new Map();
function walk(n) {
  if(n.name==='image') assets.set(n.attributes.id,n.attributes.href||n.attributes['xlink:href']);
  for(const c of n.elements||[]) walk(c);
}
walk(xml.xml2js(original,{compact:false}));
if(assets.size!==12) throw new Error(`Expected 12 embedded image tiles, found ${assets.size}`);

const W=1440,H=988,widthMM=183,heightMM=H/W*widthMM;
const pointScale=widthMM/25.4*72/W;
const C={ink:'#222222',muted:'#58636a',orange:'#b35806',orangeLine:'#dc8422',blue:'#2166ac',teal:'#087865',red:'#b2182b'};
const layers=[],texts=[],images=[],segments=[];
let parts=[],counter=0;
const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
function begin(id,label) { parts=[`<g id="${id}" inkscape:groupmode="layer" inkscape:label="${esc(label)}">`]; }
function end() { parts.push('</g>'); layers.push(parts.join('\n')); }
function rect(x,y,w,h,fill,rx=6,opacity=1) {
  parts.push(`<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${rx}" fill="${fill}" fill-opacity="${opacity}" stroke="none"/>`);
}
function text(value,x,y,{size=18,weight=400,anchor='middle',color=C.ink,family='Arial, Helvetica, Liberation Sans, sans-serif',italic=false,math=false,annotation=false}={}) {
  const id=`label-${++counter}`;
  parts.push(`<text id="${id}" x="${x}" y="${y}" font-family="${family}" font-size="${size}" font-weight="${weight}" text-anchor="${anchor}" fill="${color}" letter-spacing="0"${italic?' font-style="italic"':''}>${esc(value)}</text>`);
  texts.push({id,value,size,pt:size*pointScale,math,annotation});
}
function line(points,color=C.ink,sw=1.6) {
  parts.push(`<polyline points="${points.map(p=>p.join(',')).join(' ')}" fill="none" stroke="${color}" stroke-width="${sw}" stroke-linejoin="round"/>`);
  for(let i=1;i<points.length;i++) segments.push([points[i-1],points[i],sw]);
}
function arrow(points,color=C.ink,size=10,sw=1.6) {
  const [x,y]=points.at(-1),[px,py]=points.at(-2),a=Math.atan2(y-py,x-px);
  const bx=x-size*Math.cos(a),by=y-size*Math.sin(a),dx=-Math.sin(a)*size*.44,dy=Math.cos(a)*size*.44;
  line([...points.slice(0,-1),[bx,by]],color,sw);
  parts.push(`<polygon points="${x},${y} ${bx+dx},${by+dy} ${bx-dx},${by-dy}" fill="${color}"/>`);
}
async function image(id,x,y,w,h) {
  const href=assets.get(id);
  if(!href?.startsWith('data:image/')) throw new Error(`Missing embedded asset: ${id}`);
  const bytes=Buffer.from(href.slice(href.indexOf(',')+1),'base64');
  const info=await sharp(bytes).metadata();
  const scale=Math.min(w/info.width,h/info.height);
  const width=info.width*scale,height=info.height*scale,ix=x+(w-width)/2,iy=y+(h-height)/2;
  parts.push(`<image id="${id}" x="${ix}" y="${iy}" width="${width}" height="${height}" preserveAspectRatio="xMidYMid meet" xlink:href="${href}"/>`);
  images.push({id,x:ix,y:iy,width,height,pixels:[info.width,info.height],effectiveDpi:Math.round(info.width/(width/W*widthMM/25.4)),sha256:digest(bytes)});
}
function heading(letter,title,x,y) {
  text(letter,x,y,{size:26,weight:700,anchor:'start'});
  text(title,x+29,y,{size:22,weight:700,anchor:'start'});
}

begin('backgrounds','01 Soft backgrounds');
rect(0,0,W,H,'#ffffff',0);
rect(16,16,1408,346,'#f0f5f8',8);
rect(16,386,320,586,'#f1f4f8',8);
rect(360,386,686,586,'#fff6e9',8);
rect(1070,386,354,586,'#eef6f1',8);
end();

begin('field','02 Confidence-weighted field and feature maps');
heading('c','Confidence-weighted ILGS: identity-aware 3D Gaussian field',36,49);
const top=[['novel-view-image',40,'Novel view'],['language-feature-image',393,'Language feature'],['identity-feature-image',746,'Identity feature'],['segment-similarity-image',1099,'Segment similarity']];
for(const [id,x,label] of top) {
  text(label,x+150,83,{weight:700});
  await image(id,x,98,300,225);
}
text('Text query: "Portuguese egg tart"',897,348,{size:19,weight:700});
end();

begin('input','03 Noisy identity supervision');
heading('a','Noisy identity labels',32,420);
await image('stage1-rgb-image',36,458,280,210);
rect(44,466,49,25,'#293238',3,.9);
text('RGB',68.5,485,{size:17,weight:700,color:'#ffffff',annotation:true});
await image('stage1-noisy-map',36,698,280,210);
rect(46,708,115,25,'#ffffff',3,.94);
text('Wall · ID 6',103.5,726,{size:17,weight:700,color:C.orange,annotation:true});
arrow([[104,735],[77,753]],C.orangeLine,8);
rect(184,877,120,25,'#ffffff',3,.94);
text('Floor · ID 4',244,895,{size:17,weight:700,color:C.orange,annotation:true});
arrow([[289,875],[305,851]],C.orangeLine,8);
text('Background IDs occupy 85.6%',176,938,{size:17,weight:700,color:C.muted});
end();

begin('ipr','04 IPR detail and pixel-wise weighting');
heading('b','IPR: estimate pixel reliability',376,420);
const methods=[['cleanup-image',380,'Structure cleanup'],['semantic-image',604,'Semantic evidence'],['area-image',828,'Area prior']];
for(const [id,x,label] of methods) {
  text(label,x+99,453,{weight:700});
  await image(id,id==='semantic-image'?587:x,477,id==='semantic-image'?232:198,148.5);
}
await image('reliability-map-image',478,696,246,184.5);
text('Reliability map W(p)',601,906,{size:19,weight:700});
rect(764,742,262,86,'#ffedd6',6);
text('Pixel-wise weighting',895,724,{size:18,weight:700,color:C.orange});
// Explicit baselines stack the subscript and superscript without Unicode approximations.
const mo={size:24,anchor:'start',family:'Cambria, Times New Roman, serif',italic:true,math:true};
text('L',790,795,mo);
text('id',803,803,{...mo,size:17,italic:false});
text('IPR',803,778,{...mo,size:17,italic:false});
text('(p) = W(p)L',836,795,mo);
text('id',955,803,{...mo,size:17,italic:false});
text('(p)',973,795,mo);
text('Preserve identity anchors; suppress unreliable pixels',703,941,{size:17,color:C.muted});
end();

begin('output','05 Qualitative segmentation example');
heading('d','Cleaner segment',1086,420);
text('Official ILGS: noisy mask',1247,448,{size:18,weight:700,color:C.red});
await image('official-image',1090,462,314,196);
text('+ IPR: target mask',1247,689,{size:18,weight:700,color:C.teal});
await image('ipr-image',1090,705,314,196);
text('+5.06 mIoU / +5.53 mBIoU',1247,934,{size:19,weight:700,color:C.blue});
text('3D-OVS · 10 scenes · 3 seeds',1247,960,{size:17,color:C.muted});
end();

begin('connections','06 Editable method connections');
line([[317,566],[346,566],[346,803],[317,803]],C.ink);
arrow([[346,566],[377,566]],C.ink);
line([[479,628],[479,654],[927,654],[927,628]],C.orangeLine);
arrow([[703,628],[703,674],[601,674],[601,693]],C.orangeLine);
arrow([[726,788],[760,788]],C.blue);
// Reliability changes training supervision, not the test-time query operation.
arrow([[1027,785],[1058,785],[1058,374],[703,374],[703,364]],C.blue,9);
arrow([[1247,364],[1247,383]],C.ink,9);
end();

const svg=`<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" width="${widthMM}mm" height="${heightMM}mm" viewBox="0 0 ${W} ${H}">
<title>ILGS-IPR method: pixel reliability and segmentation</title>
<desc>Visual refinement of the user's method.svg. All twelve embedded images are preserved without cropping or stretching. Pixel-wise weighting is schematic; it is not the complete normalized training objective. The displayed +5.06 mIoU and +5.53 mBIoU refer to the supplied three-seed ten-scene 3D-OVS aggregate, not the illustrated query or frame. Labels and quantitative values are retained from the supplied figure and results.</desc>
${layers.join('\n')}
</svg>`;
await fs.writeFile(`${output}.svg`,svg,'utf8');
const inkscape='E:/Inkscape/bin/inkscape.com';
execFileSync(inkscape,[`${output}.svg`,'--export-type=png',`--export-filename=${output}.png`,'--export-dpi=300'],{stdio:'inherit'});
execFileSync(inkscape,[`${output}.svg`,'--export-type=pdf',`--export-filename=${output}.pdf`],{stdio:'inherit'});
const response=execFileSync(inkscape,[`${output}.svg`,'--query-all'],{encoding:'utf8'});
const factor=W/(widthMM/25.4*96);
const bounds=new Map(response.trim().split(/\r?\n/).map(row=>{const [id,...v]=row.split(',');return [id,v.map(Number).map(n=>n*factor)];}));
const intersects=(a,b,pad=.6)=>a[0]+a[2]>b[0]+pad && b[0]+b[2]>a[0]+pad && a[1]+a[3]>b[1]+pad && b[1]+b[3]>a[1]+pad;
for(const t of texts)t.bounds=bounds.get(t.id);
const overlaps={text:[],image:[],line:[],outside:[]};
for(let i=0;i<texts.length;i++) {
  const t=texts[i],b=t.bounds;
  if(!b||b[0]<0||b[1]<0||b[0]+b[2]>W||b[1]+b[3]>H)overlaps.outside.push(t.value);
  for(let j=i+1;j<texts.length;j++)if(b&&texts[j].bounds&&intersects(b,texts[j].bounds))overlaps.text.push([t.value,texts[j].value]);
  if(!t.annotation) for(const im of images)if(b&&intersects(b,[im.x,im.y,im.width,im.height]))overlaps.image.push([t.value,im.id]);
  for(const [p,q,sw]of segments)if(b&&intersects(b,[Math.min(p[0],q[0])-sw/2,Math.min(p[1],q[1])-sw/2,Math.abs(p[0]-q[0])+sw,Math.abs(p[1]-q[1])+sw]))overlaps.line.push(t.value);
}
const sourceUnchanged=sourceHash===digest(await fs.readFile(source));
if(!sourceUnchanged)throw new Error('Source method.svg changed unexpectedly');
const pdf=await fs.readFile(`${output}.pdf`);
const audit={source,sourceHash,sourceUnchanged,widthMM,heightMM,minimumFontPt:Math.min(...texts.map(t=>t.pt)),images,texts,overlaps,pdfHasEmbeddedFonts:/\/FontFile[23]?\b/.test(pdf.toString('latin1'))};
await fs.writeFile(`${output}_checks.json`,JSON.stringify(audit,null,2));
console.log(JSON.stringify({svg:`${output}.svg`,imageCount:images.length,minDpi:Math.min(...images.map(i=>i.effectiveDpi)),minFontPt:audit.minimumFontPt,overlaps,sourceUnchanged,pdfHasEmbeddedFonts:audit.pdfHasEmbeddedFonts},null,2));

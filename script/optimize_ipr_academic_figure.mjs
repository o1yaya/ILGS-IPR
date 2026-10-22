// Academic Figure Skill Asset Confirmation (verified against assets/figures/)
// (a-d) Existing schematic -> no matching production plot -> native SVG adaptation.
// Existing embedded raster panels are reused byte-for-byte; no data are synthesized.
// Cosmetic refinement follows Steps 4-6. Matplotlib/R baselines are not executed
// in this native-SVG backend; their physical typography/export rules are applied below.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';

const require = createRequire(import.meta.url);
const dependencies = 'C:/Users/hp/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const xml = require(`${dependencies}/xml-js`);
const sharp = require(`${dependencies}/sharp`);
const dir = path.resolve('outputs/pipeline_masks_20261010');
const source = path.join(dir, 'ILGS_IPR_pipeline_journal_editable.svg');
const basename = path.join(dir, 'ILGS_IPR_pipeline_academic_optimized');
const inkscape = 'E:/Inkscape/bin/inkscape.com';
const sourceText = await fs.readFile(source, 'utf8');
const sourceHash = crypto.createHash('sha256').update(sourceText).digest('hex');
const parsed = xml.xml2js(sourceText, { compact: false });
const assets = new Map();
function walk(n) {
  if (n.name === 'image') {
    const a = n.attributes;
    assets.set(a.id, a['xlink:href'] || a.href);
  }
  for (const child of n.elements || []) walk(child);
}
walk(parsed);
if (assets.size !== 16) throw new Error(`Expected 16 image tiles; found ${assets.size}`);

// Academic Figure Skill palette; colors label signals, not experimental outcomes.
const CATEGORICAL = ['#2166AC', '#B2182B', '#1B7837', '#F1A340', '#762A83', '#666666'];
const CATEGORICAL_EXTENDED = [...CATEGORICAL, '#4393C3', '#D6604D', '#5AAE61', '#B35806', '#9970AB', '#999999'];
const DIVERGING = ['#2166AC', '#F7F7F7', '#B2182B'];
const SEQUENTIAL = ['#F7FBFF', '#6BAED6', '#08306B'];
const ACCENT_RED = '#B2182B', GREY = '#999999', BLACK = '#222222';
const C = { ink: BLACK, muted: '#555f65', rule: '#d4dadd', orange: '#b35806', orangeLine: '#dc8422', blue: CATEGORICAL[0], red: ACCENT_RED };
const W = 1440, H = 670, widthMM = 183, heightMM = H / W * widthMM;
const ptPerUnit = widthMM / 25.4 * 72 / W;
const font = { panel: 22, letter: 26, body: 18, small: 17, signal: 21 };
const layerStrings = [], auditText = [], auditImages = [], auditSegments = [];
let parts = [], idCounter = 0, currentPanel = '';
const esc = s => String(s).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
const unique = prefix => `${prefix}-${++idCounter}`;
function begin(id,label,panel = '') {
  currentPanel = panel;
  parts = [`<g id="${id}" inkscape:groupmode="layer" inkscape:label="${esc(label)}">`];
}
function end() { parts.push('</g>'); layerStrings.push(parts.join('\n')); }
function rect(x,y,w,h,fill,stroke='none',sw=1,rx=0) {
  parts.push(`<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${rx}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"/>`);
}
function text(value,x,y,{size=font.body,weight=400,anchor='middle',color=C.ink,allowed=null,rotation=0}={}) {
  const id = unique('text');
  parts.push(`<text id="${id}" x="${x}" y="${y}"${rotation ? ` transform="rotate(${rotation} ${x} ${y})"` : ''} font-family="Arial, Helvetica, Liberation Sans, sans-serif" font-size="${size}" font-weight="${weight}" text-anchor="${anchor}" letter-spacing="0" fill="${color}">${esc(value)}</text>`);
  auditText.push({id,value,x,y,size,pt:size*ptPerUnit,panel:currentPanel,allowed});
}
function lines(values,x,y,options={}) {
  values.forEach((s,i)=>text(s,x,y+i*22,options));
}
function poly(points,color=C.ink,sw=1.6,dash=null) {
  parts.push(`<polyline points="${points.map(p=>p.join(',')).join(' ')}" fill="none" stroke="${color}" stroke-width="${sw}" stroke-linejoin="round"${dash ? ` stroke-dasharray="${dash}"` : ''}/>`);
  for (let i=1;i<points.length;i++) auditSegments.push([points[i-1],points[i],sw]);
}
function arrow(points,color=C.ink,sw=1.6,size=10) {
  const [x,y]=points.at(-1), [px,py]=points.at(-2), a=Math.atan2(y-py,x-px);
  const bx=x-size*Math.cos(a), by=y-size*Math.sin(a), rx=-Math.sin(a)*size*.43, ry=Math.cos(a)*size*.43;
  poly([...points.slice(0,-1),[bx,by]],color,sw);
  parts.push(`<polygon points="${x},${y} ${bx+rx},${by+ry} ${bx-rx},${by-ry}" fill="${color}"/>`);
}
async function image(id,x,y,w,h) {
  const href = assets.get(`${id}-image`);
  if (!href?.startsWith('data:image/')) throw new Error(`Missing embedded image ${id}`);
  const bytes=Buffer.from(href.slice(href.indexOf(',')+1),'base64');
  const info=await sharp(bytes).metadata();
  const scale=Math.min(w/info.width,h/info.height);
  const iw=info.width*scale, ih=info.height*scale, ix=x+(w-iw)/2, iy=y+(h-ih)/2;
  parts.push(`<g id="${id}" inkscape:label="${esc(id)}"><image id="${id}-image" x="${ix}" y="${iy}" width="${iw}" height="${ih}" preserveAspectRatio="xMidYMid meet" xlink:href="${href}"/><rect x="${ix}" y="${iy}" width="${iw}" height="${ih}" fill="none" stroke="#cbd3d6" stroke-width="0.8"/></g>`);
  const dpi=info.width/(iw/W*widthMM/25.4);
  auditImages.push({id,x:ix,y:iy,width:iw,height:ih,pixels:[info.width,info.height],effectiveDpi:Math.round(dpi),sha256:crypto.createHash('sha256').update(bytes).digest('hex')});
}

begin('background','01 Background and restrained hierarchy');
rect(0,0,W,H,'#ffffff');
rect(228,16,442,622,'#fffaf2','none',0,5);
rect(228,16,442,3,C.orangeLine);
for(const x of [217,680]) poly([[x,78],[x,626]],C.rule,1);
end();

begin('titles','02 Editable panel titles');
for(const [letter,title,x] of [['a','Input supervision',16],['b','IPR',242],['c','Gaussian field',692],['d','Joint optimization',958]]) {
  text(letter,x,43,{size:font.letter,weight:700,anchor:'start'});
  text(title,x+29,43,{size:title==='Input supervision'?20:font.panel,weight:700,anchor:'start'});
}
text('Identity-preserving reliability',257,67,{size:font.small,anchor:'start',color:C.orange});
end();

begin('input','03 Input supervision','a');
await image('input-rgb',22,109,180,136);
await image('input-labels',22,285,180,136);
await image('input-clip',22,461,180,136);
text('RGB images',112,267);
text('Noisy identity labels',112,439);
text('CLIP features',112,615);
end();

begin('ipr','04 IPR contribution','b');
text('Cleanup',300,117,{weight:700});
lines(['Semantic','reliability'],444,95,{weight:700});
text('Area prior',588,117,{weight:700});
await image('cleanup-mask',240,132,120,108);
await image('semantic-crops',384,132,120,108);
await image('area-prior',528,132,120,108);
rect(274,283,340,49,'#fff2df','#e5b887',1.2,4);
text('Pixel reliability estimation',444,314,{weight:700,size:20});
await image('clean-labels',252,388,170,128);
await image('reliability',478,388,170,128);
text('Clean labels',337,541,{weight:700});
text('Reliability',563,541,{weight:700});
text('Y\u2032',337,594,{size:font.signal,weight:700,color:C.orange});
text('W',563,594,{size:font.signal,weight:700,color:C.blue});
rect(493,551,14,10,'#ffe35a'); text('High',513,563,{size:font.small,anchor:'start'});
rect(575,551,14,10,'#77734b'); text('Low',595,563,{size:font.small,anchor:'start'});
text('Preserve identities; downweight unreliable pixels',449,627,{size:font.small,color:C.muted});
end();

begin('gaussian','05 Gaussian representation','c');
await image('gaussian-illustration',702,128,224,270);
lines(['Identity-aware','language Gaussians'],814,429);
for(const [label,y,fill] of [['Appearance',482,'#f3f5f6'],['Language',522,'#edf4f9'],['Identity',562,'#f9f0df']]) {
  rect(706,y,216,38,fill);
  text(label,814,y+25,{weight:700});
}
end();

begin('optimization','06 Joint optimization','d');
await image('outlier-mask',1149,100,90,66);
text('Outlier mask',1194,89,{size:font.small});
const rowSpecs=[
  {y:230,left:'rasterized-identity',right:'target-identity',l:['Rasterized','identity'],r:['Clean labels'],loss:['Weighted','identity loss'],height:82},
  {y:397,left:'rasterized-language',right:'target-language',l:['Rasterized','language'],r:['CLIP feature','map'],loss:['Language','loss'],height:68},
  {y:550,left:'rendered-rgb',right:'target-rgb',l:['Rendered RGB'],r:['Ground-truth','RGB'],loss:['RGB','loss'],height:68},
];
for(const row of rowSpecs) {
  await image(row.left,978,row.y-53,118,106);
  await image(row.right,1292,row.y-53,118,106);
  rect(1126,row.y-row.height/2,136,row.height,'#ffffff',row.y===230?C.red:'#8e9ba2',1.4,4);
  lines(row.loss,1194,row.y-4,{weight:700});
  lines(row.l,1037,row.y+70,{size:font.small});
  lines(row.r,1351,row.y+70,{size:font.small});
}
text('Y\u2032',1351,134,{size:font.signal,weight:700,color:C.orange});
text('W',1194,326,{size:font.signal,weight:700,color:C.blue});
end();

begin('connections','07 Editable signal routing');
arrow([[203,353],[218,353],[218,200],[237,200]],C.ink);
poly([[300,241],[300,258],[444,258]],C.orangeLine);
poly([[588,241],[588,258],[444,258]],C.orangeLine);
arrow([[444,241],[444,280]],C.orangeLine);
arrow([[444,333],[444,358],[337,358],[337,384]],C.orangeLine);
arrow([[444,334],[444,358],[563,358],[563,384]],C.blue);
arrow([[337,550],[337,574]],C.orangeLine,1.6,9);
arrow([[563,566],[563,574]],C.blue,1.6,7);
arrow([[1351,144],[1351,174]],C.orangeLine);
arrow([[1194,167],[1194,187]],C.ink);
arrow([[1194,306],[1194,275]],C.blue);
for(const y of [230,397,550]) {
  arrow([[1098,y],[1123,y]],C.red,1.6,10);
  arrow([[1290,y],[1265,y]],C.red,1.6,10);
}
poly([[928,230],[941,230],[941,550]],C.ink);
for(const y of [230,397,550]) arrow([[941,y],[974,y]],C.ink);
text('Rasterize',963,315,{size:font.small,rotation:-90});
end();

const svg=`<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" width="${widthMM}mm" height="${heightMM}mm" viewBox="0 0 ${W} ${H}">
<title>ILGS-IPR pipeline: academic layout refinement</title>
<desc>IPR preserves identity labels and estimates pixel reliability for weighted identity supervision. Four panels show inputs, IPR, Gaussian representation and joint optimization. Y-prime and W labels denote matching signal ports. All sixteen existing illustration tiles are embedded unchanged; text, boxes, lines and arrows are editable SVG elements. Images are schematic, not quantitative evidence.</desc>
${layerStrings.join('\n')}
</svg>`;
await fs.writeFile(`${basename}.svg`,svg,'utf8');
execFileSync(inkscape,[`${basename}.svg`,'--export-type=png',`--export-filename=${basename}.png`,'--export-dpi=300'],{stdio:'inherit'});
execFileSync(inkscape,[`${basename}.svg`,'--export-type=pdf',`--export-filename=${basename}.pdf`],{stdio:'inherit'});

// Inkscape measures the actual rendered text; this catches font-dependent overflow.
const queried=execFileSync(inkscape,[`${basename}.svg`,'--query-all'],{encoding:'utf8'});
const scale=W/(widthMM/25.4*96);
const bounds=new Map(queried.trim().split(/\r?\n/).map(row=>{
  const [id,...v]=row.split(','); return [id,v.map(Number).map(n=>n*scale)];
}));
for(const t of auditText) t.bounds=bounds.get(t.id);
const textOverlaps=[];
function intersects(a,b,pad=0) {
  return a[0]+a[2]>b[0]+pad && b[0]+b[2]>a[0]+pad && a[1]+a[3]>b[1]+pad && b[1]+b[3]>a[1]+pad;
}
for(let i=0;i<auditText.length;i++) for(let j=i+1;j<auditText.length;j++) {
  const a=auditText[i],b=auditText[j];
  if(a.bounds && b.bounds && intersects(a.bounds,b.bounds,0.5)) textOverlaps.push([a.value,b.value]);
}
const imageTextOverlaps=[];
for(const t of auditText) for(const im of auditImages) {
  if(t.bounds && intersects(t.bounds,[im.x,im.y,im.width,im.height],1)) imageTextOverlaps.push([t.value,im.id]);
}
const lineTextOverlaps=[];
for(const t of auditText) for(const [a,b,sw] of auditSegments) {
  const box=[Math.min(a[0],b[0])-sw/2,Math.min(a[1],b[1])-sw/2,Math.abs(a[0]-b[0])+sw,Math.abs(a[1]-b[1])+sw];
  if(t.bounds && intersects(t.bounds,box,0.5)) lineTextOverlaps.push(t.value);
}
const outside=auditText.filter(t=>!t.bounds || t.bounds[0]<0 || t.bounds[1]<0 || t.bounds[0]+t.bounds[2]>W || t.bounds[1]+t.bounds[3]>H).map(t=>t.value);
const pdf=await fs.readFile(`${basename}.pdf`);
const audit={source,sourceHash,widthMM,heightMM,fontFamily:'Arial',minimumFontPt:Math.min(...auditText.map(t=>t.pt)),imageCount:auditImages.length,textCount:auditText.length,textOverlaps,imageTextOverlaps,lineTextOverlaps,outsideCanvas:outside,pdfHasEmbeddedFont:/\/FontFile[23]?\b/.test(pdf.toString('latin1')),images:auditImages,text:auditText};
await fs.writeFile(`${basename}_checks.json`,JSON.stringify(audit,null,2));
if(sourceHash!==crypto.createHash('sha256').update(await fs.readFile(source)).digest('hex')) throw new Error('Source SVG unexpectedly changed');
console.log(JSON.stringify({svg:`${basename}.svg`,minFontPt:audit.minimumFontPt,textOverlaps,imageTextOverlaps,lineTextOverlaps,outside,pdfHasEmbeddedFont:audit.pdfHasEmbeddedFont,minSourceDpi:Math.min(...auditImages.map(i=>i.effectiveDpi))},null,2));

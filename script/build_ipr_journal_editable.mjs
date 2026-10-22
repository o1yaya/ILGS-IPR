import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';

const require = createRequire(import.meta.url);
const sharp = require('C:/Users/hp/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const root = path.resolve('outputs/pipeline_masks_20261010');
const source = path.join(root, 'ILGS_IPR_pipeline_journal_layout.png');
const destination = path.join(root, 'ILGS_IPR_pipeline_journal_editable.svg');
const preview = path.join(root, 'ILGS_IPR_pipeline_journal_editable_preview.png');
const W = 1896, H = 830;
const metadata = await sharp(source).metadata();
const sx = metadata.width / W, sy = metadata.height / H;
const C = { ink: '#192f3b', orange: '#ec7916', teal: '#008977', red: '#dd3b43', line: '#becdd3' };
const layers = [];
let parts = [];
const esc = s => String(s).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
function begin(id, label) {
  parts = [`<g id="${id}" inkscape:groupmode="layer" inkscape:label="${esc(label)}">`];
}
function end() { parts.push('</g>'); layers.push(parts.join('\n')); }
function rect(x,y,w,h,fill,stroke='none',sw=1,rx=0) {
  parts.push(`<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${rx}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"/>`);
}
function text(value,x,y,size=18,weight=400,anchor='middle',fill=C.ink) {
  parts.push(`<text x="${x}" y="${y}" font-family="Arial, Helvetica, sans-serif" font-size="${size}" font-weight="${weight}" text-anchor="${anchor}" fill="${fill}" letter-spacing="0">${esc(value)}</text>`);
}
function line(points,color=C.ink,width=2) {
  parts.push(`<polyline points="${points.map(p=>p.join(',')).join(' ')}" fill="none" stroke="${color}" stroke-width="${width}" stroke-linejoin="round"/>`);
}
// Explicit arrowheads keep the connectors editable across SVG importers.
function arrow(points,color=C.ink,width=2,size=12) {
  const tip=points.at(-1), previous=points.at(-2);
  const angle=Math.atan2(tip[1]-previous[1],tip[0]-previous[0]);
  const base=[tip[0]-size*Math.cos(angle),tip[1]-size*Math.sin(angle)];
  line([...points.slice(0,-1),base],color,width);
  const spread=size*0.46;
  const side=[-Math.sin(angle)*spread,Math.cos(angle)*spread];
  parts.push(`<polygon points="${tip.join(',')} ${base[0]+side[0]},${base[1]+side[1]} ${base[0]-side[0]},${base[1]-side[1]}" fill="${color}"/>`);
}
let imageCount=0;
async function tile(id,box,caption,cx,cy,border=C.line) {
  const [x,y,w,h]=box;
  const left=Math.round(x*sx),top=Math.round(y*sy);
  const right=Math.round((x+w)*sx),bottom=Math.round((y+h)*sy);
  const data=await sharp(source).extract({left,top,width:right-left,height:bottom-top}).png().toBuffer();
  parts.push(`<g id="${id}" inkscape:label="${esc(caption || id)}"><image id="${id}-image" x="${x}" y="${y}" width="${w}" height="${h}" preserveAspectRatio="none" xlink:href="data:image/png;base64,${data.toString('base64')}"/><rect x="${x}" y="${y}" width="${w}" height="${h}" fill="none" stroke="${border}" stroke-width="1"/></g>`);
  imageCount++;
  if(caption) text(caption,cx,cy,18,400);
}

begin('stage-backgrounds','01 Panel backgrounds');
rect(0,0,W,H,'#ffffff');
rect(15,28,324,763,'#f5f6f7','#d3dce2',1.4,8);
rect(356,28,608,763,'#fff9f0','#ee983f',1.4,8);
rect(979,28,374,763,'#eff6fd','#8eb5da',1.4,8);
rect(1367,28,515,763,'#f0f8ed','#a5cea0',1.4,8);
end();

begin('headings','02 Editable panel headings');
for (const [letter,title,x] of [['a','Input supervision',31],['b','IPR',375],['c','Gaussian learning',998],['d','Joint optimization',1385]]) {
  text(letter,x,73,32,700,'start');
  text(title,x+43,73,26,700,'start');
}
end();

begin('input-supervision','03 Input images');
await tile('input-rgb',[38,100,279,207],'RGB images',177.5,332);
await tile('input-labels',[38,349,279,169],'Noisy identity labels',177.5,546);
await tile('input-clip',[38,562,279,175],'CLIP features',177.5,765);
end();

begin('ipr','04 IPR images and editable labels');
text('Cleanup',454,128,20,700);
text('Semantic reliability',649,128,20,700);
text('Area prior',865,128,20,700);
await tile('cleanup-mask',[374,149,161,128],null,0,0,'#d7a976');
await tile('semantic-crops',[555,149,189,130],null,0,0,'#e8bc91');
await tile('area-prior',[783,149,161,130],null,0,0,'#e8bc91');
rect(413,350,494,59,'#fff2e3',C.orange,1.5,8);
text('Pixel reliability estimation',660,388,22,700);
await tile('clean-labels',[385,472,243,153],'Clean labels Y\u2032',506.5,655,'#8bc4b7');
await tile('reliability',[688,472,239,153],'Reliability W',807.5,655,C.teal);
rect(727,670,22,15,'#ffe35a'); text('high',758,684,16,400,'start');
rect(837,670,22,15,'#77734b'); text('low',868,684,16,400,'start');
rect(382,701,565,67,'#fffdf9','#efc8a6',1,8);
parts.push('<circle cx="420" cy="735" r="21" fill="#ffe2bf"/>');
line([[410,735],[418,742],[433,722]],'#bc6414',4);
text('Preserve identities · downweight unreliable pixels',452,742,19,700,'start');
end();

begin('gaussian-field','05 Gaussian representation');
await tile('gaussian-illustration',[995,132,343,413],'Identity-aware language Gaussians',1166.5,574,'#cfdee6');
rect(991,614,348,126,'#f7f9fb','#b8cddc',1,5);
rect(1106,615,116,124,'#e6f2fc');
rect(1222,615,116,124,'#fff2c8');
line([[1106,615],[1106,739]],'#d0dbe1',1);
line([[1222,615],[1222,739]],'#d0dbe1',1);
text('Appearance',1049,669,16,700);
text('Language',1164,669,16,700);
text('Identity',1280,669,16,700);
text('color + geometry',1049,697,14);
text('CLIP-aligned',1164,697,14);
text('confidence-weighted',1280,697,12);
end();

begin('optimization','06 Optimization images and losses');
rect(1525,108,105,75,'#f7fae9','#c9daba',1,3);
await tile('outlier-mask',[1536,114,84,61],null,0,0,'#7f824d');
text('Outlier',1646,142,19,700,'start');
text('mask',1646,166,19,700,'start');
await tile('rasterized-identity',[1398,229,135,120],'Rasterized identity',1465.5,376,'#94c6bb');
await tile('target-identity',[1728,229,134,120],'Clean labels Y\u2032',1795,376,'#94c6bb');
rect(1566,245,128,97,'#ffffff',C.red,1.7,9);
text('Weighted',1630,286,19,700);
text('identity loss',1630,313,19,700);
await tile('rasterized-language',[1401,438,137,109],'Rasterized language',1469.5,573);
await tile('target-language',[1720,438,142,110],'CLIP feature map',1791,573);
rect(1573,451,113,83,'#ffffff',C.ink,1.5,7);
text('Language',1629.5,487,19,700);
text('loss',1629.5,512,19,700);
await tile('rendered-rgb',[1402,598,137,117],'Rendered RGB',1470.5,742);
await tile('target-rgb',[1720,598,142,117],'Ground-truth RGB',1791,742);
rect(1573,623,113,81,'#ffffff',C.ink,1.5,7);
text('RGB',1629.5,658,19,700);
text('loss',1629.5,683,19,700);
end();

begin('connectors','07 Editable connectors');
arrow([[319,437],[338,437],[338,214],[362,214]],C.ink,2,16);
line([[455,280],[455,310],[659,310]],C.orange,2);
line([[864,280],[864,310],[659,310]],C.orange,2);
arrow([[659,280],[659,344]],C.orange,2,17);
arrow([[659,409],[659,431],[513,431],[513,465]],C.orange,2,17);
arrow([[659,411],[659,431],[808,431],[808,465]],C.teal,2,17);
arrow([[629,543],[653,543]],C.orange,2,14);
text('Y\u2032',668,551,24,700,'middle',C.orange);
arrow([[929,543],[954,543]],C.teal,2,14);
text('W',971,551,24,700,'middle',C.teal);
text('Y\u2032',1800,175,25,700,'middle',C.orange);
arrow([[1800,185],[1800,223]],C.orange,2,17);
arrow([[1578,184],[1629,184],[1629,242]],C.ink,2,15);
text('W',1630,408,25,700,'middle',C.teal);
arrow([[1630,381],[1630,346]],C.teal,2,16);
// All loss comparisons converge on their loss node.
for (const [y,left,right,lossLeft,lossRight] of [[293,1535,1726,1564,1696],[493,1540,1718,1571,1688],[663,1541,1718,1571,1688]]) {
  arrow([[left,y],[lossLeft,y]],C.red,2,17);
  arrow([[right,y],[lossRight,y]],C.red,2,17);
}
line([[1339,676],[1362,676],[1362,293]],C.ink,2);
arrow([[1362,293],[1392,293]],C.ink,2,14);
arrow([[1362,493],[1395,493]],C.ink,2,14);
arrow([[1362,663],[1396,663]],C.ink,2,14);
parts.push(`<text x="1357" y="430" transform="rotate(-90 1357 430)" font-family="Arial, Helvetica, sans-serif" font-size="17" fill="${C.ink}">Rasterize</text>`);
end();

const svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
<title>ILGS-IPR journal-style pipeline</title>
<desc>Editable reconstruction of the approved generated layout. Image tiles are individually embedded raster illustrations; text, panel backgrounds, labels and connectors are editable vector elements. Matching Y-prime and W ports connect cleaned labels and reliability to identity supervision. Red arrows converge on loss nodes. The images are illustrative and not quantitative experimental evidence.</desc>
${layers.join('\n')}
</svg>`;
await fs.writeFile(destination, svg, 'utf8');
execFileSync('E:/Inkscape/bin/inkscape.com',[destination,'--export-type=png',`--export-filename=${preview}`,'--export-width=2844'],{stdio:'inherit'});
console.log(JSON.stringify({destination,preview,embeddedImages:imageCount,sourceSize:[metadata.width,metadata.height]},null,2));

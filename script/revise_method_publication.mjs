// Academic Figure Skill: no matching plot template; preserve the editable native SVG.
// Original categorical assets are deterministically re-exported without render artefacts.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
import {execFileSync} from 'node:child_process';
const require=createRequire(import.meta.url);
const deps='C:/Users/hp/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const xml=require(`${deps}/xml-js`),sharp=require(`${deps}/sharp`);
const dir='D:/wlxy/ilgs/文章图',source=path.join(dir,'method_optimized.svg'),output=path.join(dir,'method_final');
const assetDir='D:/PycharmProjects/PythonProject/ILGS_release-main/outputs/method_figure_pipeline_gpt_image2_20261009/source_assets';
const cleanDir='D:/PycharmProjects/PythonProject/ILGS_release-main/outputs/method_clean_assets_20261010';
const original=await fs.readFile(source,'utf8');
const hash=v=>crypto.createHash('sha256').update(v).digest('hex');
const sourceHash=hash(original),tree=xml.xml2js(original,{compact:false}),nodes=[];
function walk(n,p){if(n.type==='element')nodes.push([n,p]);for(const c of n.elements||[])walk(c,n);}
walk(tree);
const root=nodes.find(([n])=>n.name==='svg')[0];
const crops=new Set(['cleanup-image','stage1-noisy-map','area-image','reliability-map-image']);
const images=[],clips=[],texts=[],arrows=[];
const W=1440,H=988,widthMM=183,pt=widthMM/25.4*72/W;
await fs.mkdir(cleanDir,{recursive:true});

async function reexportCategorical(input,outputPath){
  const {data,info}=await sharp(input).raw().toBuffer({resolveWithObject:true});
  const palette=[[187,194,169],[203,171,174],[171,217,196],[102,205,137],[164,183,209],[90,132,216],[233,80,137]];
  const keyToLabel=new Map(palette.map((c,i)=>[((c[0]<<16)|(c[1]<<8)|c[2]),i]));
  const labels=new Uint8Array(info.width*info.height),unresolved=[];
  for(let p=0,i=0;p<labels.length;p++,i+=3){
    const key=(data[i]<<16)|(data[i+1]<<8)|data[i+2],label=keyToLabel.get(key);
    if(label===undefined){labels[p]=255;unresolved.push(p);}else labels[p]=label;
  }
  let pending=unresolved;
  for(let pass=0;pending.length&&pass<64;pass++){
    const next=[],assigned=[];
    for(const p of pending){
      const x=p%info.width,y=Math.floor(p/info.width),count=new Uint16Array(palette.length);
      for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){
        if(!dx&&!dy)continue;
        const nx=x+dx,ny=y+dy;
        if(nx<0||ny<0||nx>=info.width||ny>=info.height)continue;
        const label=labels[ny*info.width+nx];
        if(label!==255)count[label]++;
      }
      let best=-1,bestCount=0;
      for(let i=0;i<count.length;i++)if(count[i]>bestCount){best=i;bestCount=count[i];}
      if(bestCount)assigned.push([p,best]);else next.push(p);
    }
    for(const [p,label] of assigned)labels[p]=label;
    if(next.length===pending.length)break;
    pending=next;
  }
  if(pending.length)throw Error(`Could not reconstruct ${pending.length} categorical pixels`);
  const out=Buffer.alloc(data.length);
  for(let p=0,i=0;p<labels.length;p++,i+=3){const c=palette[labels[p]];out[i]=c[0];out[i+1]=c[1];out[i+2]=c[2];}
  await sharp(out,{raw:info}).png({compressionLevel:9}).toFile(outputPath);
  return {removedPixels:unresolved.length,palette};
}

async function reexportReliability(input,outputPath){
  const {data,info}=await sharp(input).raw().toBuffer({resolveWithObject:true});
  const background=[112,120,116],foreground=[252,223,102],out=Buffer.alloc(data.length);
  let backgroundPixels=0,foregroundPixels=0;
  for(let i=0;i<data.length;i+=3){
    const db=(data[i]-background[0])**2+(data[i+1]-background[1])**2+(data[i+2]-background[2])**2;
    const df=(data[i]-foreground[0])**2+(data[i+1]-foreground[1])**2+(data[i+2]-foreground[2])**2;
    const c=df<db?foreground:background;
    if(c===foreground)foregroundPixels++;else backgroundPixels++;
    out[i]=c[0];out[i+1]=c[1];out[i+2]=c[2];
  }
  await sharp(out,{raw:info}).png({compressionLevel:9}).toFile(outputPath);
  return {background,foreground,backgroundPixels,foregroundPixels};
}

const cleanupPath=path.join(cleanDir,'structure_cleanup_clean.png');
const reliabilityPath=path.join(cleanDir,'reliability_map_clean.png');
const cleaning={
  cleanup:await reexportCategorical(path.join(assetDir,'structure_cleanup.png'),cleanupPath),
  reliability:await reexportReliability(path.join(assetDir,'reliability_map.png'),reliabilityPath)
};
const replacements=new Map([
  ['cleanup-image',await fs.readFile(cleanupPath)],
  ['reliability-map-image',await fs.readFile(reliabilityPath)]
]);
for(const [n,p] of nodes.filter(([n])=>n.name==='image')){
  const a=n.attributes,href=a['xlink:href']||a.href;
  if(!href?.startsWith('data:image/'))throw Error('Image is not embedded');
  let bytes=Buffer.from(href.slice(href.indexOf(',')+1),'base64');
  const replacement=replacements.get(a.id);
  if(replacement){
    bytes=replacement;
    a['xlink:href']='data:image/png;base64,'+bytes.toString('base64');
    delete a.href;
  }
  const m=await sharp(bytes).metadata();
  const box=['x','y','width','height'].map(k=>Number(a[k]));
  let crop=null;
  if(crops.has(a.id)){
    if(m.width!==4032||m.height!==3024)throw Error('Unexpected map dimensions');
    const [x,y,w,h]=box,s=4032/3968,id=a.id+'-edge-viewport';
    crop={left:32,right:32,top:24,bottom:24,visiblePixels:[3968,2976]};
    Object.assign(a,{x:String(x-w*(s-1)/2),y:String(y-h*(s-1)/2),width:String(w*s),height:String(h*s)});
    clips.push({type:'element',name:'clipPath',attributes:{id,clipPathUnits:'userSpaceOnUse'},elements:[{type:'element',name:'rect',attributes:{x:String(x),y:String(y),width:String(w),height:String(h)}}]});
    p.elements[p.elements.indexOf(n)]={type:'element',name:'g',attributes:{id:a.id+'-viewport','clip-path':`url(#${id})`},elements:[n]};
  }
  images.push({id:a.id,pixels:[m.width,m.height],viewport:box,sha256:hash(bytes),reexported:Boolean(replacement),crop,effectiveDpi:(crop?.visiblePixels[0]||m.width)/(box[2]/W*widthMM/25.4)});
}
if(images.length!==12)throw Error('Unexpected image count');
root.elements.unshift({type:'element',name:'defs',elements:clips});
for(const [n] of nodes.filter(([n])=>n.name==='text')){
  const a=n.attributes,value=(n.elements||[]).map(c=>c.text||'').join('');
  if(Number(a['font-size'])>19.4)a['font-size']='19.4';
  texts.push({id:a.id,value,pt:Number(a['font-size'])*pt});
}
// Reflow the equation after resizing, instead of leaving old character positions.
const mathPositions=[['label-21',811,795,19.4],['label-22',821,801,14],['label-23',821,782,14],['label-24',848,795,19.4],['label-25',944,801,14],['label-26',958,795,19.4]];
for(const [id,x,y,size] of mathPositions){
  const n=nodes.find(([n])=>n.attributes?.id===id)[0];
  Object.assign(n.attributes,{x:String(x),y:String(y),'font-size':String(size)});
  texts.find(t=>t.id===id).pt=size*pt;
}
const connections=nodes.find(([n])=>n.attributes?.id==='connections')[0],blue='#2166ac';
connections.elements=connections.elements.filter(n=>n.attributes?.stroke!==blue&&n.attributes?.fill!==blue);
function arrow(id,points,size=12){
  const [x,y]=points.at(-1),[px,py]=points.at(-2),a=Math.atan2(y-py,x-px);
  const bx=x-size*Math.cos(a),by=y-size*Math.sin(a),dx=-Math.sin(a)*size*.42,dy=Math.cos(a)*size*.42;
  connections.elements.push({type:'element',name:'polyline',attributes:{id:id+'-stem',points:[...points.slice(0,-1),[bx,by]].map(p=>p.join(',')).join(' '),fill:'none',stroke:blue,'stroke-width':'2.2','stroke-linejoin':'round'}});
  connections.elements.push({type:'element',name:'polygon',attributes:{id:id+'-head',points:`${x},${y} ${bx+dx},${by+dy} ${bx-dx},${by-dy}`,fill:blue}});
  arrows.push({id,points,widthPt:2.2*pt});
}
arrow('reliability-to-loss',[[726,788],[760,788]],10);
arrow('weighted-supervision-to-field',[[1027,785],[1058,785],[1058,360]]);
root.elements.find(n=>n.name==='desc').elements=[{type:'text',text:'Final editable method figure. Structure cleanup is reconstructed from its seven original categorical colors by spatially filling only the eighth dark artefact color. Reliability is re-exported as its two original semantic levels by nearest-palette assignment, removing the unintended blue seam. Map viewports trim 32 horizontal and 24 vertical source pixels per edge. Blue connections feed the pixel-wise identity loss and field training. Gains refer to the supplied ten-scene three-seed 3D-OVS aggregate, not this qualitative frame.'}];
await fs.writeFile(output+'.svg',xml.js2xml(tree,{compact:false,spaces:2}));
const inkscape='E:/Inkscape/bin/inkscape.com';
for(const type of ['png','pdf'])execFileSync(inkscape,[output+'.svg','--export-type='+type,'--export-filename='+output+'.'+type,...(type==='png'?['--export-dpi=300']:[])],{stdio:'inherit'});
const raw=execFileSync(inkscape,[output+'.svg','--query-all'],{encoding:'utf8'}),factor=W/(widthMM/25.4*96);
const bounds=new Map(raw.trim().split(/\r?\n/).map(r=>{const [id,...v]=r.split(',');return[id,v.map(Number).map(x=>x*factor)];}));
const intersects=(a,b)=>a[0]+a[2]>b[0]+.6&&b[0]+b[2]>a[0]+.6&&a[1]+a[3]>b[1]+.6&&b[1]+b[3]>a[1]+.6;
const issues={textText:[],textBlueArrow:[],outside:[]};
for(let i=0;i<texts.length;i++){
  const t=texts[i],b=bounds.get(t.id);t.bounds=b;
  if(!b||b[0]<0||b[1]<0||b[0]+b[2]>W||b[1]+b[3]>H)issues.outside.push(t.value);
  for(let j=i+1;j<texts.length;j++){const o=bounds.get(texts[j].id);if(b&&o&&intersects(b,o))issues.textText.push([t.value,texts[j].value]);}
  for(const a of arrows)for(let j=1;j<a.points.length;j++){
    const p=a.points[j-1],q=a.points[j],s=[Math.min(p[0],q[0])-1.1,Math.min(p[1],q[1])-1.1,Math.abs(p[0]-q[0])+2.2,Math.abs(p[1]-q[1])+2.2];
    if(b&&intersects(b,s))issues.textBlueArrow.push([t.value,a.id]);
  }
}
const sourceUnchanged=sourceHash===hash(await fs.readFile(source));
if(!sourceUnchanged)throw Error('Source changed unexpectedly');
const pdf=await fs.readFile(output+'.pdf');
const audit={source,sourceHash,sourceUnchanged,widthMM,heightMM:H/W*widthMM,cleaning,images,texts,arrows,issues,minFontPt:Math.min(...texts.map(t=>t.pt)),maxFontPt:Math.max(...texts.map(t=>t.pt)),pdfHasEmbeddedFonts:/\/FontFile[23]?\b/.test(pdf.toString('latin1'))};
await fs.writeFile(output+'_checks.json',JSON.stringify(audit,null,2));
console.log(JSON.stringify({...audit,images:images.length,texts:texts.length},null,2));
if(Object.values(issues).some(x=>x.length))process.exitCode=1;

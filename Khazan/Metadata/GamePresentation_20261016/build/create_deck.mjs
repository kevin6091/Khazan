import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const runtime='C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies';
const {Presentation,PresentationFile}=await import(pathToFileURL(runtime+'/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs').href);
const root=path.resolve('Metadata/GamePresentation_20261016');
const deck=JSON.parse(await fs.readFile(root+'/deck.json','utf8'));
const p=Presentation.create({slideSize:{width:1280,height:720}});
const C=deck.theme;
function txt(s,t,x,y,w,h,size=27,color=C.white,bold=false){let a=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});a.text=t;a.text.style={typeface:C.font,fontSize:size,color,bold,insets:0,verticalAlignment:'top',autoFit:'none',wrap:'square'};return a;}
async function image(s,f,x,y,w,h,crop){let b=await fs.readFile(root+'/assets/'+f);s.images.add({blob:new Uint8Array(b),contentType:f.endsWith('.jpg')?'image/jpeg':'image/png',alt:f,fit:'cover',position:{left:x,top:y,width:w,height:h},...(crop?{crop}:{})});}
function table(s,values,x,y,w,h,widths,header=true){let t=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:w,height:h,values,columnWidths:widths});t.borders.assign({fill:'#51405C',width:0.7});for(let r=0;r<values.length;r++)for(let c=0;c<values[r].length;c++){let a=t.getCell(r,c);a.fill=C.background;a.text.style={typeface:C.font,fontSize:25,color:header&&r===0?C.purple:c===0?C.red:C.white,bold:(header&&r===0)||c===0,insets:12,verticalAlignment:'middle'};}return t;}
for(let i=0;i<deck.slides.length;i++){
let d=deck.slides[i],s=p.slides.add();s.background.fill=C.background;s.speakerNotes.text=d.notes;
if(d.layout==='cover'){await image(s,d.image,0,0,1280,720);txt(s,d.caption,56,490,520,40,24,C.purple,true);txt(s,d.title,56,537,650,75,48,C.white,true);txt(s,'Unreal Engine 5.8',56,625,520,40,24);continue;}
txt(s,d.title,64,48,1152,65,44,C.white,true);if(d.subtitle)txt(s,d.subtitle,64,119,1152,44,25,C.muted);
txt(s,String(i+1).padStart(2,'0'),1200,669,50,30,21,C.muted);
if(d.footnote)txt(s,d.footnote,64,625,1100,60,23,C.muted);
if(d.layout==='wide_image'){await image(s,d.image,64,134,1152,340);for(let j=0;j<2;j++){txt(s,d.items[j][0],64+j*608,504,544,40,27,C.red,true);txt(s,d.items[j][1],64+j*608,548,544,105,25);}}
if(d.layout==='controls')for(let j=0;j<2;j++){let x=64+j*605;txt(s,d.columns[j].heading,x,190,547,45,29,C.red,true);table(s,d.columns[j].rows,x,242,547,320,[170,377],false);}
if(d.layout==='roles')for(let j=0;j<3;j++){let x=64+j*400;txt(s,d.items[j][0],x,240,352,65,33,j===1?C.red:C.purple,true);txt(s,d.items[j][1],x,324,352,250,28);}
if(d.layout==='sequence')for(let j=0;j<4;j++){let x=64+(j%2)*615,y=166+Math.floor(j/2)*212;txt(s,d.items[j][0],x,y,537,45,31,j%2?C.red:C.purple,true);txt(s,d.items[j][1],x,y+59,537,142,28);}
if(d.layout==='table')table(s,[d.headers,...d.rows],64,198,1152,398,[265,449,438]);
if(d.layout==='split'){await image(s,d.image,64,160,650,386,d.imageCrop?{left:174/939,top:146/510,right:173/939,bottom:12/510}:undefined);txt(s,d.caption,64,562,650,60,20,C.muted);for(let j=0;j<2;j++){let y=160+j*213;txt(s,d.items[j][0],756,y,460,50,29,j?C.red:C.purple,true);txt(s,d.items[j][1],756,y+61,460,146,26);}}
if(d.layout==='comparison')for(let j=0;j<2;j++){await image(s,d.images[j].path,64+j*592,197,560,326);txt(s,d.images[j].label,64+j*592,545,560,50,27,j?C.red:C.purple,true);}
}
await fs.mkdir(root+'/build/native-render',{recursive:true});
await (await PresentationFile.exportPptx(p)).save(root+'/build/candidate.pptx');
console.log('EXPORTED '+p.slides.items.length);
for(let i=0;i<p.slides.items.length;i++){const b=await p.export({slide:p.slides.items[i],format:'png',scale:1});await fs.writeFile(root+'/build/native-render/slide-'+String(i+1).padStart(2,'0')+'.png',new Uint8Array(await b.arrayBuffer()));}
console.log('RENDERED');


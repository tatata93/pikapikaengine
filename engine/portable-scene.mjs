import {Scene,validateScene} from './scene.mjs';

const header=['pikapika-scene 1','units m s kg','axes right-handed y-up'];
const maxId=9007199254740991n;
const types=new Set(['box','plane','robot']);
function stableId(value) {
  if(typeof value!=='string'||! /^[1-9][0-9]{0,15}$/.test(value)||BigInt(value)>maxId) throw new Error('Invalid native stable ID');
  return value;
}
function numeric(value) { const n=Number(value); if(!value||!Number.isFinite(n)) throw new Error('Nonfinite portable scene number'); return n; }
function tokenize(line) {
  const result=[];let i=0;
  while(i<line.length) {
    while(i<line.length&&/\s/.test(line[i]))i++;
    if(i===line.length) break;
    let value='',quoted=false;
    if(line[i]==='"') {
      quoted=true;i++;let closed=false;
      while(i<line.length) {
        const c=line[i++];
        if(c==='"'){closed=true;break;}
        if(c==='\\'){if(i===line.length)throw new Error('Broken quoted escape');value+=line[i++];}
        else value+=c;
      }
      if(!closed||i<line.length&&!/\s/.test(line[i]))throw new Error('Broken quoted property');
    } else {while(i<line.length&&!/\s/.test(line[i]))value+=line[i++];}
    result.push({value,quoted});
  }
  return result;
}
function quote(value) {
  if(typeof value!=='string'||/[\r\n]/.test(value)||value.length>1024)throw new Error('Invalid portable scene name');
  return '"'+value.replace(/[\\"]/g,'\\$&')+'"';
}
function hashId(id) {
  let hash=14695981039346656037n;
  for(const byte of new TextEncoder().encode(id)){hash^=BigInt(byte);hash=BigInt.asUintN(64,hash*1099511628211n);}
  return ((hash%maxId)+1n).toString();
}

// The geometry subset is box/plane/robot and rotations around Y only. Unsupported
// rotations fail; primitive source types and numeric identities survive edits.
export function parsePortableScene(text) {
  if(typeof text!=='string'||text.length>2e6)throw new Error('Portable scene limit: 2 MB');
  const lines=text.replace(/\r\n/g,'\n').split('\n');
  if(header.some((s,i)=>s!==lines[i]))throw new Error('Unsupported portable scene header/version/units/axes');
  const entities=[],ids=new Set(),metadata=new Map(),comments=[];
  for(const line of lines.slice(3)) {
    if(line.length>4096)throw new Error('Portable scene line limit');
    if(!line)continue;
    if(line.startsWith('# browser-meta ')) {
      const m=JSON.parse(line.slice(15)); stableId(m.nativeId);
      if(metadata.has(m.nativeId)||typeof m.id!=='string'||!m.id||m.id.length>96||
        !Array.isArray(m.color)||m.color.length!==3||m.color.some(n=>!Number.isFinite(n)||n<0||n>1))throw new Error('Invalid browser scene metadata');
      metadata.set(m.nativeId,m);continue;
    }
    if(line.startsWith('#')){comments.push(line);continue;}
    const t=tokenize(line);
    if(t.length!==15||t[0].value!=='entity'||!t[2].quoted||!t[3].quoted)throw new Error('Malformed portable entity');
    const id=stableId(t[1].value),sourceType=t[2].value,name=t[3].value;
    if(ids.has(id))throw new Error('Duplicate native stable ID');ids.add(id);
    if(!types.has(sourceType))throw new Error('Unsupported portable primitive: '+sourceType);
    if(name.length>1024||/[\r\n]/.test(name))throw new Error('Invalid portable name');
    const n=t.slice(4).map(x=>numeric(x.value)),q=n.slice(3,7),scale=n.slice(7,10),radius=n[10];
    if(Math.abs(q.reduce((s,v)=>s+v*v,0)-1)>=1e-6)throw new Error('Quaternion must be normalized');
    if(Math.abs(q[0])>1e-12||Math.abs(q[2])>1e-12)throw new Error('Browser portable scenes support Y rotation only');
    if(scale.some(x=>x<=0)||radius<0)throw new Error('Invalid portable scale/radius');
    if(sourceType==='plane')scale[1]*=0.02;
    entities.push({id:`native:${id}`,nativeId:id,type:'box',sourceType,name,nativeRadius:radius,
      position:n.slice(0,3),yaw:2*Math.atan2(q[1],q[3]),scale,
      color:sourceType==='robot'?[.06,.8,1]:sourceType==='plane'?[.08,.12,.2]:[.7,.2,.12]});
  }
  for(const id of metadata.keys())if(!ids.has(id))throw new Error('Browser metadata references missing entity');
  for(const entity of entities)if(metadata.has(entity.nativeId)) {
    const m=metadata.get(entity.nativeId);entity.id=m.id;entity.color=m.color;
  }
  const scene=new Scene({version:1,units:'m-s-kg',axes:'right-handed-y-up',entities,portableComments:comments});
  return scene;
}

export function savePortableScene(scene) {
  const data=validateScene(scene instanceof Scene?scene.data:scene);
  const records=[],metadata=[],ids=new Set();
  for(const e of data.entities) {
    const id=e.nativeId!==undefined?stableId(e.nativeId):hashId(e.id);
    if(ids.has(id))throw new Error('Native ID collision; assign a distinct nativeId');ids.add(id);
    const sourceType=e.sourceType??'box';if(!types.has(sourceType))throw new Error('Unsupported portable primitive');
    const radius=e.nativeRadius??1;if(!Number.isFinite(radius)||radius<0)throw new Error('Invalid native radius');
    const scale=[...e.scale];if(sourceType==='plane')scale[1]/=0.02;
    const properties=[...e.position,0,Math.sin(e.yaw/2),0,Math.cos(e.yaw/2),...scale,radius];
    if(properties.some(x=>!Number.isFinite(x)))throw new Error('Portable numeric range exceeded');
    metadata.push('# browser-meta '+JSON.stringify({nativeId:id,id:e.id,color:e.color}));
    records.push(`entity ${id} ${quote(sourceType)} ${quote(e.name??e.id)} ${properties.join(' ')}`);
  }
  const comments=data.portableComments??[];
  if(!Array.isArray(comments)||comments.some(s=>typeof s!=='string'||!s.startsWith('#')||s.startsWith('# browser-meta ')||s.length>4096||/[\r\n]/.test(s)))throw new Error('Invalid portable comments');
  const result=[...header,...comments,...metadata,...records,''].join('\n');
  if(result.length>2e6)throw new Error('Portable scene limit: 2 MB');
  return result;
}

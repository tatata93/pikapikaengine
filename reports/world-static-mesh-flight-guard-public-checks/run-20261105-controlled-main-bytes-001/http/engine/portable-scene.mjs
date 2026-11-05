import {Scene,validateScene} from './scene.mjs';
import {validateMesh} from './mesh.mjs';

const header=['pikapika-scene 1','units m s kg','axes right-handed y-up'];
const maxId=9007199254740991n;
const nongeometryTypes=new Set(['camera','source','listener']);
const types=new Set(['box','plane','robot','mesh',...nongeometryTypes]);
function stableId(value) {
  if(typeof value!=='string'||! /^[1-9][0-9]{0,15}$/.test(value)||BigInt(value)>maxId) throw new Error('Invalid native stable ID');
  return value;
}
function numeric(value) {
  if(!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(value))throw new Error('Invalid portable scene number');
  const n=Number(value); if(!Number.isFinite(n)) throw new Error('Nonfinite portable scene number'); return n;
}
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

// Geometry is box/plane/robot; camera/source/listener retain typed transforms.
// The browser subset has Y rotation only and rejects unsupported rotations.
export function parsePortableScene(text) {
  if(typeof text!=='string'||text.length>2e6)throw new Error('Portable scene limit: 2 MB');
  const lines=text.replace(/\r\n/g,'\n').split('\n');
  if(!['pikapika-scene 1','pikapika-scene 2'].includes(lines[0])||header.slice(1).some((s,i)=>s!==lines[i+1]))throw new Error('Unsupported portable scene header/version/units/axes');
  const version=Number(lines[0].slice(-1));
  const entities=[],ids=new Set(),metadata=new Map(),comments=[],byNativeId=new Map(),meshBlocks=new Set();
  let totalVertices=0,totalTriangles=0;
  for(let lineIndex=3;lineIndex<lines.length;lineIndex++) {
    const line=lines[lineIndex];
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
    if(t[0]?.value==='mesh') {
      if(version!==2||t.length!==4||t.some(x=>x.quoted))throw new Error('Malformed mesh block header/version');
      const nativeId=stableId(t[1].value),entity=byNativeId.get(nativeId);
      if(!entity||entity.type!=='mesh'||meshBlocks.has(nativeId))throw new Error('Unknown or duplicate mesh block');
      if(!t.slice(2).every(x=>/^[0-9]+$/.test(x.value)))throw new Error('Invalid mesh counts');
      const vertices=Number(t[2].value),triangles=Number(t[3].value);
      if(vertices<3||vertices>65536||triangles<1||triangles>131072)throw new Error('Mesh block count limit exceeded');
      totalVertices+=vertices;totalTriangles+=triangles;
      if(totalVertices>262144||totalTriangles>524288)throw new Error('Scene mesh geometry quota exceeded');
      const readRecord=(tag)=>{
        const record=lines[++lineIndex];
        if(typeof record!=='string'||!record||record.length>4096)throw new Error('Incomplete mesh geometry block');
        const tokens=tokenize(record);
        if(tokens.length!==4||tokens[0].value!==tag||tokens.some(x=>x.quoted))throw new Error('Malformed mesh '+tag);
        return tokens.slice(1).map(x=>x.value);
      };
      const mesh={version:1,positions:[],triangles:[]};
      for(let i=0;i<vertices;i++)mesh.positions.push(readRecord('vertex').map(numeric));
      for(let i=0;i<triangles;i++) {
        const values=readRecord('triangle');
        if(!values.every(x=>/^[0-9]+$/.test(x)))throw new Error('Invalid mesh triangle indices');
        mesh.triangles.push(values.map(Number));
      }
      entity.mesh=validateMesh(mesh);meshBlocks.add(nativeId);continue;
    }
    if(t.length!==15||t[0].value!=='entity'||!t[2].quoted||!t[3].quoted)throw new Error('Malformed portable entity');
    if(t.some((token,index)=>index!==2&&index!==3&&token.quoted))throw new Error('Quoted numeric portable property');
    const id=stableId(t[1].value),sourceType=t[2].value,name=t[3].value;
    if(ids.has(id))throw new Error('Duplicate native stable ID');ids.add(id);
    if(!types.has(sourceType))throw new Error('Unsupported portable primitive: '+sourceType);
    if(sourceType==='mesh'&&version!==2)throw new Error('Mesh entities require scene version 2');
    if(name.length>1024||/[\r\n]/.test(name))throw new Error('Invalid portable name');
    const n=t.slice(4).map(x=>numeric(x.value)),q=n.slice(3,7),scale=n.slice(7,10),radius=n[10];
    if(Math.abs(q.reduce((s,v)=>s+v*v,0)-1)>=1e-6)throw new Error('Quaternion must be normalized');
    if(Math.abs(q[0])>1e-12||Math.abs(q[2])>1e-12)throw new Error('Browser portable scenes support Y rotation only');
    if(scale.some(x=>x<=0)||radius<0)throw new Error('Invalid portable scale/radius');
    if(nongeometryTypes.has(sourceType)&&radius!==0)throw new Error('Nongeometry radius is reserved as zero');
    if(sourceType==='plane')scale[1]*=0.02;
    const entity={id:`native:${id}`,nativeId:id,type:nongeometryTypes.has(sourceType)||sourceType==='mesh'?sourceType:'box',sourceType,name,nativeRadius:radius,
      position:n.slice(0,3),yaw:2*Math.atan2(q[1],q[3]),scale,
      color:nongeometryTypes.has(sourceType)?[0,0,0]:sourceType==='robot'?[.06,.8,1]:sourceType==='plane'?[.08,.12,.2]:[.7,.2,.12]};
    entities.push(entity);byNativeId.set(id,entity);
  }
  for(const entity of entities)if(entity.type==='mesh'&&!meshBlocks.has(entity.nativeId))throw new Error('Missing mesh geometry block');
  for(const id of metadata.keys())if(!ids.has(id))throw new Error('Browser metadata references missing entity');
  for(const entity of entities)if(metadata.has(entity.nativeId)) {
    const m=metadata.get(entity.nativeId);entity.id=m.id;entity.color=m.color;
  }
  const scene=new Scene({version,units:'m-s-kg',axes:'right-handed-y-up',entities,portableComments:comments});
  return scene;
}

export function savePortableScene(scene) {
  const data=validateScene(scene instanceof Scene?scene.data:scene);
  const records=[],metadata=[],ids=new Set();
  for(const e of data.entities) {
    const id=e.nativeId!==undefined?stableId(e.nativeId):hashId(e.id);
    if(ids.has(id))throw new Error('Native ID collision; assign a distinct nativeId');ids.add(id);
    const sourceType=e.sourceType??e.type;if(!types.has(sourceType))throw new Error('Unsupported portable primitive');
    if(nongeometryTypes.has(sourceType)||sourceType==='mesh'?e.type!==sourceType:e.type!=='box')throw new Error('Portable source type does not match entity type');
    const radius=e.nativeRadius??(nongeometryTypes.has(sourceType)?0:1);if(!Number.isFinite(radius)||radius<0)throw new Error('Invalid native radius');
    if(nongeometryTypes.has(sourceType)&&radius!==0)throw new Error('Nongeometry radius is reserved as zero');
    const scale=[...e.scale];if(sourceType==='plane')scale[1]/=0.02;
    const properties=[...e.position,0,Math.sin(e.yaw/2),0,Math.cos(e.yaw/2),...scale,radius];
    if(properties.some(x=>!Number.isFinite(x)))throw new Error('Portable numeric range exceeded');
    metadata.push('# browser-meta '+JSON.stringify({nativeId:id,id:e.id,color:e.color??[0,0,0]}));
    records.push(`entity ${id} ${quote(sourceType)} ${quote(e.name??e.id)} ${properties.join(' ')}`);
    if(e.type==='mesh') {
      const mesh=validateMesh(e.mesh);records.push(`mesh ${id} ${mesh.positions.length} ${mesh.triangles.length}`);
      for(const position of mesh.positions)records.push('vertex '+position.join(' '));
      for(const triangle of mesh.triangles)records.push('triangle '+triangle.join(' '));
    }
  }
  const comments=data.portableComments??[];
  if(!Array.isArray(comments)||comments.some(s=>typeof s!=='string'||!s.startsWith('#')||s.startsWith('# browser-meta ')||s.length>4096||/[\r\n]/.test(s)))throw new Error('Invalid portable comments');
  const outputHeader=[...header];if(data.entities.some(e=>e.type==='mesh'))outputHeader[0]='pikapika-scene 2';
  const result=[...outputHeader,...comments,...metadata,...records,''].join('\n');
  if(result.length>2e6)throw new Error('Portable scene limit: 2 MB');
  return result;
}

import {validateMesh} from './mesh.mjs';
import {createMotionSource,serializeMotionPortable,parseMotionPortable} from './motion.mjs';
import {savePortableScene,parsePortableScene} from './portable-scene.mjs';
import {parseStrictJson,stringifyStrictJson,utf8Length} from './strict-json.mjs';

const MAX_BYTES=8*1024*1024,MAX_MOTION_BYTES=4*1024*1024,MAX_ID=Number.MAX_SAFE_INTEGER;
const exact=(x,fields,label)=>{if(!x||typeof x!=='object'||Array.isArray(x)||Object.keys(x).length!==fields.length||Object.keys(x).some(k=>!fields.includes(k)))throw new Error('Invalid '+label+' fields');};
const finite=(x,label)=>{if(typeof x!=='number'||!Number.isFinite(x))throw new Error(label+' requires a finite number');return x;};
const integer=(x,lo,hi,label)=>{finite(x,label);if(!Number.isInteger(x)||x<lo||x>hi)throw new Error(label+' integer outside '+lo+'..'+hi);return x===0?0:x;};
const vector=(v,n,label,limit=Infinity)=>{if(!Array.isArray(v)||v.length!==n)throw new Error(label+' width');return Array.from(v,x=>{finite(x,label);if(Math.abs(x)>limit)throw new Error(label+' numeric range');return x;});};
const name=(x,label,bytes=256)=>{if(typeof x!=='string'||/[\u0000-\u001f\u007f]/u.test(x)||utf8Length(x)>bytes)throw new Error(label+' requires printable UTF-8 within '+bytes+' bytes');return x;};
const nativeId=x=>{if(typeof x!=='string'||!/^[1-9][0-9]{0,15}$/.test(x)||BigInt(x)>BigInt(MAX_ID))throw new Error('Invalid native object ID');return x;};
const matrix=(m,label)=>{const a=vector(m,16,label,1e150);if(a[3]!==0||a[7]!==0||a[11]!==0||a[15]!==1)throw new Error(label+' must be affine');return a;};
const sameVector=(a,b)=>a.length===b.length&&a.every((v,i)=>v===b[i]);
const samePose=(a,b)=>['position','rotation','scale'].every(k=>sameVector(a[k],b[k]));
const decimal=x=>Object.is(x,-0)?'-0':String(x);
const quoted=x=>JSON.stringify(x);

export function meshFingerprint(input){
 const mesh=validateMesh(input);let hash=0xcbf29ce484222325n;
 const byte=b=>{hash=BigInt.asUintN(64,(hash^BigInt(b))*0x100000001b3n);};
 const buffer=new ArrayBuffer(8),view=new DataView(buffer),bytes=new Uint8Array(buffer);
 const u32=n=>{view.setUint32(0,n,true);for(let j=0;j<4;++j)byte(bytes[j]);};
 for(const b of new TextEncoder().encode('pikapika_mesh_fingerprint 1\n'))byte(b);
 u32(mesh.version);u32(mesh.positions.length);u32(mesh.triangles.length);
 for(const p of mesh.positions)for(const n of p){view.setFloat64(0,n===0?0:n,true);for(let j=0;j<8;++j)byte(bytes[j]);}
 for(const t of mesh.triangles)for(const n of t)u32(n);
 return hash.toString(16).padStart(16,'0');
}

export function createSkinBindingSource(input){
 stringifyStrictJson(input,{maxBytes:MAX_BYTES});
 exact(input,['version','kind','name','units','axes','space','target','fingerprint','mesh','influences','joints','restBones','motion'],'skin source');
 if(input.version!==1||input.kind!=='mesh-skin-binding'||input.units!=='m-s-kg'||input.axes!=='right-handed-y-up'||input.space!=='mesh-local-is-skeleton')throw new Error('Unsupported skin source format/space');
 const sourceName=name(input.name,'Skin name');exact(input.target,['objectId','nativeId'],'skin target');
 const objectId=name(input.target.objectId,'Browser object ID',384);if(!objectId||objectId.length>96)throw new Error('Browser object ID length');
 const target={objectId,nativeId:nativeId(input.target.nativeId)};
 exact(input.mesh,['version','positions','triangles'],'skin mesh');
 if(!Array.isArray(input.mesh.positions)||input.mesh.positions.length>2048)throw new Error('Skin source vertex limit 2048');
 const mesh=validateMesh(input.mesh);mesh.triangles=mesh.triangles.map(t=>t.map(index=>index===0?0:index));const fingerprint=meshFingerprint(mesh);
 if(typeof input.fingerprint!=='string'||!/^[0-9a-f]{16}$/.test(input.fingerprint)||input.fingerprint!==fingerprint)throw new Error('Skin mesh fingerprint mismatch');
 const motion=createMotionSource(input.motion),bones=new Map(motion.bones.map(b=>[b.id,b]));
 if(utf8Length(serializeMotionPortable(motion))>MAX_MOTION_BYTES)throw new Error('Skin motion block exceeds 4 MiB');
 if(!Array.isArray(input.joints)||input.joints.length!==bones.size||input.joints.length>128)throw new Error('Skin joint ID set/count');
 const jointIds=new Set(),joints=Array.from(input.joints,j=>{
  exact(j,['id','restWorld','inverseBind'],'skin joint');const id=integer(j.id,1,MAX_ID,'Joint ID');
  if(!bones.has(id)||jointIds.has(id))throw new Error('Unknown/duplicate skin joint ID');jointIds.add(id);
  return {id,restWorld:matrix(j.restWorld,'Rest world'),inverseBind:matrix(j.inverseBind,'Inverse bind')};
 });
 if(!Array.isArray(input.restBones)||input.restBones.length!==bones.size||input.restBones.length>128)throw new Error('Rest snapshot ID set/count');
 const restIds=new Set(),restBones=Array.from(input.restBones,b=>{
  exact(b,['id','parentId','rest'],'rest snapshot');const id=integer(b.id,1,MAX_ID,'Rest ID'),parentId=integer(b.parentId,0,MAX_ID,'Rest parent ID');
  if(!bones.has(id)||restIds.has(id))throw new Error('Unknown/duplicate rest snapshot ID');restIds.add(id);
  exact(b.rest,['position','rotation','scale'],'snapshot local pose');
  const rest={position:vector(b.rest.position,3,'Snapshot position'),rotation:vector(b.rest.rotation,4,'Snapshot rotation'),scale:vector(b.rest.scale,3,'Snapshot scale')};
  const current=bones.get(id);if(parentId!==current.parentId||!samePose(rest,current.rest))throw new Error('Stale local rest/parent snapshot');
  return {id,parentId,rest};
 });
 if(!Array.isArray(input.influences)||input.influences.length!==mesh.positions.length)throw new Error('Skin influence/vertex count mismatch');
 let total=0;
 const influences=Array.from(input.influences,ws=>{
  if(!Array.isArray(ws)||ws.length<1||ws.length>4||(total+=ws.length)>8192)throw new Error('Skin influence limit: 1..4 per vertex, 8192 total');
  const ids=new Set(),out=Array.from(ws,w=>{exact(w,['boneId','weight'],'author influence');const boneId=integer(w.boneId,1,MAX_ID,'Influence ID'),weight=finite(w.weight,'Author weight');if(!bones.has(boneId)||ids.has(boneId)||weight<0)throw new Error('Unknown/duplicate influence ID or negative weight');ids.add(boneId);return {boneId,weight};});
  if(!out.some(w=>w.weight>0))throw new Error('At least one positive author weight is required');return out;
 });
 const source={version:1,kind:'mesh-skin-binding',name:sourceName,units:'m-s-kg',axes:'right-handed-y-up',space:'mesh-local-is-skeleton',target,fingerprint,mesh,influences,joints,restBones,motion};
 // The strict emitter also rejects accessors, sparse/extra array properties and
 // excessive depth/nodes, without replacing authored signed zeros.
 stringifyStrictJson(source,{maxBytes:MAX_BYTES});return source;
}

export const parseSkinBindingSource=text=>createSkinBindingSource(parseStrictJson(text,{maxBytes:MAX_BYTES}));
export const serializeSkinBindingSource=source=>stringifyStrictJson(createSkinBindingSource(source),{maxBytes:MAX_BYTES});

function contextMatch(source,scene){
 const mapped=parsePortableScene(savePortableScene(scene)),entity=mapped.entities.find(e=>e.id===source.target.objectId);
 if(!entity||entity.nativeId!==source.target.nativeId||entity.type!=='mesh')throw new Error('Unknown/mismatched skin target object or native ID');
 const mesh=validateMesh(entity.mesh);
 if(meshFingerprint(mesh)!==source.fingerprint)throw new Error('Context mesh fingerprint mismatch');
 // Mandatory even if the non-cryptographic fingerprints agree. The hash is
 // an index/diagnostic, never evidence of full source geometry identity.
 if(mesh.positions.length!==source.mesh.positions.length||mesh.triangles.length!==source.mesh.triangles.length||!mesh.positions.every((p,j)=>sameVector(p,source.mesh.positions[j]))||!mesh.triangles.every((t,j)=>sameVector(t,source.mesh.triangles[j])))throw new Error('Context full geometry/order mismatch');
 return true;
}
export function validateSkinBindingContext(input,scene){return contextMatch(createSkinBindingSource(input),scene);}

export function setSkinInfluences(input,vertexIndex,influences){
 const source=createSkinBindingSource(input);integer(vertexIndex,0,source.mesh.positions.length-1,'Vertex index');source.influences[vertexIndex]=influences;return createSkinBindingSource(source);
}
export function setSkinWeight(input,vertexIndex,boneId,weight){
 const source=createSkinBindingSource(input);integer(vertexIndex,0,source.mesh.positions.length-1,'Vertex index');integer(boneId,1,MAX_ID,'Influence ID');
 const influence=source.influences[vertexIndex].find(w=>w.boneId===boneId);if(!influence)throw new Error('No existing influence for that bone ID');influence.weight=weight;return createSkinBindingSource(source);
}

export function evaluateSkinBinding(runtime,input,seconds,{loop=false,scene}={}){
 const source=createSkinBindingSource(input);if(scene!==undefined)contextMatch(source,scene);
 if(typeof runtime?.sampleMotion!=='function'||typeof runtime?.deformSkin!=='function')throw new Error('Common C++ skin/motion runtime unavailable');
 const rest=runtime.sampleMotion({bones:source.motion.bones,clip:{...source.motion.clip,tracks:[]}},0);
 if(rest.status!=='completed')throw new Error('Skin rest FK failed: '+rest.status);
 const restById=new Map(rest.bones.map(b=>[b.id,b.worldMatrix]));
 if(restById.size!==source.joints.length||source.joints.some(j=>!restById.has(j.id)||!sameVector(j.restWorld,restById.get(j.id))))throw new Error('Stale C++ rest world matrix');
 const pose=runtime.sampleMotion(source.motion,seconds,{loop});if(pose.status!=='completed')throw new Error('Skin current pose failed: '+pose.status);
 const deformation=runtime.deformSkin({joints:source.joints,pose:pose.bones.map(b=>({id:b.id,matrix:b.worldMatrix})),vertices:source.mesh.positions.map((position,j)=>({position,influences:source.influences[j].map(w=>({id:w.boneId,weight:w.weight}))}))});
 return {rest,pose,deformation};
}

export function defaultSkinBindingSource(runtime){
 if(typeof runtime?.sampleMotion!=='function'||typeof runtime?.bindSkin!=='function')throw new Error('Common C++ skin/motion runtime unavailable');
 const identity={position:[0,0,0],rotation:[0,0,0,1],scale:[1,1,1]},child={...identity,position:[1,0,0]},key=(time,rotation)=>({time,...child,rotation});
 const motion=createMotionSource({version:1,kind:'skeletal-motion',name:'Original arm motion',bones:[{id:19,name:'Child',parentId:7,rest:child},{id:7,name:'Root',parentId:0,rest:identity}],clip:{name:'Bend',duration:2,tracks:[{boneId:19,interpolation:'linear',keys:[key(0,[0,0,0,1]),key(1,[0,0,1,1]),key(2,[0,0,0,1])]}]}});
 const mesh=validateMesh({version:1,positions:[[0,-.2,0],[1,-.2,0],[2,-.2,0],[0,.2,0],[1,.2,0],[2,.2,0]],triangles:[[0,1,4],[0,4,3],[1,2,5],[1,5,4]]});
 const rest=runtime.sampleMotion({bones:motion.bones,clip:{...motion.clip,tracks:[]}},0);if(rest.status!=='completed')throw new Error('Default rest FK failed: '+rest.status);
 const binding=runtime.bindSkin(rest.bones.map(b=>({id:b.id,matrix:b.worldMatrix})));if(binding.status!=='completed')throw new Error('Default inverse bind failed: '+binding.status);
 return createSkinBindingSource({version:1,kind:'mesh-skin-binding',name:'Original arm binding',units:'m-s-kg',axes:'right-handed-y-up',space:'mesh-local-is-skeleton',target:{objectId:'arm-mesh',nativeId:'42'},fingerprint:meshFingerprint(mesh),mesh,influences:mesh.positions.map((_,j)=>j%3===0?[{boneId:7,weight:1}]:j%3===1?[{boneId:19,weight:1},{boneId:7,weight:1}]:[{boneId:19,weight:1}]),joints:binding.joints,restBones:motion.bones.map(({id,parentId,rest})=>({id,parentId,rest})),motion});
}

export function serializeSkinBindingPortable(input){
 const source=createSkinBindingSource(input),m=source.mesh,values=a=>a.map(decimal).join(' ');
 const rows=['pikapika_skin 1','name '+quoted(source.name),'object '+quoted(source.target.objectId)+' '+quoted(source.target.nativeId),'space mesh-local-is-skeleton','fingerprint '+source.fingerprint,`mesh ${m.positions.length} ${m.triangles.length}`];
 for(const p of m.positions)rows.push('vertex '+values(p));for(const t of m.triangles)rows.push('triangle '+values(t));rows.push('influences '+source.influences.length);
 for(const ws of source.influences)rows.push('weights '+ws.length+' '+ws.map(w=>w.boneId+' '+decimal(w.weight)).join(' '));
 rows.push('joints '+source.joints.length);for(const j of source.joints)rows.push('joint '+j.id+' '+values(j.restWorld)+' '+values(j.inverseBind));
 rows.push('rest_bones '+source.restBones.length);for(const b of source.restBones)rows.push('rest_bone '+b.id+' '+b.parentId+' '+values([...b.rest.position,...b.rest.rotation,...b.rest.scale]));
 const motion=serializeMotionPortable(source.motion);rows.push('motion_bytes '+utf8Length(motion));const output=rows.join('\n')+'\n'+motion+'end_skin\n';
 if(utf8Length(output)>MAX_BYTES)throw new Error('Portable skin source exceeds 8 MiB');return output;
}

function tokens(line){
 const result=[];let at=0;
 while(at<line.length){while(line[at]===' '||line[at]==='\t'||line[at]==='\r')++at;if(at===line.length)break;
  const start=at;let isQuoted=false,value='';
  if(line[at]==='"'){isQuoted=true;++at;let closed=false;while(at<line.length){const c=line[at++];if(c==='"'){closed=true;break;}if(c==='\\'){const d=line[at++];if(d!=='"'&&d!=='\\')throw new Error('Invalid portable skin quote escape');value+=d;}else value+=c;}if(!closed)throw new Error('Truncated portable skin quote');if(at<line.length&&line[at]!==' '&&line[at]!=='\t'&&line[at]!=='\r')throw new Error('Trailing quoted skin token');}
  else{while(at<line.length&&line[at]!==' '&&line[at]!=='\t'&&line[at]!=='\r')++at;value=line.slice(start,at);}
  result.push({value,quoted:isQuoted});
 }return result;
}
function embeddedMotionWhitespace(text){
 // Existing standalone motion parsing accepts JavaScript whitespace. This
 // sidecar's native reader uses classic ASCII whitespace instead. Preserve
 // literal Unicode whitespace in quoted names, but reject it as a separator.
 let quoted=false,escaped=false;
 for(const c of text){
  if(quoted){if(escaped){escaped=false;continue;}if(c==='\\'){escaped=true;continue;}if(c==='"')quoted=false;}
  else if(c==='"')quoted=true;
  else if(c.codePointAt(0)>127&&/\s/u.test(c))throw new Error('Non-ASCII whitespace outside embedded motion name');
 }
 return text;
}
export function parseSkinBindingPortable(text){
 if(typeof text!=='string'||utf8Length(text)>MAX_BYTES)throw new Error('Portable skin source exceeds 8 MiB');
 const bytes=new TextEncoder().encode(text),decoder=new TextDecoder('utf-8',{fatal:true,ignoreBOM:true});let at=0;
 const line=()=>{if(at>=bytes.length)throw new Error('Truncated portable skin source');const start=at;while(at<bytes.length&&bytes[at]!==10){if(at-start>=4096)throw new Error('Portable skin line exceeds 4096 bytes');++at;}let end=at;if(at<bytes.length)++at;if(bytes[end-1]===13)--end;return decoder.decode(bytes.subarray(start,end));};
 const row=(tag,n)=>{const t=tokens(line());if(t.length!==n+1||t[0].quoted||t[0].value!==tag)throw new Error('Invalid portable skin '+tag+' row');return t.slice(1);};
 const word=t=>{if(t.quoted)throw new Error('Quoted portable skin numeric/token');return t.value;};
 const string=t=>{if(!t.quoted)throw new Error('Portable skin name must be quoted');return t.value;};
 const number=t=>{const s=word(t);if(!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(s))throw new Error('Invalid portable skin decimal');const n=finite(Number(s),'Portable decimal');if(n===0&&/[1-9]/.test(s.split(/[eE]/)[0]))throw new Error('Portable skin decimal underflow');return n;};
 const count=(t,lo,hi,label)=>integer(number(t),lo,hi,label),nums=t=>t.map(number);
 if(number(row('pikapika_skin',1)[0])!==1)throw new Error('Unsupported portable skin version');
 const sourceName=string(row('name',1)[0]),object=row('object',2),target={objectId:string(object[0]),nativeId:string(object[1])};
 if(word(row('space',1)[0])!=='mesh-local-is-skeleton')throw new Error('Unsupported portable skin space');
 const fingerprint=word(row('fingerprint',1)[0]),shape=row('mesh',2),nv=count(shape[0],3,2048,'Skin vertices'),nt=count(shape[1],1,131072,'Skin triangles');
 const mesh={version:1,positions:[],triangles:[]};for(let j=0;j<nv;++j)mesh.positions.push(nums(row('vertex',3)));for(let j=0;j<nt;++j)mesh.triangles.push(nums(row('triangle',3)));
 if(count(row('influences',1)[0],3,2048,'Influence vertices')!==nv)throw new Error('Portable skin influence/vertex count');
 const influences=[];let total=0;for(let j=0;j<nv;++j){const ws=tokens(line());if(ws[0]?.quoted||ws[0]?.value!=='weights'||ws.length<2)throw new Error('Invalid portable weights row');const n=count(ws[1],1,4,'Vertex influences');if(ws.length!==2+2*n||(total+=n)>8192)throw new Error('Portable skin total influence count');influences.push(Array.from({length:n},(_,k)=>({boneId:number(ws[2+2*k]),weight:number(ws[3+2*k])})));}
 const nj=count(row('joints',1)[0],1,128,'Skin joints'),joints=[];for(let j=0;j<nj;++j){const v=nums(row('joint',33));joints.push({id:v[0],restWorld:v.slice(1,17),inverseBind:v.slice(17,33)});}
 const nb=count(row('rest_bones',1)[0],1,128,'Rest bones'),restBones=[];for(let j=0;j<nb;++j){const v=nums(row('rest_bone',12));restBones.push({id:v[0],parentId:v[1],rest:{position:v.slice(2,5),rotation:v.slice(5,9),scale:v.slice(9,12)}});}
 const length=count(row('motion_bytes',1)[0],1,MAX_MOTION_BYTES,'Motion bytes');if(length>bytes.length-at||bytes[at+length-1]!==10)throw new Error('Portable skin motion byte boundary/terminal LF');
 const motion=parseMotionPortable(embeddedMotionWhitespace(decoder.decode(bytes.subarray(at,at+length))));at+=length;
 row('end_skin',0);if(at!==bytes.length)throw new Error('Trailing portable skin data');
 return createSkinBindingSource({version:1,kind:'mesh-skin-binding',name:sourceName,units:'m-s-kg',axes:'right-handed-y-up',space:'mesh-local-is-skeleton',target,fingerprint,mesh,influences,joints,restBones,motion});
}

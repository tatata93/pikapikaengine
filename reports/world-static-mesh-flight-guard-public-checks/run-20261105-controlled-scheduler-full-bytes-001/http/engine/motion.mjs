// Authored motion data and edits. Pose interpolation/FK run in the common C++ core.
const kind='skeletal-motion',maxId=Number.MAX_SAFE_INTEGER;
const exactKeys=(value,names,label)=>{if(!value||typeof value!=='object'||Array.isArray(value)||Object.keys(value).some(k=>!names.includes(k)))throw new Error(`Unknown ${label} field`);};
const finite=(x,label)=>{if(typeof x!=='number'||!Number.isFinite(x))throw new Error(`${label} must be finite`);return x===0?0:x;};
const integer=(x,lo,hi,label)=>{x=finite(x,label);if(!Number.isInteger(x)||x<lo||x>hi)throw new Error(`${label} outside ${lo}..${hi}`);return x;};
const vector=(v,n,label,lo,hi)=>{if(!Array.isArray(v)||v.length!==n)throw new Error(`${label} requires ${n} numbers`);return Array.from(v,x=>{x=finite(x,label);if(x<lo||x>hi)throw new Error(`${label} numeric range exceeded`);return x;});};
function name(value,label){
 if(typeof value!=='string'||new TextEncoder().encode(value).length>256||/[\u0000-\u001f\u007f]/u.test(value))throw new Error(`${label} must be printable UTF-8 within 256 bytes`);
 for(let j=0;j<value.length;++j){const c=value.charCodeAt(j);if(c>=0xd800&&c<=0xdbff){const d=value.charCodeAt(++j);if(!(d>=0xdc00&&d<=0xdfff))throw new Error(`${label} has unpaired surrogate`);}else if(c>=0xdc00&&c<=0xdfff)throw new Error(`${label} has unpaired surrogate`);}
 return value;
}
function pose(value,label){
 exactKeys(value,['position','rotation','scale'],label);
 const position=vector(value.position,3,label+' position',-1e6,1e6),rotation=vector(value.rotation,4,label+' rotation',-1e300,1e300),scale=vector(value.scale,3,label+' scale',1e-6,1e6);
 if(rotation.every(x=>x===0))throw new Error(`${label} quaternion is zero`);
 return {position,rotation,scale};
}
export function createMotionSource(input){
 exactKeys(input,['version','kind','name','bones','clip'],'motion source');
 if(input.version!==1||input.kind!==kind)throw new Error('Unsupported motion source version/kind');
 const sourceName=name(input.name,'Motion name');
 if(!Array.isArray(input.bones)||input.bones.length<1||input.bones.length>128)throw new Error('Motion requires 1..128 bones');
 const ids=new Map(),bones=Array.from(input.bones,b=>{exactKeys(b,['id','name','parentId','rest'],'bone');const id=integer(b.id,1,maxId,'Bone ID'),parentId=integer(b.parentId,0,maxId,'Parent ID');if(ids.has(id))throw new Error('Duplicate bone ID');ids.set(id,parentId);return {id,name:name(b.name,'Bone name'),parentId,rest:pose(b.rest,'Rest pose')};});
 if(bones.filter(b=>b.parentId===0).length!==1)throw new Error('Motion requires exactly one root');
 for(const b of bones){const visited=new Set();let current=b.id;while(current!==0){if(visited.has(current))throw new Error('Bone parent cycle');visited.add(current);if(!ids.has(current))throw new Error('Missing parent bone');current=ids.get(current);}}
 exactKeys(input.clip,['name','duration','tracks'],'clip');const duration=finite(input.clip.duration,'Clip duration');if(duration<=0||duration>1e9)throw new Error('Clip duration outside (0,1e9] seconds');
 if(!Array.isArray(input.clip.tracks)||input.clip.tracks.length>128)throw new Error('Motion supports at most 128 tracks');
 const targets=new Set();let totalKeys=0;
 const tracks=Array.from(input.clip.tracks,t=>{exactKeys(t,['boneId','interpolation','keys'],'track');const boneId=integer(t.boneId,1,maxId,'Track bone ID');if(!ids.has(boneId)||targets.has(boneId))throw new Error('Unknown or duplicate track bone');targets.add(boneId);
  if(!['linear','step'].includes(t.interpolation))throw new Error('Track interpolation requires linear or step');
  if(!Array.isArray(t.keys)||t.keys.length<1||totalKeys+t.keys.length>4096)throw new Error('Tracks require keys, at most 4096 in total');totalKeys+=t.keys.length;let previous=-1;
  const keys=Array.from(t.keys,k=>{exactKeys(k,['time','position','rotation','scale'],'key');const time=finite(k.time,'Key time');if(time<0||time>duration||time<=previous)throw new Error('Key times must strictly increase within clip duration');previous=time;return {time,...pose({position:k.position,rotation:k.rotation,scale:k.scale},'Key pose')};});
  return {boneId,interpolation:t.interpolation,keys};
 });
 return {version:1,kind,name:sourceName,bones,clip:{name:name(input.clip.name,'Clip name'),duration,tracks}};
}
export function defaultMotionSource(){
 const rest=position=>({position,rotation:[0,0,0,1],scale:[1,1,1]});
 const key=(time,position,rotation)=>({time,position,rotation,scale:[1,1,1]});
 return createMotionSource({version:1,kind,name:'Original two-link arm',bones:[{id:1,name:'Root',parentId:0,rest:rest([0,0,0])},{id:2,name:'Upper',parentId:1,rest:rest([0,1,0])},{id:3,name:'Forearm',parentId:2,rest:rest([1,0,0])},{id:4,name:'Tip',parentId:3,rest:rest([1,0,0])}],clip:{name:'Reach',duration:2,tracks:[{boneId:2,interpolation:'linear',keys:[key(0,[0,1,0],[0,0,0,1]),key(1,[0,1,0],[0,0,1,1]),key(2,[0,1,0],[0,0,0,1])]},{boneId:3,interpolation:'linear',keys:[key(0,[1,0,0],[0,0,0,1]),key(1,[1,0,0],[0,0,-1,1]),key(2,[1,0,0],[0,0,0,1])]}]}});
}
export const serializeMotionSource=source=>JSON.stringify(createMotionSource(source),null,2)+'\n';
export const parseMotionSource=text=>{if(typeof text!=='string'||text.length>4*1024*1024)throw new Error('Motion JSON exceeds text budget');return createMotionSource(JSON.parse(text));};
export function setMotionKey(input,{boneId,time,position,rotation,scale}){
 const source=createMotionSource(input);if(!source.bones.some(b=>b.id===boneId))throw new Error('Unknown key bone');
 const key={time,position,rotation,scale};let track=source.clip.tracks.find(t=>t.boneId===boneId);if(!track){track={boneId,interpolation:'linear',keys:[]};source.clip.tracks.push(track);}
 const index=track.keys.findIndex(k=>k.time===time);if(index<0)track.keys.push(key);else track.keys[index]=key;track.keys.sort((a,b)=>a.time-b.time);return createMotionSource(source);
}
export function removeMotionKey(input,boneId,time){
 const source=createMotionSource(input);integer(boneId,1,maxId,'Key bone');finite(time,'Key time');const track=source.clip.tracks.find(t=>t.boneId===boneId);
 if(!source.bones.some(b=>b.id===boneId)||!track||!track.keys.some(k=>k.time===time))throw new Error('No such key');
 track.keys=track.keys.filter(k=>k.time!==time);if(!track.keys.length)source.clip.tracks=source.clip.tracks.filter(t=>t!==track);return createMotionSource(source);
}
export function sampleMotion(runtime,input,seconds,options={}){
 if(typeof runtime?.sampleMotion!=='function')throw new Error('Common C++ motion API unavailable; load matching WASM');
 return runtime.sampleMotion(createMotionSource(input),seconds,options);
}
// Original portable text v1. Decimal numbers round-trip binary64; names are UTF-8
// quoted strings with quote/backslash escaping. This is not a glTF file format.
export function serializeMotionPortable(input){
 const s=createMotionSource(input),rows=['pikapika_motion 1','name '+JSON.stringify(s.name),'bones '+s.bones.length];
 const values=p=>[...p.position,...p.rotation,...p.scale].map(String).join(' ');
 for(const b of s.bones)rows.push(`bone ${b.id} ${b.parentId} ${JSON.stringify(b.name)} ${values(b.rest)}`);
 rows.push(`clip ${JSON.stringify(s.clip.name)} ${s.clip.duration} ${s.clip.tracks.length}`);
 for(const t of s.clip.tracks){rows.push(`track ${t.boneId} ${t.interpolation} ${t.keys.length}`);for(const k of t.keys)rows.push(`key ${k.time} ${values(k)}`);}
 return rows.join('\n')+'\nend\n';
}
export function parseMotionPortable(text){
 if(typeof text!=='string'||text.length>4*1024*1024)throw new Error('Portable motion exceeds text budget');
 const tokens=text.match(/"(?:\\["\\]|[^"\\\r\n])*"|[^\s]+/gu)??[];let index=0;
 const take=()=>{if(index>=tokens.length)throw new Error('Truncated portable motion');return tokens[index++];};
 const expect=t=>{if(take()!==t)throw new Error('Invalid portable motion token '+t);};
 const number=()=>{const t=take();if(!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(t))throw new Error('Invalid portable decimal');const n=finite(Number(t),'Portable decimal');if(n===0&&/[1-9]/.test(t.split(/[eE]/)[0]))throw new Error('Portable decimal underflow');return n;};
 const count=(max,label)=>integer(number(),0,max,label),string=()=>{const token=take();if(!/^"(?:\\["\\]|[^"\\\r\n])*"$/u.test(token))throw new Error('Invalid portable quoted name');return name(JSON.parse(token),'Portable name');};
 const transform=()=>({position:[number(),number(),number()],rotation:[number(),number(),number(),number()],scale:[number(),number(),number()]});
 expect('pikapika_motion');if(number()!==1)throw new Error('Unsupported portable motion version');expect('name');const sourceName=string();expect('bones');const n=count(128,'Bone count'),bones=[];
 for(let j=0;j<n;++j){expect('bone');const id=number(),parentId=number(),boneName=string();bones.push({id,parentId,name:boneName,rest:transform()});}
 expect('clip');const clipName=string(),duration=number(),nt=count(128,'Track count'),tracks=[];let total=0;
 for(let j=0;j<nt;++j){expect('track');const boneId=number(),interpolation=take(),nk=count(4096,'Key count');if((total+=nk)>4096)throw new Error('Portable key budget exceeded');const keys=[];for(let k=0;k<nk;++k){expect('key');keys.push({time:number(),...transform()});}tracks.push({boneId,interpolation,keys});}
 expect('end');if(index!==tokens.length)throw new Error('Trailing portable motion data');return createMotionSource({version:1,kind,name:sourceName,bones,clip:{name:clipName,duration,tracks}});
}

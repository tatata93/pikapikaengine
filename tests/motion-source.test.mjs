import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,readFileSync,writeFileSync,rmSync,existsSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,resolve,dirname,basename} from 'node:path';
import {spawnSync} from 'node:child_process';
import {createMotionSource,defaultMotionSource,serializeMotionSource,parseMotionSource,setMotionKey,removeMotionKey,sampleMotion,serializeMotionPortable,parseMotionPortable} from '../engine/motion.mjs';
const copy=x=>JSON.parse(JSON.stringify(x));
const change=fn=>{const source=defaultMotionSource();fn(source);return source;};
const close=(a,b)=>assert.ok(Math.abs(a-b)<=2e-12*Math.max(1,Math.abs(b)),`${a} != ${b}`);
const freeze=x=>{if(x&&typeof x==='object'){Object.freeze(x);for(const v of Object.values(x))freeze(v);}return x;};

test('strict source schema rejects sparse data, wrong fields, invalid tree graphs and ambiguous key times',()=>{
  const mutations=[s=>{s.extra=1;},s=>{s.bones[0].extra=1;},s=>{s.bones[0].rest.extra=1;},s=>{s.clip.extra=1;},s=>{s.clip.tracks[0].extra=1;},s=>{s.clip.tracks[0].keys[0].extra=1;},s=>{delete s.clip.name;},s=>{s.version=2;},s=>{s.bones=[];},s=>{s.bones[1].id=1;},s=>{s.bones[0].id=0;},s=>{s.bones[1].id=Number.MAX_SAFE_INTEGER+1;},s=>{s.bones[1].id=2.5;},s=>{s.bones[1].parentId=99;},s=>{s.bones[1].parentId=0;},s=>{s.bones[1].parentId=3;s.bones[2].parentId=2;},s=>{s.bones[1].parentId=2;},s=>{s.clip.tracks.push(copy(s.clip.tracks[0]));},s=>{s.clip.tracks[0].boneId=99;},s=>{s.clip.tracks[0].keys=[];},s=>{s.clip.tracks[0].keys[1].time=0;},s=>{s.clip.tracks[0].keys.reverse();},s=>{s.clip.tracks[0].keys[2].time=3;},s=>{s.clip.duration=0;},s=>{s.bones[0].rest.position[0]=Infinity;},s=>{s.bones[0].rest.scale[1]=0;},s=>{s.bones[0].rest.rotation=[0,0,0,0];},s=>{s.clip.tracks=Array(1);},s=>{s.clip.tracks[0].keys=Array(1);},s=>{s.bones[0].rest.position=Array(3);},s=>{s.bones[0].rest.rotation=Array(4);},s=>{s.bones[0].rest.scale=Array(3);}];
  mutations.forEach((mutate,i)=>assert.throws(()=>createMotionSource(change(mutate)),`mutation ${i}`));
  const permuted=change(s=>{s.bones=[s.bones[3],s.bones[1],s.bones[0],s.bones[2]];});assert.deepEqual(createMotionSource(permuted).bones.map(b=>b.id),[4,2,1,3]);
  const max=change(s=>{s.bones[3].id=Number.MAX_SAFE_INTEGER;});assert.equal(createMotionSource(max).bones[3].id,Number.MAX_SAFE_INTEGER);
});

test('motion names validate UTF-8 byte boundaries, paired scalars and controls at every name location',()=>{
  for(const accepted of ['é'.repeat(128),'😀'.repeat(64),'日本語の原本 \\ "quoted"','']){
    const source=change(s=>{s.name=accepted;s.clip.name=accepted;s.bones[0].name=accepted;});assert.deepEqual(parseMotionSource(serializeMotionSource(source)),source);assert.deepEqual(parseMotionPortable(serializeMotionPortable(source)),source);
  }
  for(const invalid of ['é'.repeat(128)+'a','😀'.repeat(64)+'a','x\u0000y','x\u001fy','x\u007fy','\ud800','\udc00','\ud800x'])for(const field of ['name','clip','bone'])assert.throws(()=>createMotionSource(change(s=>{if(field==='name')s.name=invalid;else if(field==='clip')s.clip.name=invalid;else s.bones[0].name=invalid;})),field);
});

test('negative zero alone is canonicalized while quaternion signs magnitudes IDs and all source order remain authored',()=>{
  const raw=defaultMotionSource();raw.bones[0].parentId=-0;raw.bones[0].rest.position=[-0,Number.MIN_VALUE,-Number.MIN_VALUE];raw.bones[0].rest.rotation=[-0,-2,3,-4];raw.clip.tracks[0].keys[0].time=-0;raw.clip.tracks[0].keys[0].rotation=[-0,0,-3,-5];const before=structuredClone(raw),source=createMotionSource(raw);
  assert.equal(Object.is(raw.bones[0].rest.position[0],-0),true);assert.deepEqual(raw,before);assert.equal(Object.is(source.bones[0].parentId,-0),false);assert.equal(Object.is(source.bones[0].rest.position[0],-0),false);assert.equal(Object.is(source.bones[0].rest.rotation[0],-0),false);assert.equal(Object.is(source.clip.tracks[0].keys[0].time,-0),false);assert.deepEqual(source.bones[0].rest.rotation,[0,-2,3,-4]);assert.deepEqual(source.clip.tracks[0].keys[0].rotation,[0,0,-3,-5]);assert.deepEqual(parseMotionPortable(serializeMotionPortable(source)),source);
});

test('portable decimals retain binary64 extrema and reject underflow overflow hex junk and unsupported name escapes',()=>{
  const source=change(s=>{s.name='原本 "quotes" \\ path';s.bones[0].rest.position=[Number.MIN_VALUE,-Number.MIN_VALUE,1e6];s.bones[0].rest.rotation=[1e-300,0,0,-1e300];s.bones[0].rest.scale=[1e-6,1,1e6];s.clip.tracks[0].keys.splice(1,0,{...copy(s.clip.tracks[0].keys[0]),time:Number.MIN_VALUE});});
  assert.deepEqual(parseMotionPortable(serializeMotionPortable(source)),source);
  const base=serializeMotionPortable(defaultMotionSource()),firstPosition=token=>base.replace(/^(bone \S+ \S+ "(?:\\["\\]|[^"\\])*" )\S+/m,(_m,prefix)=>prefix+token);
  for(const token of ['0x10','NaN','Infinity','1e999','1e-999','1e','1.25junk'])assert.throws(()=>parseMotionPortable(firstPosition(token)),token);
  for(const [token,value]of [['+.5',.5],['1.25e+2',125],['-0',0],['5e-324',Number.MIN_VALUE]])assert.equal(parseMotionPortable(firstPosition(token)).bones[0].rest.position[0],value);
  for(const escaped of ['"\\u0041"','"A\\/B"'])assert.throws(()=>parseMotionPortable(base.replace('"Original two-link arm"',escaped)),escaped);
  assert.throws(()=>parseMotionPortable(base+'junk'));assert.throws(()=>parseMotionPortable(base.replace(/end\s*$/,'')));assert.throws(()=>parseMotionSource('null'));
});

test('immutable upsert and exact-time removal preserve other IDs keys rest poses and remove the final track',()=>{
  const original=freeze(defaultMotionSource()),before=serializeMotionSource(original),key={boneId:2,time:1,position:[0,1.25,0],rotation:[0,0,-10,-10],scale:[1,2,1]},updated=setMotionKey(original,key);
  assert.equal(serializeMotionSource(original),before);assert.equal(updated.clip.tracks[0].keys.length,3);assert.deepEqual(updated.clip.tracks[1],original.clip.tracks[1]);assert.deepEqual(updated.bones,original.bones);assert.deepEqual(updated.clip.tracks[0].keys[0],original.clip.tracks[0].keys[0]);assert.deepEqual(updated.clip.tracks[0].keys[2],original.clip.tracks[0].keys[2]);assert.deepEqual(updated.clip.tracks[0].keys[1].rotation,[0,0,-10,-10]);
  const adjacent=setMotionKey(updated,{...key,time:1+Number.EPSILON}),removed=removeMotionKey(adjacent,2,1);assert.deepEqual(removed.clip.tracks[0].keys.map(k=>k.time),[0,1+Number.EPSILON,2]);
  const added=setMotionKey(original,{...key,boneId:4,time:.75}),back=removeMotionKey(added,4,.75);assert.deepEqual(back,original);assert.equal(added.clip.tracks.find(t=>t.boneId===4).interpolation,'linear');
  assert.throws(()=>setMotionKey(original,{...key,boneId:99}));assert.throws(()=>removeMotionKey(original,2,.75));assert.equal(serializeMotionSource(original),before);
});

test('source sampling wrapper forwards the validated full original and returns only the common runtime result',()=>{
  const source=defaultMotionSource(),packet={status:'test marker'},calls=[],runtime={sampleMotion(...args){calls.push(args);return packet;}};assert.strictEqual(sampleMotion(runtime,source,.125,{loop:true}),packet);assert.deepEqual(calls[0],[source,.125,{loop:true}]);assert.notStrictEqual(calls[0][0],source);assert.throws(()=>sampleMotion({},source,0),/API unavailable/);assert.equal(calls.length,1);
});

const nativeCli=resolve(process.env.PIKAPIKA_MOTION_CLI??(process.platform==='win32'?'build/native/Release/pikapika-motion.exe':'build/ci/pikapika-motion'));
function cli(args){assert.ok(existsSync(nativeCli),'Build the pikapika-motion native target before this integration test');const result=spawnSync(nativeCli,args,{encoding:'utf8',windowsHide:true,timeout:10000,maxBuffer:2*1024*1024});assert.ifError(result.error);return result;}
function success(args){const result=cli(args);assert.equal(result.status,0,result.stderr);return result;}
function withFiles(run){const root=resolve(tmpdir()),directory=mkdtempSync(join(root,'pikapika-motion-source-'));try{return run(directory);}finally{const target=resolve(directory);assert.equal(dirname(target),root);assert.ok(basename(target).startsWith('pikapika-motion-source-'));rmSync(target,{recursive:true,force:true});}}
const readSource=path=>parseMotionPortable(readFileSync(path,'utf8'));

test('native CLI init to JS parse export to native roundtrip preserves source and independently known FK',()=>withFiles(directory=>{
  const native=join(directory,'native.motion'),js=join(directory,'js.motion'),round=join(directory,'round.motion');success(['init',native]);assert.deepEqual(readSource(native),defaultMotionSource());
  const source=readSource(native);source.name='JS "原本" \\ verified';source.clip.name='😀'.repeat(64);source.bones[3].id=Number.MAX_SAFE_INTEGER;source.bones[3].name='é'.repeat(128);source.bones=[source.bones[3],source.bones[2],source.bones[0],source.bones[1]];source.bones.find(b=>b.id===1).rest.position[2]=Number.MIN_VALUE;writeFileSync(js,serializeMotionPortable(source));success(['roundtrip',js,round]);assert.deepEqual(readSource(round),createMotionSource(source));assert.deepEqual(parseMotionSource(serializeMotionSource(readSource(round))),createMotionSource(source));
  const at=time=>JSON.parse(success(['sample',native,String(time)]).stdout);for(const [time,expected]of [[0,[2,1,0]],[1,[1,2,0]]]){const pose=at(time);assert.equal(pose.status,'completed');const tip=pose.bones.find(b=>b.id===4).worldMatrix;expected.forEach((n,i)=>close(tip[12+i],n));assert.deepEqual(pose.evaluationOrder,[1,2,3,4]);}
  const loop=JSON.parse(success(['sample',native,'2','loop']).stdout),clamp=JSON.parse(success(['sample',native,'3','clamp']).stdout);assert.equal(loop.sampledTime,0);assert.equal(clamp.sampledTime,2);
}));

test('native CLI key upsert remove and invalid edits preserve untouched source and named existing output',()=>withFiles(directory=>{
  const input=join(directory,'input.motion'),edited=join(directory,'edited.motion'),removed=join(directory,'removed.motion'),existing=join(directory,'existing.motion');success(['init',input]);const before=readSource(input),inputBytes=readFileSync(input),args=['key',input,'4','.75','1','0','.5','0','0','0','-2','1','1','1',edited];success(args);const added=readSource(edited);assert.deepEqual(added.bones,before.bones);assert.deepEqual(added.clip.tracks.slice(0,2),before.clip.tracks);assert.deepEqual(added.clip.tracks[2].keys[0],{time:.75,position:[1,0,.5],rotation:[0,0,0,-2],scale:[1,1,1]});assert.deepEqual(readFileSync(input),inputBytes);
  const upserted=join(directory,'upserted.motion');success(['key',edited,'2','1','0','1.25','0','0','0','-10','-10','1','2','1',upserted]);const updated=readSource(upserted);assert.equal(updated.clip.tracks[0].keys.length,3);assert.deepEqual(updated.clip.tracks[0].keys[1],{time:1,position:[0,1.25,0],rotation:[0,0,-10,-10],scale:[1,2,1]});assert.deepEqual(updated.clip.tracks.slice(1),added.clip.tracks.slice(1));assert.deepEqual(updated.bones,added.bones);
  success(['remove-key',edited,'4','.75',removed]);assert.deepEqual(readSource(removed),before);
  const sentinel=Buffer.from('Existing named output must remain byte-identical\n\x00\xff','latin1');writeFileSync(existing,sentinel);
  const invalid=[['key',input,'4','.75','1','0','0','0','0','0','0','1','1','1',existing],['key',input,'4','.75','1','0','0','0','0','0','1','0','1','1',existing],['key',input,'99','.75','1','0','0','0','0','0','1','1','1','1',existing],['remove-key',input,'2','.75',existing],['key',input,'4','3','1','0','0','0','0','0','1','1','1','1',existing]];
  for(const args of invalid){const result=cli(args);assert.notEqual(result.status,0,args.join(' '));assert.deepEqual(readFileSync(existing),sentinel);assert.deepEqual(readFileSync(input),inputBytes);}
  const corrupt=join(directory,'corrupt.motion');writeFileSync(corrupt,readFileSync(input,'utf8').replace('"Original two-link arm"','"\\u0041"'));assert.notEqual(cli(['roundtrip',corrupt,existing]).status,0);assert.deepEqual(readFileSync(existing),sentinel);
}));

import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,readFile,writeFile,rm,access} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,relative,isAbsolute,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {validateMesh,createBoxMesh,moveVertex,compileMesh,meshBounds,MESH_LIMITS} from '../engine/mesh.mjs';
import {Scene} from '../engine/scene.mjs';

const triangle=()=>({version:1,positions:[[0,0,0],[2,0,0],[0,3,0]],triangles:[[0,1,2]]});
const close=(a,b,tolerance=1e-6)=>assert.ok(Math.abs(a-b)<=tolerance,`${a} != ${b}`);

test('box source is closed, consistently outward wound, centered and has known volume',()=>{
  const mesh=createBoxMesh([2,4,6]);
  assert.equal(mesh.positions.length,8);assert.equal(mesh.triangles.length,12);
  assert.deepEqual(meshBounds(mesh),{min:[-1,-2,-3],max:[1,2,3],center:[0,0,0],size:[2,4,6]});
  let volume=0;const edges=new Map();
  for(const [a,b,c] of mesh.triangles){
    const p=mesh.positions[a],q=mesh.positions[b],r=mesh.positions[c];
    volume+=(p[0]*(q[1]*r[2]-q[2]*r[1])-p[1]*(q[0]*r[2]-q[2]*r[0])+p[2]*(q[0]*r[1]-q[1]*r[0]))/6;
    for(const [i,j] of [[a,b],[b,c],[c,a]]){
      const key=[Math.min(i,j),Math.max(i,j)].join(':');
      edges.set(key,(edges.get(key)||[]).concat(i<j?1:-1));
    }
  }
  close(volume,48);
  for(const signs of edges.values()){assert.equal(signs.length,2);assert.equal(signs[0]+signs[1],0);}
  const compiled=compileMesh(mesh);
  assert.equal(compiled.length,216);
  const faceNormals=new Set();
  for(let i=0;i<compiled.length;i+=18){
    const n=[...compiled.slice(i+3,i+6)],center=[0,1,2].map(axis=>(compiled[i+axis]+compiled[i+6+axis]+compiled[i+12+axis])/3);
    close(Math.hypot(...n),1);assert.ok(n.reduce((s,v,j)=>s+v*center[j],0)>0);
    faceNormals.add(n.join(','));
  }
  assert.equal(faceNormals.size,6);
});

test('compile produces exact expanded positions and right-handed flat normals',()=>{
  const result=compileMesh(triangle());
  assert.ok(result instanceof Float32Array);
  assert.deepEqual([...result],[0,0,0,0,0,1,2,0,0,0,0,1,0,3,0,0,0,1]);
  const reversed=triangle();reversed.triangles[0]=[0,2,1];
  assert.deepEqual([...compileMesh(reversed).slice(3,6)],[0,0,-1]);
});

test('validation clones source and a vertex edit preserves topology and all other vertices',()=>{
  const mesh=createBoxMesh([2,2,2]),original=structuredClone(mesh),copy=validateMesh(mesh);
  copy.positions[0][0]=99;copy.triangles[0][0]=7;
  assert.deepEqual(mesh,original);
  const edited=moveVertex(mesh,6,[2,3,4]);
  assert.deepEqual(edited.triangles,mesh.triangles);
  assert.deepEqual(edited.positions.filter((_,i)=>i!==6),mesh.positions.filter((_,i)=>i!==6));
  assert.deepEqual(mesh,original);
  assert.deepEqual(meshBounds(edited),{min:[-1,-1,-1],max:[2,3,4],center:[0.5,1,1.5],size:[3,4,5]});
  assert.notDeepEqual([...compileMesh(edited)],[...compileMesh(mesh)]);
});

test('failed vertex edits leave source unchanged and reject invalid index or degeneracy',()=>{
  const mesh=triangle(),original=JSON.stringify(mesh);
  for(const index of [-1,0.5,3,Infinity])assert.throws(()=>moveVertex(mesh,index,[1,1,1]));
  assert.throws(()=>moveVertex(mesh,1,[0,0,0]),/degenerate|Zero-area/i);
  assert.throws(()=>moveVertex(mesh,1,[Infinity,1,1]),/position/);
  assert.equal(JSON.stringify(mesh),original);
});

test('malformed versions, counts, vectors, references and singular triangles are rejected',()=>{
  const corrupt=[null,{}, {...triangle(),version:2}, {...triangle(),positions:[]}, {...triangle(),triangles:[]},
    {...triangle(),positions:new Array(MESH_LIMITS.vertices+1)},
    {...triangle(),triangles:new Array(MESH_LIMITS.triangles+1)},
    {...triangle(),positions:[[NaN,0,0],[2,0,0],[0,3,0]]},
    {...triangle(),positions:[[0,0,0],[Infinity,0,0],[0,3,0]]},
    {...triangle(),positions:[[0,0,0],[1e6+1,0,0],[0,3,0]]},
    {...triangle(),positions:[[0,0,0],[2,0,0],new Array(3)]},
    {...triangle(),positions:[...triangle().positions,,]},
    {...triangle(),triangles:[[0,1,3]]}, {...triangle(),triangles:[[0,1,1.5]]},
    {...triangle(),triangles:[[0,0,2]]}, {...triangle(),triangles:[[0,-1,2]]},
    {...triangle(),triangles:[[0,,2]]}, {...triangle(),triangles:new Array(1)},
    {...triangle(),positions:[[0,0,0],[1,1,1],[2,2,2]]},
    {...triangle(),positions:[[0,0,0],[1e-7,0,0],[0,1e-7,0]]}];
  for(const mesh of corrupt)assert.throws(()=>validateMesh(mesh));
  for(const dimensions of [[0,1,1],[-1,1,1],[1,1],['1',1,1],[1,1,Infinity],[1,1,1e6+1]])assert.throws(()=>createBoxMesh(dimensions));
});

test('triangles that collapse only at Float32 output precision are rejected explicitly',()=>{
  const mesh={version:1,positions:[[1e6,1e6,0],[1e6+0.001,1e6,0],[1e6,1e6+0.001,0]],triangles:[[0,1,2]]};
  // Keep every source coordinate inside the SI bound while retaining the same Float32 collapse.
  for(const p of mesh.positions){p[0]-=1;p[1]-=1;}
  assert.throws(()=>validateMesh(mesh),/Float32/);
  assert.doesNotThrow(()=>validateMesh({...triangle(),positions:[[0,0,0],[1e-5,0,0],[0,1e-5,0]]}));
});

test('Scene source saves and reloads an edited indexed mesh without changing stable identity',()=>{
  const source=createBoxMesh([2,2,2]);
  const scene=new Scene({version:2,units:'m-s-kg',axes:'right-handed-y-up',entities:[
    {id:'authored',type:'mesh',position:[4,2,-8],scale:[2,1,3],yaw:0.25,color:[0.2,0.3,0.4],mesh:source}]});
  scene.edit('authored',{mesh:moveVertex(source,6,[2,3,4])});
  const loaded=Scene.load(scene.save());
  assert.deepEqual(loaded.entities,scene.entities);assert.equal(loaded.entities[0].id,'authored');
  assert.deepEqual(loaded.entities[0].mesh.triangles,source.triangles);
  assert.deepEqual(meshBounds(loaded.entities[0].mesh).size,[3,4,5]);
});

test('CLI creates and edits real mesh source files and does not write rejected edits',async t=>{
  const directory=await mkdtemp(join(tmpdir(),'pikapika-mesh-test-'));
  const resolved=resolve(directory),relativeToTemp=relative(resolve(tmpdir()),resolved);
  assert.ok(relativeToTemp&&!relativeToTemp.startsWith('..')&&!isAbsolute(relativeToTemp));
  t.after(()=>rm(resolved,{recursive:true,force:true}));
  const cli=fileURLToPath(new URL('../tools/author.mjs',import.meta.url));
  const run=args=>spawnSync(process.execPath,[cli,...args],{encoding:'utf8'});
  const input=join(directory,'box.json'),output=join(directory,'edited.json'),invalid=join(directory,'rejected.json');
  let result=run(['mesh-box',input,'2','4','6']);assert.equal(result.status,0,result.stderr);
  let scene=Scene.load(await readFile(input,'utf8'));
  assert.equal(scene.data.version,2);assert.deepEqual(meshBounds(scene.entities[0].mesh).size,[2,4,6]);
  // Verify unrelated nodes and their stable IDs survive the command path too.
  scene.add({id:'camera-original',type:'camera',position:[4,5,6],scale:[1,1,1],yaw:0,color:[0,0,0]});
  await writeFile(input,scene.save(),'utf8');
  result=run(['mesh-vertex',input,'mesh-1','6','2','3','4',output]);assert.equal(result.status,0,result.stderr);
  const edited=Scene.load(await readFile(output,'utf8'));
  assert.deepEqual(edited.entities.map(e=>e.id),['mesh-1','camera-original']);
  assert.deepEqual(edited.entities[0].mesh.positions[6],[2,3,4]);
  assert.deepEqual(edited.entities[0].mesh.triangles,scene.entities[0].mesh.triangles);
  assert.deepEqual(edited.entities[1],scene.entities[1]);
  result=run(['mesh-vertex',input,'mesh-1','0','1','-2','-3',invalid]);assert.notEqual(result.status,0);await assert.rejects(access(invalid));
  assert.equal(run(['mesh-box',invalid,'NaN','1','1']).status,1);
  assert.match(run(['help']).stdout,/mesh-vertex/);
  assert.notEqual(run(['unknown']).status,0);
});

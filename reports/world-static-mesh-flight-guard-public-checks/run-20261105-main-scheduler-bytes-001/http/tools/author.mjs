import {readFile,writeFile,stat} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import {Scene} from '../engine/scene.mjs';
import {createBoxMesh,moveVertex,meshBounds} from '../engine/mesh.mjs';

export const help=`pikapikaengine source mesh authoring (SI metres, right-handed, +Y up)
Usage:
  node tools/author.mjs help
  node tools/author.mjs mesh-box output.scene.json [width height depth]
  node tools/author.mjs mesh-vertex input.scene.json id index x y z output.scene.json

mesh-box creates an indexed box as mesh-1 in a version 2 source scene.
mesh-vertex edits one local-space vertex through the shared mesh and Scene APIs.
Stable IDs, triangle indices and unaffected scene data are retained.
Output files are written only after validating the full edit. Existing output paths are replaced.
Collision is a derived conservative world AABB, not exact triangle collision.
`;

const number=value=>{
  if(typeof value!=='string'||!value.trim()||!Number.isFinite(Number(value)))throw new Error(`Invalid finite number: ${value}`);
  return Number(value);
};

export async function runAuthor(args) {
  const [command,...rest]=args;
  if(!command||command==='help'||command==='--help'){return help;}
  if(command==='mesh-box') {
    if(rest.length!==1&&rest.length!==4)throw new Error('mesh-box requires output.scene.json and optionally width height depth');
    const [output,...values]=rest,dimensions=values.length?values.map(number):[1,1,1],mesh=createBoxMesh(dimensions);
    const scene=new Scene({version:2,units:'m-s-kg',axes:'right-handed-y-up',entities:[]});
    scene.add({id:'mesh-1',type:'mesh',position:[0,0,0],scale:[1,1,1],yaw:0,color:[0.3,0.65,0.7],mesh});
    await writeFile(output,scene.save(),'utf8');
    return JSON.stringify({operation:command,output,id:'mesh-1',vertices:mesh.positions.length,triangles:mesh.triangles.length,bounds:meshBounds(mesh)});
  }
  if(command==='mesh-vertex') {
    if(rest.length!==7)throw new Error('mesh-vertex requires input.scene.json id index x y z output.scene.json');
    const [input,id,indexText,x,y,z,output]=rest;
    const file=await stat(input);if(file.size>32*1024*1024)throw new Error('Source scene file limit: 32 MiB');
    const scene=Scene.load(await readFile(input,'utf8')),entity=scene.entities.find(e=>e.id===id);
    if(!entity||entity.type!=='mesh')throw new Error(`Unknown mesh stable ID: ${id}`);
    const mesh=moveVertex(entity.mesh,number(indexText),[x,y,z].map(number));
    scene.edit(id,{mesh});await writeFile(output,scene.save(),'utf8');
    return JSON.stringify({operation:command,output,id,vertex:number(indexText),bounds:meshBounds(mesh)});
  }
  throw new Error(`Unknown authoring command: ${command}. Use help.`);
}

if(process.argv[1]&&pathToFileURL(process.argv[1]).href===import.meta.url) {
  try{console.log(await runAuthor(process.argv.slice(2)));}catch(error){console.error(`author: ${error.message}`);process.exitCode=1;}
}

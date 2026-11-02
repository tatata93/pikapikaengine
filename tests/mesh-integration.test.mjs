import test from 'node:test';
import assert from 'node:assert/strict';
import {Scene,meshEntity} from '../engine/scene.mjs';
import {createBoxMesh,moveVertex} from '../engine/mesh.mjs';
import {deriveCollider,sweepAabb,moveController} from '../engine/physics.mjs';
import {RobotGame} from '../samples/robot.mjs';

test('mesh edits rebuild collision bounds and undo/load restore the actual contact boundary',()=>{
  const scene=new Scene();scene.add(meshEntity('obstacle',createBoxMesh([2,2,2]),[0,3,0]));
  assert.equal(scene.data.version,2);
  const original=deriveCollider(scene.entities[0]);assert.deepEqual(original.scale,[2,2,2]);
  assert.throws(()=>{scene.entities[0].mesh.positions[0][0]=100;},TypeError);
  const rayA=[-5,3,-1.5],rayB=[5,3,-1.5];
  assert.equal(sweepAabb(rayA,rayB,original.position,original.scale),null);
  scene.edit('obstacle',{mesh:moveVertex(scene.entities[0].mesh,0,[-1,-1,-3])});
  const changed=deriveCollider(scene.entities[0]);
  assert.notEqual(changed,original);assert.deepEqual(changed.position,[0,3,-1]);assert.deepEqual(changed.scale,[2,2,4]);
  assert.ok(sweepAabb(rayA,rayB,changed.position,changed.scale)!==null);
  const game=new RobotGame(scene);assert.deepEqual(game.obstacles[0].scale,[2,2,4]);
  const velocity=[10,0,0],moved=moveController(rayA,velocity,1,game.obstacles,.1);assert.ok(moved[0]<-1);
  scene.undo();assert.deepEqual(deriveCollider(scene.entities[0]).scale,[2,2,2]);
  scene.redo();assert.deepEqual(deriveCollider(Scene.load(scene.save()).entities[0]).scale,[2,2,4]);
});
test('world bounds include nonuniform scale and yaw while source remains local metres',()=>{
  const entity=meshEntity('scaled',createBoxMesh([2,4,6]),[10,20,30],[2,3,4],[.2,.3,.4],Math.PI/2);
  const bounds=deriveCollider(entity);for(const [value,expected]of bounds.scale.map((v,i)=>[v,[24,12,4][i]]))assert.ok(Math.abs(value-expected)<1e-10);
  assert.deepEqual(bounds.position,[10,20,30]);assert.equal(bounds.approximation,'conservative-world-aabb');
});
test('v1 files still load and incompatible mesh versions fail without silent migration',()=>{
  assert.equal(new Scene().data.version,1);
  const entity=meshEntity('mesh',createBoxMesh());
  assert.throws(()=>new Scene({version:1,units:'m-s-kg',axes:'right-handed-y-up',entities:[entity]}),/version 2/);
  const scene=new Scene();scene.add(entity);scene.undo();assert.equal(scene.data.version,1);scene.redo();assert.equal(scene.data.version,2);
  assert.throws(()=>scene.edit('mesh',{scale:[1e-100,1,1]}),/transform/);
});

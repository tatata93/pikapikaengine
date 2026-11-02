// Cross-language parity catches drift; analytic tests separately check physics.
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {hydrostaticForces} from '../engine/hydrostatics.mjs';

const root=fileURLToPath(new URL('../',import.meta.url));
const executable=process.argv[2]??(process.platform==='win32'?'build/native/Release/pikapika-buoyancy.exe':'build/ci/pikapika-buoyancy');
const output=execFileSync(path.resolve(root,executable),['--fixtures'],{encoding:'utf8',maxBuffer:16*1024*1024,timeout:30000});
const data=JSON.parse(output);
assert.ok(Array.isArray(data.fixtures)&&data.fixtures.length>0,'Native CLI must produce its complete fixture set');
const names=new Set();let maxRelativeError=0,maxAbsoluteError=0,values=0;
function compare(actual,expected,label){
  if(actual===null||expected===null){assert.equal(actual,expected,label);return;}
  if(Array.isArray(actual)||Array.isArray(expected)){
    assert.ok(Array.isArray(actual)&&Array.isArray(expected),label);assert.equal(actual.length,expected.length,label);
    actual.forEach((value,i)=>compare(value,expected[i],`${label}[${i}]`));return;
  }
  assert.ok(Number.isFinite(actual)&&Number.isFinite(expected),`${label}: finite numerical output`);
  const error=Math.abs(actual-expected),scale=Math.max(Math.abs(actual),Math.abs(expected));
  maxAbsoluteError=Math.max(maxAbsoluteError,error);maxRelativeError=Math.max(maxRelativeError,error/Math.max(1,scale));values++;
  assert.ok(error<=1e-8+1e-11*scale,`${label}: JS=${actual}, native=${expected}, difference=${error}`);
}
for(const fixture of data.fixtures){
  assert.equal(typeof fixture.name,'string');assert.ok(!names.has(fixture.name),'Fixture names must be unique');names.add(fixture.name);
  const result=hydrostaticForces(fixture.mesh,fixture.options);
  for(const key of ['force','torque','wetArea','submergedVolume','centerOfBuoyancy','totalVolume','shells'])compare(result[key],fixture.result[key],`${fixture.name}.${key}`);
}
console.log(JSON.stringify({verification:'JS-native-hydrostatic-parity',fixtures:[...names],numericalValues:values,maxAbsoluteError,maxRelativeError,tolerance:'abs 1e-8 + relative 1e-11; parity is not independent physical validation'},null,2));

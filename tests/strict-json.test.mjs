import test from 'node:test';
import assert from 'node:assert/strict';
import {parseStrictJson, stringifyStrictJson,utf8Length} from '../engine/strict-json.mjs';

test('strict JSON round trips finite binary64 including signed zero and subnormal values',()=>{
 const values=[-0,0,Number.MIN_VALUE,-Number.MIN_VALUE,Number.MAX_VALUE,-Number.MAX_VALUE,Number.MIN_SAFE_INTEGER,Number.MAX_SAFE_INTEGER,1/3,2**-1022,1e-300];
 const encoded=stringifyStrictJson({values,text:'骨🙂 " \\ / \b\f\n\r\t'}),decoded=parseStrictJson(encoded);
 values.forEach((v,j)=>assert.ok(Object.is(v,decoded.values[j])));assert.equal(decoded.text,'骨🙂 " \\ / \b\f\n\r\t');assert.match(encoded,/\[-0,0,/);assert.equal(utf8Length('骨🙂'),7);
 assert.equal(parseStrictJson('-0e-999'),-0);assert.equal(parseStrictJson('0.000e+999'),0);
});
test('strict JSON rejects duplicates after unescaping and keeps prototype keys as data',()=>{
 for(const text of ['{"x":1,"x":2}','{"x":1,"\\u0078":2}','{"a":{"x":1,"x":2}}'])assert.throws(()=>parseStrictJson(text),/Duplicate/);
 const value=parseStrictJson('{"__proto__":{"polluted":true},"constructor":3}');assert.equal(Object.getPrototypeOf(value),Object.prototype);assert.ok(Object.hasOwn(value,'__proto__'));assert.equal(value.polluted,undefined);assert.equal(value.__proto__.polluted,true);assert.equal(value.constructor,3);assert.equal({}.polluted,undefined);assert.equal(stringifyStrictJson(value),'{"__proto__":{"polluted":true},"constructor":3}');
});
test('strict JSON refuses nonfinite rounding and positive or negative decimal underflow',()=>{
 for(const text of ['1e999','-1e999','1e-999','-1e-999','0.0000001e-999','NaN','Infinity','-Infinity'])assert.throws(()=>parseStrictJson(text));
 for(const value of [NaN,Infinity,-Infinity])assert.throws(()=>stringifyStrictJson(value),/Nonfinite/);
 assert.equal(parseStrictJson('5e-324'),Number.MIN_VALUE);assert.equal(parseStrictJson('1.7976931348623157e308'),Number.MAX_VALUE);
});
test('strict JSON rejects malformed grammar and raw or escaped invalid Unicode',()=>{
 const bad=['','\ufeff{}','01','+1','.1','1.','1e','1e+','--1','true false','nullx','[1,]','[,1]','{"a":1,}','{"a" 1}','{"a":1','[1','"x\n"','"\\x"','"\\u000"','"\\ud800"','"\\udc00"','"\ud800"','"\udc00"'];
 for(const text of bad)assert.throws(()=>parseStrictJson(text),undefined,JSON.stringify(text));
 for(const text of ['\ud800','\udc00']){assert.throws(()=>utf8Length(text),/surrogate/);assert.throws(()=>stringifyStrictJson(text),/surrogate/);}
 assert.equal(parseStrictJson('"\\ud83d\\ude42"'),'🙂');assert.deepEqual(parseStrictJson(' \r\n\t[true,false,null] '),[true,false,null]);
});
test('strict JSON text depth and node budgets have exact boundaries',()=>{
 assert.equal(parseStrictJson('"骨"',{maxBytes:5}),'骨');assert.throws(()=>parseStrictJson('"骨"',{maxBytes:4}),/byte/);assert.equal(stringifyStrictJson('骨',{maxBytes:5}),'"骨"');assert.throws(()=>stringifyStrictJson('骨',{maxBytes:4}),/byte/);
 assert.deepEqual(parseStrictJson('[0]',{maxDepth:2,maxNodes:2}),[0]);assert.throws(()=>parseStrictJson('[0]',{maxDepth:1}),/depth/);assert.throws(()=>parseStrictJson('[0]',{maxNodes:1}),/node/);assert.equal(stringifyStrictJson([0],{maxDepth:2,maxNodes:2}),'[0]');assert.throws(()=>stringifyStrictJson([0],{maxDepth:1}),/depth/);assert.throws(()=>stringifyStrictJson([0],{maxNodes:1}),/node/);
 for(const options of [{maxBytes:0},{maxDepth:NaN},{maxNodes:-1},{maxBytes:1.5}]){assert.throws(()=>parseStrictJson('0',options),/budget/);assert.throws(()=>stringifyStrictJson(0,options),/budget/);}
});
test('strict JSON rejects lossy JavaScript values and does not invoke accessors',()=>{
 let called=false;const accessor={get a(){called=true;return 1;}},arrayAccessor=[];Object.defineProperty(arrayAccessor,0,{get(){called=true;return 1;},enumerable:true});
 const circular={};circular.self=circular;const extended=[1];extended.extra=2;const symbol={[Symbol('key')]:1};
 for(const value of [undefined,()=>1,1n,new Date(),[undefined],[,1],circular,extended,symbol,accessor,arrayAccessor])assert.throws(()=>stringifyStrictJson(value));assert.equal(called,false);
 assert.equal(stringifyStrictJson({a:{x:1},b:{x:1}}),'{"a":{"x":1},"b":{"x":1}}');
});

test('strict JSON finite bit corpus agrees with the native JSON decoder without losing any bits',()=>{
 let state=0x91e10da5c79e7b1dn;const view=new DataView(new ArrayBuffer(8)),values=[];
 for(let i=0;i<512;++i){state=BigInt.asUintN(64,state*6364136223846793005n+1442695040888963407n);view.setBigUint64(0,state);const value=view.getFloat64(0);if(Number.isFinite(value))values.push(value);}
 values.push(-0,0,Number.MIN_VALUE,-Number.MIN_VALUE,Number.MAX_VALUE);
 const original={values,nested:[{text:'骨🙂',escaped:'\u0000\t\n"\\'},{empty:{},array:[]}]},text=stringifyStrictJson(original),actual=parseStrictJson(text),native=JSON.parse(text);
 assert.deepEqual(actual,native);assert.deepEqual(actual,original);for(let i=0;i<values.length;++i)assert.ok(Object.is(actual.values[i],values[i]));
 assert.equal(parseStrictJson('{"a":{}}',{maxNodes:3}).a.constructor,Object);assert.throws(()=>parseStrictJson('{"a":{}}',{maxNodes:2}),/node/);assert.equal(stringifyStrictJson({a:{}},{maxNodes:3}),'{"a":{}}');assert.throws(()=>stringifyStrictJson({a:{}},{maxNodes:2}),/node/);
});

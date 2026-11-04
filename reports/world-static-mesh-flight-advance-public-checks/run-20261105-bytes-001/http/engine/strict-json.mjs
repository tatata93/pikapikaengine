// Original bounded JSON codec. Finite binary64 numbers, duplicate-key rejection,
// valid Unicode and signed-zero output are explicit source-format contracts.
const encoder=new TextEncoder();
function unicode(text){
 for(let i=0;i<text.length;++i){const a=text.charCodeAt(i);if(a>=0xd800&&a<=0xdbff){const b=text.charCodeAt(++i);if(!(b>=0xdc00&&b<=0xdfff))throw new Error('Unpaired Unicode surrogate');}else if(a>=0xdc00&&a<=0xdfff)throw new Error('Unpaired Unicode surrogate');}
 return text;
}
export function utf8Length(text){if(typeof text!=='string')throw new Error('Text must be a string');return encoder.encode(unicode(text)).length;}
function limits(options){
 const {maxBytes=8388608,maxDepth=16,maxNodes=1000000}=options??{};
 for(const [key,value] of Object.entries({maxBytes,maxDepth,maxNodes}))if(!Number.isSafeInteger(value)||value<1)throw new Error('Invalid JSON '+key+' budget');
 return {maxBytes,maxDepth,maxNodes};
}
export function parseStrictJson(text,options){
 const budget=limits(options);
 if(typeof text!=='string'||text.length>budget.maxBytes||utf8Length(text)>budget.maxBytes)throw new Error('JSON text byte budget exceeded');
 let at=0,nodes=0;
 const fail=message=>{throw new Error(message+' at JSON offset '+at);};
 const whitespace=()=>{while(at<text.length&&/[\x20\t\r\n]/.test(text[at]))++at;};
 function string(){
  if(text[at++]!=='"')fail('Expected JSON string');let value='';
  while(at<text.length){const c=text[at++];if(c==='"')return unicode(value);if(c.charCodeAt(0)<32)fail('Control character in JSON string');
   if(c!=='\\'){value+=c;continue;}
   if(at>=text.length)fail('Truncated JSON escape');const e=text[at++],escapes={'"':'"','\\':'\\','/':'/','b':'\b','f':'\f','n':'\n','r':'\r','t':'\t'};
   if(Object.hasOwn(escapes,e)){value+=escapes[e];continue;}
   if(e!=='u'||! /^[0-9a-fA-F]{4}$/.test(text.slice(at,at+4)))fail('Invalid JSON escape');
   value+=String.fromCharCode(Number.parseInt(text.slice(at,at+4),16));at+=4;
  }fail('Unterminated JSON string');
 }
 function number(){
  const start=at;if(text[at]==='-')++at;
  if(text[at]==='0')++at;else if(/[1-9]/.test(text[at]??'')){while(/[0-9]/.test(text[at]??''))++at;}else fail('Invalid JSON number');
  if(text[at]==='.'){++at;const first=at;while(/[0-9]/.test(text[at]??''))++at;if(at===first)fail('Missing JSON fractional digits');}
  if(text[at]==='e'||text[at]==='E'){++at;if(text[at]==='+'||text[at]==='-')++at;const first=at;while(/[0-9]/.test(text[at]??''))++at;if(at===first)fail('Missing JSON exponent digits');}
  const token=text.slice(start,at);if(token.length>1024)fail('JSON number token budget exceeded');const value=Number(token);
  if(!Number.isFinite(value))fail('Nonfinite JSON number');
  if(value===0&&/[1-9]/.test(token.split(/[eE]/)[0]))fail('Nonzero JSON number underflow');
  return value;
 }
 function value(depth){
  if(depth>budget.maxDepth)fail('JSON depth budget exceeded');if(++nodes>budget.maxNodes)fail('JSON node budget exceeded');whitespace();const c=text[at];
  if(c==='"')return string();
  if(c==='['){++at;const a=[];whitespace();if(text[at]===']'){++at;return a;}while(true){a.push(value(depth+1));whitespace();if(text[at]===']'){++at;return a;}if(text[at++]!==',')fail('Expected JSON array comma');whitespace();}}
  if(c==='{'){++at;const result={},keys=new Set();whitespace();if(text[at]==='}'){++at;return result;}while(true){if(text[at]!=='"')fail('Expected JSON object key');const key=string();if(keys.has(key))fail('Duplicate JSON key');keys.add(key);if(++nodes>budget.maxNodes)fail('JSON node budget exceeded');whitespace();if(text[at++]!==':')fail('Expected JSON colon');const item=value(depth+1);Object.defineProperty(result,key,{value:item,writable:true,enumerable:true,configurable:true});whitespace();if(text[at]==='}'){++at;return result;}if(text[at++]!==',')fail('Expected JSON object comma');whitespace();}}
  for(const [literal,item] of [['true',true],['false',false],['null',null]])if(text.startsWith(literal,at)){at+=literal.length;return item;}
  if(c==='-'||/[0-9]/.test(c??''))return number();fail('Invalid JSON value');
 }
 const result=value(1);whitespace();if(at!==text.length)fail('Trailing JSON input');return result;
}
export function stringifyStrictJson(input,options){
 const budget=limits(options),chunks=[],ancestors=new Set();let nodes=0,length=0;
 const emit=text=>{length+=text.length;if(length>budget.maxBytes)throw new Error('JSON text byte budget exceeded');chunks.push(text);};
 const quoted=text=>JSON.stringify(unicode(text));
 function value(item,depth){
  if(depth>budget.maxDepth)throw new Error('JSON depth budget exceeded');if(++nodes>budget.maxNodes)throw new Error('JSON node budget exceeded');
  if(item===null){emit('null');return;}if(typeof item==='number'){if(!Number.isFinite(item))throw new Error('Nonfinite JSON number');emit(Object.is(item,-0)?'-0':String(item));return;}
  if(typeof item==='string'){emit(quoted(item));return;}if(typeof item==='boolean'){emit(item?'true':'false');return;}
  if(typeof item!=='object')throw new Error('Unsupported JSON value');if(ancestors.has(item))throw new Error('Cyclic JSON value');
  if(!Array.isArray(item)&&![Object.prototype,null].includes(Object.getPrototypeOf(item)))throw new Error('JSON requires a plain object');
  if(Object.getOwnPropertySymbols(item).some(s=>Object.prototype.propertyIsEnumerable.call(item,s)))throw new Error('JSON symbol key');
  ancestors.add(item);
  if(Array.isArray(item)){
   if(item.length>budget.maxNodes-nodes)throw new Error('JSON node budget exceeded');
   if(Object.keys(item).length!==item.length)throw new Error('Sparse or extended JSON array');emit('[');
   for(let i=0;i<item.length;++i){const descriptor=Object.getOwnPropertyDescriptor(item,String(i));if(!descriptor)throw new Error('Sparse JSON array');if(!Object.hasOwn(descriptor,'value'))throw new Error('JSON accessor property');if(i)emit(',');value(descriptor.value,depth+1);}emit(']');
  }else{
   const keys=Object.keys(item);emit('{');for(let i=0;i<keys.length;++i){const key=keys[i];if(++nodes>budget.maxNodes)throw new Error('JSON node budget exceeded');const descriptor=Object.getOwnPropertyDescriptor(item,key);if(!Object.hasOwn(descriptor,'value'))throw new Error('JSON accessor property');if(i)emit(',');emit(quoted(key));emit(':');value(descriptor.value,depth+1);}emit('}');
  }ancestors.delete(item);
 }
 value(input,1);const result=chunks.join('');if(utf8Length(result)>budget.maxBytes)throw new Error('JSON text byte budget exceeded');return result;
}

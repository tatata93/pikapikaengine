// The same freestanding C++ source is linked into the native engine.
let core=null;
export const getPortableCore=()=>core;
export async function initializePortableCore(bytes=null) {
  if(!bytes){const response=await fetch(new URL('../assets/pikapika-core.wasm',import.meta.url));if(!response.ok)throw new Error(`C++共通コアを読み込めません: HTTP ${response.status}`);bytes=await response.arrayBuffer();}
  if(bytes.byteLength>1024*1024)throw new Error('Portable core exceeds 1 MB limit');
  const {instance}=await WebAssembly.instantiate(bytes,{});
  for(const name of ['pp_sweep_fraction','pp_direct_delay','pp_direct_pressure_gain','pp_integrate_velocity'])if(typeof instance.exports[name]!=='function')throw new Error('Invalid portable core exports');
  core=instance.exports;return core;
}

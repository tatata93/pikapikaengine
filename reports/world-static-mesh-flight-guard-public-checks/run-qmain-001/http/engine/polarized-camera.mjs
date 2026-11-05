// Original finite POWER experiment profile. No radiance/image or continuous
// pupil integration claim: every rounded node is an explicitly launched packet.
export const LENS_POWER_GEOMETRY=Object.freeze({frontRadius:.05,backRadius:-.05,thickness:.005,launchZ:-.01});
export const LENS_POWER_PATHS=Object.freeze(['primary','ghost']);
const kind='synthetic-biconvex-finite-power';
const powers={unpolarized:[0,0,0],q_plus:[1,0,0],q_minus:[-1,0,0],u_plus:[0,1,0],u_minus:[0,-1,0],v_plus:[0,0,1],v_minus:[0,0,-1]};
const keys=(o,names,label)=>{if(!o||typeof o!=='object'||Array.isArray(o)||Object.keys(o).some(k=>!names.includes(k)))throw new Error(`${label}: 未知の項目または不正な形式です`);};
const finite=(x,label)=>{if(typeof x!=='number'||!Number.isFinite(x))throw new Error(`${label}: 有限の数値が必要です`);return x;};
const between=(x,lo,hi,label)=>{finite(x,label);if(x<lo||x>hi)throw new Error(`${label}: ${lo}..${hi}の範囲が必要です`);return x;};
const integer=(x,lo,hi,label)=>{between(x,lo,hi,label);if(!Number.isInteger(x))throw new Error(`${label}: 整数が必要です`);return x;};
const vector=(x,max,label)=>{if(!Array.isArray(x)||x.length!==3)throw new Error(`${label}: 3成分が必要です`);return x.map(n=>between(n,-max,max,label));};
export function createLensPowerProfile(input={}){
  keys(input,['version','kind','apertureRadius','radialSamples','angularSamples','powerWatts','stokes','source','sensor','wavelengths','material','settings'],'profile');
  if(input.version!==undefined&&input.version!==1||input.kind!==undefined&&input.kind!==kind)throw new Error('未対応のprofile version/kindです');
  const apertureRadius=between(input.apertureRadius??.005,1e-5,.015,'開口半径[m]'),powerWatts=between(input.powerWatts??1,1e-6,1e6,'単色実験ごとのPOWER[W]');
  const radialSamples=input.radialSamples??4,angularSamples=input.angularSamples??16;
  if(![1,2,4,8,16].includes(radialSamples)||![4,8,16,32,64].includes(angularSamples)||radialSamples*angularSamples>1024)throw new Error('瞳標本は指定された二の冪の組合せで1024以下にしてください');
  const stokes=input.stokes??'unpolarized';if(!Object.hasOwn(powers,stokes))throw new Error('未対応の初期Stokesです');
  const s=input.source??{};keys(s,['kind','direction','transverseReference'],'source');if(s.kind!==undefined&&s.kind!=='parallel')throw new Error('このprofileのsourceはparallelのみです');
  const direction=vector(s.direction??[0,0,1],1000,'入射方向');if(direction[2]<=0)throw new Error('入射方向Zは正で指定してください');
  const transverseReference=vector(s.transverseReference??[1,0,0],1e6,'偏光参照軸');
  const sensorInput=input.sensor??{};keys(sensorInput,['center','apertureRadius'],'sensor');
  const center=vector(sensorInput.center??[0,0,639/11800],1,'センサー中心[m]');if(center[2]<.00501)throw new Error('センサーZはレンズ後方の0.00501..1mにしてください');
  const sensor={center,apertureRadius:between(sensorInput.apertureRadius??.05,1e-6,1,'センサー半径[m]')};
  const m=input.material??{};keys(m,['kind','coefficients','validBand'],'material');if(m.kind!==undefined&&m.kind!=='cauchy')throw new Error('このprofileは合成Cauchyモデルのみです');
  const coefficients=vector(m.coefficients??[1.48,6.05e-15,0],1e12,'Cauchy係数'),validBand=m.validBand??[400e-9,700e-9];
  if(!Array.isArray(validBand)||validBand.length!==2||!validBand.every(Number.isFinite)||validBand[0]<1e-12||validBand[1]>1||validBand[0]>validBand[1])throw new Error('有効波長帯が不正です');
  const wavelengths=input.wavelengths??[450e-9,550e-9,650e-9];if(!Array.isArray(wavelengths)||wavelengths.length<1||wavelengths.length>8)throw new Error('1..8個の独立な点波長を指定してください');
  wavelengths.forEach(w=>between(w,validBand[0],validBand[1],'真空波長[m]'));
  const t=input.settings??{};keys(t,['maximumRouteSteps','maximumParameterWidth','maxSqrtRefinements','powerMaxSqrtRefinements','maximumPackets','maximumPacketEvaluations','maximumTotalSqrtRefinements','maximumRouteSqrtRefinements','maximumPhaseWidth'],'settings');
  const settings={maximumRouteSteps:integer(t.maximumRouteSteps??64,1,64,'最大段数'),maximumParameterWidth:between(t.maximumParameterWidth??1e-7,Number.MIN_VALUE,1e6,'parameter幅'),maxSqrtRefinements:integer(t.maxSqrtRefinements??128,1,256,'幾何sqrt上限'),powerMaxSqrtRefinements:integer(t.powerMaxSqrtRefinements??128,1,256,'偏光sqrt上限'),maximumPackets:integer(t.maximumPackets??1024,1,1024,'packet数予算'),maximumPacketEvaluations:integer(t.maximumPacketEvaluations??1024,1,1024,'packet実行予算'),maximumTotalSqrtRefinements:integer(t.maximumTotalSqrtRefinements??1000000,1,4000000,'全sqrt予算'),maximumPhaseWidth:between(t.maximumPhaseWidth??1e-9,Number.MIN_VALUE,1e6,'phase幅')};
  if(t.maximumRouteSqrtRefinements!==undefined)settings.maximumRouteSqrtRefinements=integer(t.maximumRouteSqrtRefinements,1,4000000,'各routeのsqrt予算');
  return {version:1,kind,apertureRadius,radialSamples,angularSamples,powerWatts,stokes,source:{kind:'parallel',direction,transverseReference},sensor,wavelengths:[...wavelengths],material:{kind:'cauchy',coefficients,validBand:[...validBand]},settings};
}
export const serializeLensPowerProfile=profile=>JSON.stringify(createLensPowerProfile(profile),null,2)+'\n';
export const parseLensPowerProfile=text=>createLensPowerProfile(JSON.parse(text));
export function createLensPowerNodes(input){
  const profile=createLensPowerProfile(input),nodes=[],n=profile.radialSamples*profile.angularSamples,powerWatts=profile.powerWatts/n;
  // n is a power of two; this division is exact and normal throughout the domain.
  for(let ring=0;ring<profile.radialSamples;++ring){const radius=profile.apertureRadius*Math.sqrt((ring+.5)/profile.radialSamples);
    for(let j=0;j<profile.angularSamples/2;++j){const angle=2*Math.PI*(j+.5)/profile.angularSamples,x=radius*Math.cos(angle),y=radius*Math.sin(angle);
      nodes.push({position:[x,y,LENS_POWER_GEOMETRY.launchZ],power:[powerWatts,...powers[profile.stokes].map(v=>v===0?0:v*powerWatts)]},{position:[-x,-y,LENS_POWER_GEOMETRY.launchZ],power:[powerWatts,...powers[profile.stokes].map(v=>v===0?0:v*powerWatts)]});}
  }
  return nodes;
}
export function createLensPowerPaths(profileInput,index){
  const profile=createLensPowerProfile(profileInput);if(!Array.isArray(index)||index.length!==2||!index.every(Number.isFinite)||index[0]<1e-6||index[1]>1e6||index[0]>index[1])throw new Error('位相屈折率の全区間が必要です');
  const front={kind:'cap',vertex:[0,0,0],axis:[0,0,1],signedRadius:.05,apertureRadius:profile.apertureRadius},back={kind:'cap',vertex:[0,0,.005],axis:[0,0,1],signedRadius:-.05,apertureRadius:profile.apertureRadius};
  const step=(surface,nextIndex,branch)=>({surface,nextIndex,branch,minimumParameter:0,maximumParameter:1e6});
  return [{id:'primary',steps:[step(front,[...index],'transmitted'),step(back,1,'transmitted')]},{id:'ghost',steps:[step(front,[...index],'transmitted'),step(back,1,'reflected'),step(front,1,'reflected'),step(back,1,'transmitted')]}];
}
const abort=signal=>{if(signal?.aborted)throw new DOMException('参照計算を中止しました','AbortError');};
export async function evaluateLensPowerProfile(runtime,input,{onProgress=()=>{},yieldControl=()=>Promise.resolve(),signal}={}){
  const profile=createLensPowerProfile(input),nodes=createLensPowerNodes(profile),packets=[],channels=[],started=performance.now(),total=nodes.length+2*profile.wavelengths.length;
  for(const name of ['makeOpticalLaunchRay','queryDispersion','queryPolarizedPacket'])if(typeof runtime?.[name]!=='function')throw new Error('Lens power C++ API unavailable; load the matching WebAssembly runtime');
  abort(signal);for(const node of nodes){packets.push({ray:runtime.makeOpticalLaunchRay(profile.source,node.position),power:[...node.power],transverseReference:[...profile.source.transverseReference]});if(packets.length%16===0){onProgress({completed:packets.length,total,phase:'launch'});await yieldControl();abort(signal);}}
  const sensor={kind:'disk',center:[...profile.sensor.center],normal:[0,0,-1],apertureRadius:profile.sensor.apertureRadius};let done=nodes.length;
  for(const wavelength of profile.wavelengths){
    abort(signal);const dispersion=runtime.queryDispersion(profile.material,wavelength,{maximumPhaseWidth:profile.settings.maximumPhaseWidth,maxSqrtRefinements:profile.settings.maxSqrtRefinements});
    const index=dispersion.status==='resolved'&&dispersion.values?.withinInterfaceDomain?dispersion.values.phase:null,paths=[];
    for(const path of index?createLensPowerPaths(profile,index):LENS_POWER_PATHS.map(id=>({id,steps:null}))){
      abort(signal);const result=path.steps?runtime.queryPolarizedPacket({packets,steps:path.steps,sensor,index:1,vacuumWavelength:wavelength},profile.settings):null;
      paths.push({...path,result});onProgress({completed:++done,total,phase:'path',wavelength,path:path.id});await yieldControl();abort(signal);
    }
    channels.push({wavelength,index,dispersion,paths});
  }
  return {profile,geometry:{...LENS_POWER_GEOMETRY},nodes,packets,sensor,channels,diagnostics:runtime.diagnostics,timing:{totalMilliseconds:performance.now()-started}};
}

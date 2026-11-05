// Reference geometric lens spots. Physical intersections and moments are C++.
// Sampling nodes are rounded binary64 inputs, not certified disk integration.
export const LENS_SPOT_GEOMETRY=Object.freeze({frontRadius:.05,backRadius:-.05,thickness:.005,launchZ:-.01,sensorApertureRadius:1});
const kind='synthetic-biconvex-geometric-spot';
const finite=(v,label)=>{if(typeof v!=='number'||!Number.isFinite(v))throw new Error(`${label} must be a finite number`);return v;};
const vector=(v,label)=>{if(!Array.isArray(v)||v.length!==3)throw new Error(`${label} requires three numbers`);return v.map(x=>finite(x,label));};
const integer=(v,lo,hi,label)=>{finite(v,label);if(!Number.isInteger(v)||v<lo||v>hi)throw new Error(`${label} requires an integer in ${lo}..${hi}`);return v;};
const keys=(o,names,label)=>{if(!o||typeof o!=='object'||Array.isArray(o)||Object.keys(o).some(k=>!names.includes(k)))throw new Error(`Unknown ${label} field`);};
export function createLensSpotProfile(input={}){
  keys(input,['version','kind','apertureRadius','sensorZ','radialSamples','angularSamples','source','wavelengths','material','settings'],'lens profile');
  if((input.version!==undefined&&input.version!==1)||(input.kind!==undefined&&input.kind!==kind))throw new Error('Unsupported lens spot profile version/kind');
  const apertureRadius=finite(input.apertureRadius??.015,'apertureRadius'),sensorZ=finite(input.sensorZ??639/11800,'sensorZ');
  if(apertureRadius<1e-5||apertureRadius>.015)throw new Error('Synthetic lens aperture radius must be 0.00001..0.015 m');
  if(sensorZ<.00501||sensorZ>1)throw new Error('Sensor plane must be behind this lens, in 0.00501..1 m');
  const radialSamples=integer(input.radialSamples??4,1,16,'radialSamples'),angularSamples=integer(input.angularSamples??16,4,64,'angularSamples');
  if(angularSamples%2)throw new Error('Angular sample count must be even for opposite pairs');
  const sourceInput=input.source??{kind:'parallel',direction:[0,0,1]};keys(sourceInput,['kind','direction','position'],'source');let source;
  if(sourceInput.kind==='parallel'){
    if(sourceInput.position!==undefined)throw new Error('Parallel beam has no finite object position');
    const direction=vector(sourceInput.direction??[0,0,1],'parallel direction');if(direction[2]<=0||Math.max(...direction.map(Math.abs))>1000)throw new Error('Parallel beam must travel toward +Z with components within +/-1000');source={kind:'parallel',direction};
  }else if(sourceInput.kind==='finite'){
    if(sourceInput.direction!==undefined)throw new Error('Finite point direction is determined by each launch target');
    const position=vector(sourceInput.position,'finite object position');if(position[2]>=LENS_SPOT_GEOMETRY.launchZ-1e-6||Math.max(...position.map(Math.abs))>1000)throw new Error('Finite object point must precede the launch plane and lie within +/-1000m');source={kind:'finite',position};
  }else throw new Error('Source requires finite or parallel');
  const wavelengths=input.wavelengths??[450e-9,550e-9,650e-9];if(!Array.isArray(wavelengths)||wavelengths.length<1||wavelengths.length>8)throw new Error('Specify 1..8 point vacuum wavelengths');
  const materialInput=input.material??{};keys(materialInput,['kind','coefficients','validBand'],'material');if(materialInput.kind!==undefined&&materialInput.kind!=='cauchy')throw new Error('Synthetic profile requires an explicit Cauchy model');
  const coefficients=vector(materialInput.coefficients??[1.48,6.05e-15,0],'Cauchy coefficients');if(coefficients.some(x=>Math.abs(x)>1e12))throw new Error('Cauchy coefficient outside supported range');
  const validBand=materialInput.validBand??[400e-9,700e-9];if(!Array.isArray(validBand)||validBand.length!==2||!validBand.every(Number.isFinite)||validBand[0]<1e-12||validBand[1]>1||validBand[0]>validBand[1])throw new Error('Invalid declared wavelength band');
  for(const wavelength of wavelengths)if(finite(wavelength,'vacuum wavelength')<validBand[0]||wavelength>validBand[1])throw new Error('Wavelength outside the declared material band');
  const settingsInput=input.settings??{};keys(settingsInput,['maximumParameterWidth','maxSqrtRefinements','maximumSampleEvaluations','maximumTotalSqrtRefinements','maximumPhaseWidth'],'settings');
  const settings={maximumParameterWidth:finite(settingsInput.maximumParameterWidth??1e-7,'parameter width'),maxSqrtRefinements:integer(settingsInput.maxSqrtRefinements??128,1,256,'sqrt refinements'),maximumSampleEvaluations:integer(settingsInput.maximumSampleEvaluations??1024,1,1024,'sample evaluations'),maximumTotalSqrtRefinements:integer(settingsInput.maximumTotalSqrtRefinements??1000000,1,4000000,'total sqrt work'),maximumPhaseWidth:finite(settingsInput.maximumPhaseWidth??1e-9,'phase width')};
  if(settings.maximumParameterWidth<=0||settings.maximumParameterWidth>1e6||settings.maximumPhaseWidth<=0||settings.maximumPhaseWidth>1e6)throw new Error('Width limits must lie in (0,1e6]');
  return {version:1,kind,apertureRadius,sensorZ,radialSamples,angularSamples,source,wavelengths:[...wavelengths],material:{kind:'cauchy',coefficients,validBand:[...validBand]},settings};
}
export const serializeLensSpotProfile=profile=>JSON.stringify(createLensSpotProfile(profile),null,2)+'\n';
export const parseLensSpotProfile=text=>createLensSpotProfile(JSON.parse(text));
export function createLensPupilSamples(profile){
  const p=createLensSpotProfile(profile),nodes=[],weight=1/(p.radialSamples*p.angularSamples);
  for(let ring=0;ring<p.radialSamples;++ring){
    const radius=p.apertureRadius*Math.sqrt((ring+.5)/p.radialSamples);
    for(let j=0;j<p.angularSamples/2;++j){const theta=2*Math.PI*(j+.5)/p.angularSamples,x=radius*Math.cos(theta),y=radius*Math.sin(theta);
      nodes.push({position:[x,y,LENS_SPOT_GEOMETRY.launchZ],weight},{position:[-x,-y,LENS_SPOT_GEOMETRY.launchZ],weight});}
  }
  return nodes;
}
const abort=signal=>{if(signal?.aborted)throw new DOMException('Optical reference calculation cancelled','AbortError');};
export async function evaluateLensSpotProfile(runtime,input,{onProgress=()=>{},yieldControl=()=>Promise.resolve(),signal}={}){
  const profile=createLensSpotProfile(input),nodes=createLensPupilSamples(profile),started=performance.now();
  for(const name of ['makeOpticalLaunchRay','queryOpticalSpot','queryDispersion'])if(typeof runtime?.[name]!=='function')throw new Error('Lens spot C++ API unavailable; load the matching WebAssembly runtime');
  const samples=[],channels=[],total=nodes.length+profile.wavelengths.length;abort(signal);
  for(const node of nodes){samples.push({ray:runtime.makeOpticalLaunchRay(profile.source,node.position),weight:node.weight});if(samples.length%16===0){onProgress({completed:samples.length,total,phase:'launch'});await yieldControl();abort(signal);}}
  const geometry={...LENS_SPOT_GEOMETRY},sensor={kind:'disk',center:[0,0,profile.sensorZ],normal:[0,0,-1],apertureRadius:geometry.sensorApertureRadius};
  const front={kind:'cap',vertex:[0,0,0],axis:[0,0,1],signedRadius:geometry.frontRadius,apertureRadius:profile.apertureRadius};
  const back={kind:'cap',vertex:[0,0,geometry.thickness],axis:[0,0,1],signedRadius:geometry.backRadius,apertureRadius:profile.apertureRadius};
  for(const wavelength of profile.wavelengths){
    abort(signal);const dispersion=runtime.queryDispersion(profile.material,wavelength,{maximumPhaseWidth:profile.settings.maximumPhaseWidth,maxSqrtRefinements:profile.settings.maxSqrtRefinements});
    const index=dispersion.status==='resolved'&&dispersion.values?.withinInterfaceDomain?dispersion.values.phase:null;
    const result=index?runtime.queryOpticalSpot({samples,steps:[{surface:front,nextIndex:index,branch:'transmitted',maximumParameter:1e6},{surface:back,nextIndex:1,branch:'transmitted',maximumParameter:1e6}],sensor,index:1,vacuumWavelength:wavelength},profile.settings):null;
    channels.push({wavelength,index,dispersion,result});onProgress({completed:nodes.length+channels.length,total,wavelength,phase:'channel'});await yieldControl();abort(signal);
  }
  return {profile,geometry,nodes,samples,channels,diagnostics:runtime.diagnostics,timing:{totalMilliseconds:performance.now()-started}};
}

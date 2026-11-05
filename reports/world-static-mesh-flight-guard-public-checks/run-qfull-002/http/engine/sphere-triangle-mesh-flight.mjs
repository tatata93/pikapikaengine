// Owned wire/metadata decoder. C++ alone constructs the geometric enclosures.
const prefix='_pp_sim_sphere_triangle_mesh_flight';
const statuses=['entry_window','separated','initial_penetration','not_certified','invalid_input','unsupported_environment','numerical_failure'];
const reasons=['none','settings','surface_count','surface_id','duplicate_id','input_domain','surface_budget','mesh_query_failed','initial_boundary','evaluation_budget','leaf_budget','depth_budget','sqrt_budget','time_resolution','nonfinite_intermediate','allocation_failure','environment','coverage_inconsistent','body_not_found','body_invalid','unsupported_body','derived_domain'];
const kinds=['initial_point','cell'],outcomes=['pending','initial_separated','initial_penetration','initial_uncertain','separated','split','unresolved'];
const states=['unqueried','certified','unresolved','current'];
const meshStatuses=['completed','invalid_input','budget_exceeded','row_failure','numerical_failure','unsupported_environment'];
const meshReasons=['none','settings','surface_count','surface_budget','surface_id','duplicate_id','input_domain','row_failed','aggregate_inconsistent','nonfinite_intermediate','allocation_failure','environment'];
const workKeys=['meshQueries','primitiveQueries','candidatesExamined','primitiveSqrtRefinements','enclosureSqrtRefinements','sqrtRefinements','sqrtRefinementsUpper','meshSqrtLimitedRows','enclosureSqrtCalls','enclosureSqrtLimitedCalls'];
const workMaxima=[256,16384,114688,8388608,262144,8650752,16777216,16384,512,512];
const fail=label=>{throw new Error('Invalid C++ sphere triangle mesh flight '+label);};
const integer=(v,max)=>Number.isSafeInteger(v)&&!Object.is(v,-0)&&v>=0&&v<=max;
const flag=v=>Object.is(v,0)||v===1;
const finite=v=>{if(!Number.isFinite(v))throw new Error('Flight input requires finite numbers');return v;};
const uint=(v,label)=>{if(!Number.isInteger(v)||v<0||v>0xffffffff)throw new Error(label+' requires a uint32 integer');return v;};
const object=(v,label)=>{if(!v||typeof v!=='object'||Array.isArray(v)||ArrayBuffer.isView(v))throw new Error(label+' requires an object');return v;};
function vector(v,label){
  if(!(Array.isArray(v)||ArrayBuffer.isView(v)))throw new Error(label+' requires three components');
  const length=v.length;if(length!==3)throw new Error(label+' requires three components');
  return [finite(v[0]),finite(v[1]),finite(v[2])];
}
const defaulted=(value,fallback)=>value===undefined?fallback:value;
function profile(value){
  const s=object(value,'Flight held settings'),mesh=object(defaulted(s.mesh,{}),'Flight mesh settings'),p=object(defaulted(mesh.primitive,{}),'Flight primitive settings');
  return {mesh:{maxSurfaces:uint(defaulted(mesh.maxSurfaces,64),'maxSurfaces'),primitive:{
    maxCandidates:uint(defaulted(p.maxCandidates,7),'maxCandidates'),sqrtRefinements:uint(defaulted(p.sqrtRefinements,128),'sqrtRefinements'),maxTotalSqrtRefinements:uint(defaulted(p.maxTotalSqrtRefinements,1024),'primitive maxTotalSqrtRefinements'),
    maximumLocalWidth:finite(defaulted(p.maximumLocalWidth,1e-7)),maximumNormalWidth:finite(defaulted(p.maximumNormalWidth,1e-8)),minimumSineSquared:finite(defaulted(p.minimumSineSquared,1e-12))}},
    maxEvaluations:uint(defaulted(s.maxEvaluations,256),'maxEvaluations'),maxLeaves:uint(defaulted(s.maxLeaves,128),'maxLeaves'),maxDepth:uint(defaulted(s.maxDepth,24),'maxDepth'),
    enclosureSqrtRefinements:uint(defaulted(s.enclosureSqrtRefinements,128),'enclosureSqrtRefinements'),maxTotalSqrtRefinements:uint(defaulted(s.maxTotalSqrtRefinements,1000000),'maxTotalSqrtRefinements'),timeTolerance:finite(defaulted(s.timeTolerance,1e-7))};
}
function copyProfile(s,normalize=false){
  const u=v=>normalize&&v===0?0:v,p=s.mesh.primitive;
  return {mesh:{maxSurfaces:u(s.mesh.maxSurfaces),primitive:{maxCandidates:u(p.maxCandidates),sqrtRefinements:u(p.sqrtRefinements),maxTotalSqrtRefinements:u(p.maxTotalSqrtRefinements),maximumLocalWidth:p.maximumLocalWidth,maximumNormalWidth:p.maximumNormalWidth,minimumSineSquared:p.minimumSineSquared}},
    maxEvaluations:u(s.maxEvaluations),maxLeaves:u(s.maxLeaves),maxDepth:u(s.maxDepth),enclosureSqrtRefinements:u(s.enclosureSqrtRefinements),maxTotalSqrtRefinements:u(s.maxTotalSqrtRefinements),timeTolerance:s.timeTolerance};
}
const copyTriangles=source=>source.map(t=>({id:t.id,vertices:t.vertices.map(v=>v.slice())}));
function packet(values,length,label){
  if(!(Array.isArray(values)||ArrayBuffer.isView(values))||values.length!==length)fail(label+' packet length');
  const a=Array.from(values);if(!a.every(Number.isFinite))fail(label+' finite/dense packet');return a;
}
function zeros(a,lo,hi,label){for(let i=lo;i<hi;++i)if(!Object.is(a[i],0))fail(label+' padding');}
function interval(a,at){if(a[at]>a[at+1])fail('interval order');return a.slice(at,at+2);}
const bounds=(a,at)=>[interval(a,at),interval(a,at+2),interval(a,at+4)];
function optional(a,at,length,decode){if(!flag(a[at]))fail('optional flag');if(a[at])return decode(a,at+1);zeros(a,at+1,at+1+length,'absent optional');return null;}
function index(a,has,at,count,label){
  if(!flag(a[has]))fail(label+' flag');if(a[has]){if(!integer(a[at],count-1))fail(label+' index');return a[at];}
  zeros(a,at,at+1,label);return null;
}
function cell(a,at,allowInitial=false){
  const c={timeBounds:a.slice(at,at+2),depth:a[at+2]},[lo,hi]=c.timeBounds;
  if(!integer(c.depth,32)||Object.is(lo,-0)||Object.is(hi,-0)||lo<0||hi>.1)fail('seconds cell domain');
  if(allowInitial&&Object.is(lo,0)&&Object.is(hi,0)&&c.depth===0)return c;
  if(!(lo<hi))fail('seconds cell width');return c;
}
const sameArray=(a,b)=>a.length===b.length&&a.every((x,i)=>Object.is(x,b[i]));
const sameBounds=(a,b)=>a.length===b.length&&a.every((x,i)=>sameArray(x,b[i]));
const sameCell=(a,b)=>a.depth===b.depth&&sameArray(a.timeBounds,b.timeBounds);
const initialCell=c=>c.depth===0&&Object.is(c.timeBounds[0],0)&&Object.is(c.timeBounds[1],0);
function work(a,at){
  const w={};for(let i=0;i<10;++i){if(!integer(a[at+i],workMaxima[i]))fail('work counter');w[workKeys[i]]=a[at+i];}
  if(!flag(a[at+10]))fail('work exact flag');w.workExact=Boolean(a[at+10]);
  if(w.sqrtRefinements!==w.primitiveSqrtRefinements+w.enclosureSqrtRefinements||w.sqrtRefinements>w.sqrtRefinementsUpper||w.workExact&&w.sqrtRefinements!==w.sqrtRefinementsUpper||
    w.meshSqrtLimitedRows>w.primitiveQueries||w.enclosureSqrtLimitedCalls>w.enclosureSqrtCalls||w.candidatesExamined>7*w.primitiveQueries||w.primitiveSqrtRefinements>512*w.primitiveQueries||w.enclosureSqrtRefinements>512*w.enclosureSqrtCalls)fail('work arithmetic');
  return w;
}
function audit(a,ordinal,n){
  if(a[0]!==ordinal||!integer(a[0],255)||!integer(a[1],1)||!integer(a[6],6)||!flag(a[25]))fail('audit identity');zeros(a,62,64,'audit reserved');
  const c=cell(a,2,a[1]===0),kind=kinds[a[1]];
  if((ordinal===0)!==(kind==='initial_point')||kind==='initial_point'&&!initialCell(c)||Object.is(a[5],-0)||a[5]!== (kind==='initial_point'?0:(c.timeBounds[0]+c.timeBounds[1])/2))fail('audit kind/time');
  const r={kind,cell:c,time:a[5],outcome:outcomes[a[6]],pathBounds:optional(a,7,6,bounds),pointBounds:optional(a,14,6,bounds),anchor:optional(a,21,3,(v,o)=>v.slice(o,o+3)),meshQueried:Boolean(a[25]),
    meshStatus:optional(a,26,1,(v,o)=>{if(!integer(v[o],5))fail('audit mesh status');return meshStatuses[v[o]];}),meshReason:optional(a,28,1,(v,o)=>{if(!integer(v[o],11))fail('audit mesh reason');return meshReasons[v[o]];}),
    distance:optional(a,30,2,interval),displacementSquaredBound:optional(a,33,2,interval),errorSquaredBound:optional(a,36,2,interval),displacementRoot:optional(a,39,2,interval),errorRoot:optional(a,42,2,interval),
    clearanceCertificate:optional(a,45,2,interval),penetrationCertificate:optional(a,48,2,interval),work:work(a,51)};
  const w=r.work;
  if(w.meshQueries!==Number(r.meshQueried)||w.meshQueries>1||w.primitiveQueries>n||w.enclosureSqrtCalls>2||w.enclosureSqrtRefinements>1024||w.sqrtRefinementsUpper>512*n+1024||
    (r.meshStatus===null)!==(r.meshReason===null)||r.meshStatus!==null&&!r.meshQueried)fail('audit work/flags');
  if(r.pathBounds===null&&r.pointBounds!==null||r.pointBounds===null&&r.anchor!==null||r.meshQueried&&r.anchor===null||r.meshStatus===null&&(w.primitiveQueries||w.candidatesExamined||w.primitiveSqrtRefinements||w.meshSqrtLimitedRows))fail('audit execution prefix');
  if(r.meshStatus!==null){const allowed=[[0],[1,2,4,5,6],[3],[7],[8,9,10],[11]];if(!allowed[meshStatuses.indexOf(r.meshStatus)].includes(meshReasons.indexOf(r.meshReason)))fail('audit mesh classification');}
  if(r.distance!==null&&(r.meshStatus!=='completed'||r.distance[0]<=0)||r.displacementSquaredBound!==null&&r.distance===null||r.errorSquaredBound!==null&&r.displacementSquaredBound===null||
    r.displacementRoot!==null&&r.errorSquaredBound===null||r.errorRoot!==null&&r.displacementRoot===null||r.clearanceCertificate!==null&&r.errorRoot===null||r.penetrationCertificate!==null&&r.clearanceCertificate===null)fail('audit numeric prefix');
  for(const key of ['displacementSquaredBound','errorSquaredBound'])if(r[key]&&r[key][1]<0)fail('audit squared upper bound');
  for(const key of ['displacementRoot','errorRoot'])if(r[key]&&r[key][0]<0)fail('audit nonnegative root');
  const roots=Number(r.displacementRoot!==null)+Number(r.errorRoot!==null);
  if(roots>w.enclosureSqrtCalls||w.workExact&&roots!==w.enclosureSqrtCalls||w.enclosureSqrtCalls&&r.errorSquaredBound===null||!w.workExact&&w.enclosureSqrtCalls>roots+1)fail('root accounting');
  if(!w.workExact){
    // An interrupted block retains its full pre-call reservation. These are
    // counts/optional execution links, not a JavaScript estimate of its work.
    if(w.enclosureSqrtCalls===roots+1){
      if(r.meshStatus!=='completed'||r.distance===null||w.sqrtRefinementsUpper!==w.sqrtRefinements+512)fail('unknown enclosure reservation');
    }else{
      const proof=['distance','displacementSquaredBound','errorSquaredBound','displacementRoot','errorRoot','clearanceCertificate','penetrationCertificate'];
      if(!r.meshQueried||w.enclosureSqrtCalls!==0||roots!==0||w.sqrtRefinementsUpper!==n*512||proof.some(key=>r[key]!==null))fail('unknown mesh reservation');
    }
  }
  if(kind==='initial_point'&&!['initial_separated','initial_penetration','initial_uncertain','unresolved'].includes(r.outcome)||kind==='cell'&&!['separated','split','unresolved'].includes(r.outcome))fail('audit outcome kind');
  if(r.outcome==='separated'&&(!r.clearanceCertificate||r.clearanceCertificate[0]<=0)||['initial_separated','initial_penetration','initial_uncertain'].includes(r.outcome)&&(!r.clearanceCertificate||!r.penetrationCertificate)||
    r.outcome==='initial_separated'&&r.clearanceCertificate[0]<=0||r.outcome==='initial_penetration'&&r.penetrationCertificate[1]>=0||r.outcome==='initial_uncertain'&&(r.clearanceCertificate[0]>0||r.penetrationCertificate[1]<0)||
    ['split','unresolved'].includes(r.outcome)&&r.clearanceCertificate&&r.clearanceCertificate[0]>0)fail('audit outcome proof');
  if(r.outcome==='split'&&(!w.workExact||!['completed','row_failure'].includes(r.meshStatus)||r.meshStatus==='completed'&&(!r.clearanceCertificate||!r.penetrationCertificate)))fail('split returned execution prefix');
  return r;
}

// Replay the bounded *metadata* schedule. No point/triangle mathematics occurs here.
function validatePartition(r,s){
  const beforePartition=r.snapshot&&r.partition.length===0&&r.status==='numerical_failure';
  if(!r.snapshot||beforePartition){
    if(r.partition.length||r.audits.length||r.certifiedLeaves.length||r.current||r.frontier.length||r.partitionLeaves||r.maximumDepth||r.initial||r.initialSeparationProven||r.safePrefix||r.bestWitness||r.window||r.lastMesh)fail('pre-partition diagnostics');return;
  }
  const H=r.snapshot.horizon,p=[{cell:{timeBounds:[0,H],depth:0},state:'unqueried',auditIndex:null,blockedReason:'none'}];
  let maximumDepth=0,best=null;
  const choose=()=>{let selected=-1;for(let i=0;i<p.length;++i){const l=p[i];if(l.state!=='unqueried'||best&&l.cell.timeBounds[0]>=best.time)continue;
    if(selected<0||l.cell.depth<p[selected].cell.depth||l.cell.depth===p[selected].cell.depth&&l.cell.timeBounds[0]<p[selected].cell.timeBounds[0])selected=i;}return selected;};
  const first=r.audits[0];
  if(r.initial){
    if(!first||r.initial.auditIndex!==0||!first.clearanceCertificate||!first.penetrationCertificate||!sameArray(r.initial.lowerGapCertificate,first.clearanceCertificate)||!sameArray(r.initial.upperGapCertificate,first.penetrationCertificate))fail('initial proof link');
  }
  if(Boolean(r.initial)!==Boolean(first?.clearanceCertificate&&first?.penetrationCertificate))fail('missing initial proof');
  if(r.initialSeparationProven!==Boolean(r.initial&&r.initial.lowerGapCertificate[0]>0)||r.initialSeparationProven&&first.outcome!=='initial_separated')fail('initial strict sign');
  if(r.status==='initial_penetration'&&(!r.initial||first.outcome!=='initial_penetration'||r.initial.upperGapCertificate[1]>=0)||r.reason==='initial_boundary'&&(!r.initial||first.outcome!=='initial_uncertain'))fail('initial classification');
  if(!r.initialSeparationProven&&r.audits.length>1)fail('cell before positive initial proof');
  for(let i=1;i<r.audits.length;++i){const a=r.audits[i],selected=choose();
    if(selected<0||!sameCell(a.cell,p[selected].cell))fail('breadth-first audit order');maximumDepth=Math.max(maximumDepth,a.cell.depth);
    const leaf=p[selected];leaf.auditIndex=i;
    if(a.penetrationCertificate&&a.penetrationCertificate[1]<0&&(!best||a.time<best.time))best={time:a.time,auditIndex:i};
    if(a.outcome==='split'){
      if(a.cell.depth>=s.maxDepth||p.length>=s.maxLeaves)fail('split beyond profile');
      p.splice(selected,1,{cell:{timeBounds:[a.cell.timeBounds[0],a.time],depth:a.cell.depth+1},state:'unqueried',auditIndex:null,blockedReason:'none'},
        {cell:{timeBounds:[a.time,a.cell.timeBounds[1]],depth:a.cell.depth+1},state:'unqueried',auditIndex:null,blockedReason:'none'});
    }else if(a.outcome==='separated')leaf.state='certified';
    else{
      const stopped=r.current&&sameCell(a.cell,r.current)&&i===r.audits.length-1;
      leaf.state=stopped?'current':'unresolved';
      leaf.blockedReason=stopped?r.reason:r.window&&i===r.audits.length-1?'none':a.cell.depth>=s.maxDepth?'depth_budget':p.length>=s.maxLeaves?'leaf_budget':'none';
      if(!stopped&&leaf.blockedReason==='none'&&!(r.window&&i===r.audits.length-1))fail('unresolved cell without blocking reason');
    }
  }
  if(r.current&&!initialCell(r.current)){
    const linked=r.audits.at(-1);if(!linked||!sameCell(linked.cell,r.current)||linked.kind==='initial_point'){
      const selected=choose();if(selected<0||!sameCell(p[selected].cell,r.current))fail('unqueried current order');
      p[selected].state='current';p[selected].blockedReason=r.reason;maximumDepth=Math.max(maximumDepth,r.current.depth);
    }
  }else if(r.current){
    const beforeInitialAudit=!first&&r.status==='numerical_failure'&&r.reason==='allocation_failure';
    if(!beforeInitialAudit&&(!first||r.audits.length!==1||!sameCell(first.cell,r.current)))fail('initial current link');
  }
  if(!r.initialSeparationProven&&r.current&&!initialCell(r.current))fail('current before initial proof');
  if(p.length!==r.partition.length||r.partitionLeaves!==p.length||maximumDepth!==r.maximumDepth)fail('partition counts/depth');
  for(let i=0;i<p.length;++i){const x=p[i],y=r.partition[i];if(!sameCell(x.cell,y.cell)||x.state!==y.state||x.auditIndex!==y.auditIndex||x.blockedReason!==y.blockedReason)fail('partition history');}
  const frontier=p.filter(l=>l.state==='unqueried').map(l=>l.cell);
  if(frontier.length!==r.frontier.length||frontier.some((c,i)=>!sameCell(c,r.frontier[i])))fail('full unqueried frontier/tail');
  const leaves=p.filter(l=>l.state==='certified');
  if(leaves.length!==r.certifiedLeaves.length)fail('certified island count');
  for(let i=0;i<leaves.length;++i){const l=r.certifiedLeaves[i],expected=leaves[i],a=r.audits[l.auditIndex];
    if(l.auditIndex!==expected.auditIndex||!sameCell(l.cell,expected.cell)||!a||a.outcome!=='separated'||!sameArray(l.lowerGapCertificate,a.clearanceCertificate)||l.lowerGapCertificate[0]<=0)fail('certified island link');}
  let safe=0;for(const l of p){if(l.state!=='certified')break;safe=l.cell.timeBounds[1];}
  if(Boolean(r.safePrefix)!==r.initialSeparationProven||r.safePrefix&&!sameArray(r.safePrefix,[0,safe]))fail('closed prefix continuity');
  if(Boolean(best)!==Boolean(r.bestWitness)||best&&(best.auditIndex!==r.bestWitness.auditIndex||!Object.is(best.time,r.bestWitness.time)))fail('smallest strict negative witness');
  if(r.status==='separated'&&(!r.work.workExact||!r.initialSeparationProven||safe!==H||r.bestWitness||r.current||p.some(l=>l.state!=='certified')))fail('incomplete separated cover');
  if(r.status==='initial_penetration'&&(r.initialSeparationProven||r.bestWitness||r.current))fail('initial penetration metadata');
}


function validateHeld(r,s,source){
  const w=r.work,sums=Object.fromEntries(workKeys.map(k=>[k,0]));let exact=true;
  for(let i=0;i<r.audits.length;++i){const a=r.audits[i];for(const k of workKeys)sums[k]+=a.work[k];exact=exact&&a.work.workExact;if(!a.work.workExact&&i!==r.audits.length-1)fail('work after unknown block');}
  if(workKeys.some(k=>w[k]!==sums[k])||w.workExact!==exact)fail('delta/global work sums');
  if(r.snapshot&&(w.meshQueries>s.maxEvaluations||r.partition.length>s.maxLeaves||r.maximumDepth>s.maxDepth||w.sqrtRefinementsUpper>s.maxTotalSqrtRefinements))fail('profile work budget');
  if(!r.snapshot&&(Object.values(sums).some(v=>v!==0)||!w.workExact))fail('preflight work');
  if(!r.snapshot&&(r.acceleration||r.wholePathBounds||r.wholeVelocityBounds))fail('preflight global bounds');
  if(r.lastMesh){const a=r.audits[r.lastMeshAuditIndex],m=r.lastMesh;
    if(!a||!a.meshQueried||a.meshStatus!==m.status||a.meshReason!==m.reason||a.work.primitiveQueries!==m.queries||a.work.candidatesExamined!==m.candidatesExamined||a.work.primitiveSqrtRefinements!==m.sqrtRefinements||a.work.meshSqrtLimitedRows!==m.sqrtLimitedRows||
      a.distance!==null&&(!m.nearest||!sameArray(a.distance,m.nearest.distance)))fail('last mesh audit link');
    for(let i=r.lastMeshAuditIndex+1;i<r.audits.length;++i)if(r.audits[i].meshStatus!==null)fail('not the last returned mesh');
  }else if(r.audits.some(a=>a.meshStatus!==null))fail('missing returned mesh');
  if(r.bestWitness){const b=r.bestWitness,a=r.audits[b.auditIndex];
    if(!a||a.kind!=='cell'||!sameCell(b.cell,a.cell)||!Object.is(b.time,a.time)||!a.pointBounds||!sameBounds(b.exactPathBounds,a.pointBounds)||!a.anchor||!sameArray(b.anchor,a.anchor)||!a.errorRoot||!Object.is(b.errorUpper,a.errorRoot[1])||!a.penetrationCertificate||!sameArray(b.upperGapCertificate,a.penetrationCertificate)||b.upperGapCertificate[1]>=0)fail('E-corrected witness link');}
  if(r.window){const x=r.window,b=r.bestWitness,ids=source.map(t=>t.id).sort((a,b)=>a-b);
    if(!r.initialSeparationProven||!r.safePrefix||!b||!w.workExact||r.current||!sameArray(x.timeBounds,[r.safePrefix[1],b.time])||!(x.timeBounds[0]<x.timeBounds[1])||x.timeWidth[1]<=0||x.timeWidth[1]>s.timeTolerance||x.witnessAuditIndex!==b.auditIndex||!sameArray(r.candidateSurfaceIds,ids))fail('entry window proof/IDs');
    // Parameter subtraction is a metadata cross-check, not a new geometric bound.
    const difference=x.timeBounds[1]-x.timeBounds[0];if(x.timeWidth[0]>difference||x.timeWidth[1]<difference)fail('window width metadata');
  }else if(r.candidateSurfaceIds.length)fail('candidate IDs without window');
  validatePartition(r,s);
}

const guardStatuses=['certified_separated','not_certified','invalid_input','unsupported_environment','numerical_failure'];
const guardReasons=['none','settings','body_not_found','body_invalid','unsupported_body','input_domain','surface_count','surface_id','duplicate_id','surface_budget','flight_tube_failure','derived_domain','inflated_radius_domain','propagation_failure','candidate_invalid','endpoint_tube_failure','held_load_not_separated','environment','allocation_failure','nonfinite_intermediate','coverage_inconsistent'];
const flightFailures=['none','invalid_input','initial_contact','query_unresolved','event_budget','segment_budget','query_budget','root_budget','geometric_guard','propagation_failure','solver_failure','sustained_contact_required','numerical_failure'];
const clone=value=>structuredClone(value);
function id(value){if(!Number.isSafeInteger(value)||value<1)throw new Error('Flight ID requires an integer in 1..9007199254740991');return value;}
function vectorN(value,length,label){
  if(!(Array.isArray(value)||ArrayBuffer.isView(value)))throw new Error(label+' requires '+length+' components');
  const count=value.length;if(count!==length)throw new Error(label+' requires '+length+' components');
  const result=[];for(let i=0;i<length;++i)result.push(finite(value[i]));return result;
}
function sphereInput(value){
  const s=object(value,'Held sphere'),{id:identity,position,velocity,mass,force,gravity,radius}=s;
  return {id:id(identity),position:vector(position,'Sphere position'),velocity:vector(velocity,'Sphere velocity'),mass:finite(mass),force:vector(force,'Sphere force'),gravity:vector(gravity,'Sphere gravity'),radius:finite(radius)};
}
function bodyInput(value){
  const b=object(value,'Flight body'),{id:identity,isStatic,mass,radius,inertiaDiagonal,position,orientation,velocity,angularMomentum,force,torque,material}=b;
  if(typeof isStatic!=='boolean')throw new Error('Flight body isStatic requires a boolean');
  const m=object(material,'Flight material'),{restitution,friction}=m;
  return {id:id(identity),isStatic,mass:finite(mass),radius:finite(radius),inertiaDiagonal:vector(inertiaDiagonal,'Body inertiaDiagonal'),position:vector(position,'Body position'),orientation:vectorN(orientation,4,'Body orientation'),velocity:vector(velocity,'Body velocity'),angularMomentum:vector(angularMomentum,'Body angularMomentum'),force:vector(force,'Body force'),torque:vector(torque,'Body torque'),material:{restitution:finite(restitution),friction:finite(friction)}};
}
function sourceInput(triangles){
  if(!Array.isArray(triangles))throw new Error('Flight requires an array of at most 64 surfaces');
  const count=triangles.length;if(!Number.isInteger(count)||count<0||count>64)throw new Error('Flight requires an array of at most 64 surfaces');
  const result=[];for(let i=0;i<count;++i){const t=object(triangles[i],'Static triangle'),identity=t.id,vertices=t.vertices;
    if(!Array.isArray(vertices))throw new Error('Static triangle requires three vertices');const length=vertices.length;if(length!==3)throw new Error('Static triangle requires three vertices');
    const a=vertices[0],b=vertices[1],c=vertices[2];result.push({id:id(identity),vertices:[vector(a,'Triangle vertex'),vector(b,'Triangle vertex'),vector(c,'Triangle vertex')]});}
  return result;
}
function encodeProfile(s){const p=s.mesh.primitive;return [s.mesh.maxSurfaces,p.maxCandidates,p.sqrtRefinements,p.maxTotalSqrtRefinements,p.maximumLocalWidth,p.maximumNormalWidth,p.minimumSineSquared,s.timeTolerance,s.maxEvaluations,s.maxLeaves,s.maxDepth,s.enclosureSqrtRefinements,s.maxTotalSqrtRefinements];}
function encodeSphere(s,H,p){return [s.id,...s.position,...s.velocity,s.mass,...s.force,...s.gravity,s.radius,H,...encodeProfile(p),0,0,0];}
function encodeBody(b){return [b.id,Number(b.isStatic),b.mass,b.radius,...b.inertiaDiagonal,...b.position,...b.orientation,...b.velocity,...b.angularMomentum,...b.force,...b.torque,b.material.restitution,b.material.friction];}
function decodeBody(a){
  if(!integer(a[0],Number.MAX_SAFE_INTEGER)||a[0]<1||!flag(a[1]))fail('body metadata');
  return {id:a[0],isStatic:Boolean(a[1]),mass:a[2],radius:a[3],inertiaDiagonal:a.slice(4,7),position:a.slice(7,10),orientation:a.slice(10,14),velocity:a.slice(14,17),angularMomentum:a.slice(17,20),force:a.slice(20,23),torque:a.slice(23,26),material:{restitution:a[26],friction:a[27]}};
}
function validateCandidateBody(b){
  // This is the already-successful Native candidate's finite numerical domain,
  // not a caller/original-body validator and not another propagation solver.
  const bounded=(v,limit)=>v.every(x=>Math.abs(x)<=limit),[ix,iy,iz]=b.inertiaDiagonal,[x,y,z,w]=b.orientation,q2=x*x+y*y+z*z+w*w;
  if(b.isStatic||b.mass<1e-12||b.mass>1e18||!(b.radius>0)||b.radius>1e9||!bounded(b.inertiaDiagonal,1e18)||b.inertiaDiagonal.some(v=>v<1e-12)||
    ix+iy<iz||ix+iz<iy||iy+iz<ix||!bounded(b.position,1e12)||!bounded(b.velocity,1e9)||!bounded(b.angularMomentum,1e24)||!bounded(b.force,1e24)||!bounded(b.torque,1e24)||
    !Number.isFinite(q2)||Math.abs(q2-1)>=1e-8||b.material.restitution<0||b.material.restitution>1||b.material.friction<0||b.material.friction>10)fail('successful candidate body domain');
}
function open(runtime){
  const native=runtime.native,functions={};
  for(const suffix of ['_begin','_append','_query','_record','_last_mesh','_candidate']){const fn=native[prefix+suffix];if(typeof fn!=='function')throw new Error('C++ sphere triangle mesh flight API unavailable; rebuild the common simulation SDK');functions[suffix]=fn;}
  return {native,call:(suffix,...args)=>Reflect.apply(functions[suffix],native,args)};
}
function meshResult(runtime,wire,mode,source,decodeMesh){
  runtime.check(wire.call('_last_mesh',mode,0,0));const header=packet(runtime.output(),24,'last mesh header');let length=14;
  const reader={native:wire.native,check:code=>runtime.check(code),output:()=>{
    const q=packet(runtime.output(),length,'last mesh record');
    const metadata=length===58?[0,1,2,3,4,5,6,7,8,9,10,13]:length===13?[0,1,2]:[];
    if(metadata.some(i=>Object.is(q[i],-0)))fail('last mesh canonical metadata');return q;
  }};
  if(typeof decodeMesh!=='function')fail('missing const mesh decoder');
  return decodeMesh(reader,header,source,{
    source:i=>{length=14;return wire.call('_record',mode,1,i);},
    row:i=>{length=58;return wire.call('_last_mesh',mode,1,i);},
    candidate:(i,j)=>{length=13;return wire.call('_candidate',mode,i,j);}});
}
function sourcePackets(read,source,hasMesh){
  for(let i=0;i<source.length;++i){const q=read(1,i,14,'source'),expected=[i,source[i].id,...source[i].vertices.flat()];
    if(!expected.every((v,j)=>Object.is(v,q[j]))||![11,12,13].every(j=>flag(q[j]))||q[12]>q[11]||q[13]>q[12]||!hasMesh&&q.slice(11).some(v=>!Object.is(v,0)))fail('owned source bits/flags');}
}
function decodeHeld(runtime,wire,mode,read,source,sphere,H,s,decodeMesh){
  const a=read(3,0,48,'held header'),n=source.length;
  if(!integer(a[0],6)||!integer(a[1],21)||a[2]!==n||!integer(a[2],64)||![3,4,6,7,8,9,10,11,16,19,20,22,23,24].every(i=>flag(a[i]))||![12,13,14,26].every(i=>integer(a[i],128))||!integer(a[15],256)||!integer(a[21],64)||!integer(a[27],32)||a[6]!==0)fail('held header metadata');
  zeros(a,39,48,'held header');
  const status=statuses[a[0]],reason=reasons[a[1]],allowed=[[0],[0],[0],[6,7,8,9,10,11,12,13,20,21],[1,2,3,4,5,18,19],[16],[14,15,17]];
  if(!allowed[a[0]].includes(a[1])||Boolean(a[20])!==(status==='entry_window')||a[23]!==a[24]||a[11]>a[10]||a[26]!==a[13])fail('held classification');
  const failedIndex=index(a,4,5,n,'failed source'),lastMeshAuditIndex=index(a,24,25,a[15],'last mesh audit');
  if(failedIndex!==null&&(status!=='invalid_input'||![3,4,5].includes(a[1])))fail('held failed index classification');
  const safePrefix=a[16]?interval(a,17):null;if(!a[16])zeros(a,17,19,'held absent prefix');
  let snapshot=null;
  if(a[3]){const echo=read(4,0,32,'held snapshot input'),expected=encodeSphere(sphere,H,copyProfile(s,true));if(!sameArray(echo,expected))fail('held normalized input bits');snapshot={input:clone(sphere),horizon:H,triangles:copyTriangles(source),settings:copyProfile(s,true)};}
  if(status==='invalid_input'&&snapshot||['entry_window','separated','initial_penetration','not_certified'].includes(status)&&!snapshot)fail('held snapshot classification');
  const getBounds=(has,kind)=>{if(!has)return null;const q=read(kind,0,8,'held bounds');zeros(q,0,1,'bounds ordinal');zeros(q,7,8,'bounds');return bounds(q,1);};
  const acceleration=getBounds(a[7],9),wholePathBounds=getBounds(a[8],10),wholeVelocityBounds=getBounds(a[9],11);
  if(wholePathBounds&&!acceleration||wholeVelocityBounds&&!wholePathBounds||a[15]&&!wholeVelocityBounds)fail('held global diagnostic prefix');
  const audits=[];for(let i=0;i<a[15];++i)audits.push(audit(read(12,i,64,'audit'),i,n));
  const certifiedLeaves=[];for(let i=0;i<a[12];++i){const q=read(13,i,6,'certified leaf');if(!integer(q[5],audits.length-1))fail('leaf audit');certifiedLeaves.push({cell:cell(q,0),lowerGapCertificate:interval(q,3),auditIndex:q[5]});}
  const partition=[];for(let i=0;i<a[13];++i){const q=read(14,i,8,'partition');if(q[0]!==i||!integer(q[0],127)||!integer(q[4],3)||!integer(q[7],21))fail('partition metadata');partition.push({cell:cell(q,1),state:states[q[4]],auditIndex:index(q,5,6,audits.length,'partition audit'),blockedReason:reasons[q[7]]});}
  const frontier=[];for(let i=0;i<a[14];++i){const q=read(15,i,4,'frontier');if(q[0]!==i||!integer(q[0],127))fail('frontier ordinal');frontier.push(cell(q,1));}
  let current=null,initial=null,bestWitness=null,window=null;
  if(a[22]){const q=read(16,0,4,'current');zeros(q,0,1,'current ordinal');current=cell(q,1,true);}
  if(a[10]){const q=read(17,0,6,'initial');zeros(q,0,1,'initial ordinal');if(!integer(q[5],audits.length-1))fail('initial audit');initial={lowerGapCertificate:interval(q,1),upperGapCertificate:interval(q,3),auditIndex:q[5]};}
  if(a[19]){const q=read(18,0,18,'witness');zeros(q,0,1,'witness ordinal');if(!integer(q[17],audits.length-1)||q[14]<0)fail('witness metadata');bestWitness={cell:cell(q,1),time:q[4],exactPathBounds:bounds(q,5),anchor:q.slice(11,14),errorUpper:q[14],upperGapCertificate:interval(q,15),auditIndex:q[17]};}
  if(a[20]){const q=read(19,0,14,'window');zeros(q,0,1,'window ordinal');if(!integer(q[13],audits.length-1))fail('window witness');window={timeBounds:interval(q,1),timeWidth:interval(q,3),pathBounds:bounds(q,5),l1DiameterBound:interval(q,11),witnessAuditIndex:q[13]};}
  const candidateSurfaceIds=[];for(let i=0;i<a[21];++i){const q=read(20,i,2,'conservative ID');if(q[0]!==i||!integer(q[0],63)||!Number.isSafeInteger(q[1])||q[1]<1)fail('conservative ID');candidateSurfaceIds.push(q[1]);}
  const lastMesh=a[23]?meshResult(runtime,wire,mode,source,decodeMesh):null;
  const result={status,reason,failedIndex,snapshot,worldBody:null,acceleration,wholePathBounds,wholeVelocityBounds,initial,initialSeparationProven:Boolean(a[11]),certifiedLeaves,safePrefix,bestWitness,window,candidateSurfaceIds,partition,frontier,current,audits,lastMesh,lastMeshAuditIndex,work:work(a,28),partitionLeaves:a[26],maximumDepth:a[27]};
  validateHeld(result,s,source);return result;
}
function decodeTube(q){
  zeros(q,18,24,'tube');const t={nominalAcceleration:q.slice(0,3),exactAcceleration:bounds(q,3),accelerationDifference:bounds(q,9),positionError:q[15],roundoff:q[16],guardRadius:q[17]};
  if(t.roundoff<0||t.positionError<t.roundoff||t.guardRadius<=0)fail('tube domain');return t;
}
function guardResult(a,read,body,gravity,H,s,source,inflated,tube){
  const status=guardStatuses[a[1]],reason=guardReasons[a[2]],allowed=[[0],[4,9,10,11,12,13,14,15,16],[1,2,3,5,6,7,8],[17],[10,16,18,19,20]];
  if(!integer(a[1],4)||!integer(a[2],20)||!allowed[a[1]].includes(a[2])||Boolean(a[14])!==(status==='certified_separated')||a[13]!==a[15])fail('guard classification');
  const failedIndex=index(a,5,6,source.length,'guard failed source');
  if(failedIndex!==null&&(status!=='invalid_input'||![5,7,8].includes(a[2])))fail('guard failure index');
  let snapshot=null,worldBody=null,flightFailure=null,endpoint=null,candidate=null;
  if(a[4]){const q=read(2,0,48,'guard snapshot'),expected=[...encodeBody(body),...gravity,H,...encodeProfile(copyProfile(s.heldLoad,true)),s.maxAngularIncrement,0,0];if(!sameArray(q,expected))fail('guard normalized snapshot');snapshot={body:clone(body),gravity:gravity.slice(),horizon:H,triangles:copyTriangles(source),settings:{heldLoad:copyProfile(s.heldLoad,true),maxAngularIncrement:s.maxAngularIncrement}};}
  if(a[7]){const q=read(5,0,32,'captured world body');zeros(q,31,32,'world body');const expected=[...encodeBody(body),...gravity,0];if(!sameArray(q,expected))fail('captured original body');worldBody={body:decodeBody(q),gravity:q.slice(28,31)};}
  if(!worldBody&&!(status==='unsupported_environment'||status==='numerical_failure'&&reason==='allocation_failure')||snapshot&&!worldBody)fail('missing captured body');
  if(a[9]){if(!integer(a[10],12)||a[10]===0)fail('flight failure enum');flightFailure=flightFailures[a[10]];}else zeros(a,10,11,'absent flight failure');
  if(a[12]){const q=read(7,0,40,'endpoint');zeros(q,35,40,'endpoint');if(![32,33,34].every(i=>flag(q[i])))fail('endpoint flags');endpoint={nominalPosition:bounds(q,0),nominalAllowed:bounds(q,6),exactPosition:bounds(q,12),exactAllowed:bounds(q,18),exactDifference:bounds(q,24),l1ErrorBound:interval(q,30),nominalContained:Boolean(q[32]),exactContained:Boolean(q[33]),l1WithinTube:Boolean(q[34])};if(!tube||endpoint.l1ErrorBound[1]<0||endpoint.l1WithinTube!==(endpoint.l1ErrorBound[1]<=tube.positionError))fail('endpoint L1 metadata');}
  if(a[14]){const q=read(8,0,32,'candidate body');zeros(q,28,32,'candidate body');candidate=decodeBody(q);validateCandidateBody(candidate);const fixed=encodeBody(body);for(let i=0;i<28;++i)if((i<7||i>=20)&&!Object.is(q[i],fixed[i]))fail('candidate changed held fields');
    if(!endpoint)fail('candidate without endpoint');for(let k=0;k<3;++k)if(candidate.position[k]<endpoint.nominalAllowed[k][0]||candidate.position[k]>endpoint.nominalAllowed[k][1]||candidate.position[k]<endpoint.exactAllowed[k][0]||candidate.position[k]>endpoint.exactAllowed[k][1])fail('candidate endpoint tube');}
  const candidateEvaluated=Boolean(a[11]);
  if(!snapshot&&(tube||flightFailure||candidateEvaluated||endpoint||inflated||candidate)||candidateEvaluated&&!tube||endpoint&&!candidateEvaluated||inflated&&!endpoint||flightFailure&&(tube||candidateEvaluated||endpoint||inflated))fail('guard execution prefix');
  if(inflated&&(!tube||tube.guardRadius>1e9||!endpoint.nominalContained||!endpoint.exactContained||!endpoint.l1WithinTube)||status==='certified_separated'&&(!inflated||inflated.status!=='separated'||!inflated.work.workExact)||status!=='certified_separated'&&inflated?.status==='separated')fail('guard/inflated completion');
  if(inflated?.acceleration&&!sameBounds(inflated.acceleration,tube.exactAcceleration))fail('guard/inflated acceleration link');
  return {status,reason,failedIndex,worldBody,snapshot,tube,flightFailure,candidateEvaluated,endpoint,inflated,candidate};
}
function execute(runtime,wire,mode,input,source,sphere,body,gravity,H,s,decodeMesh){
  runtime.check(wire.call('_begin',mode,source.length));
  for(let first=0;first<source.length;first+=6){const count=runtime.inputF64(source.slice(first,first+6).flatMap(t=>[t.id,...t.vertices.flat()]));runtime.check(wire.call('_append',mode,count));}
  runtime.check(wire.call('_query',mode,runtime.inputF64(input)));
  const a=packet(runtime.output(),24,'family summary');
  if(!integer(a[0],1)||a[0]!==mode||!integer(a[1],6)||!integer(a[2],21)||a[3]!==source.length||!integer(a[3],64)||![4,5,7,8,9,11,12,13,14,15].every(i=>flag(a[i])))fail('family summary');zeros(a,16,24,'family');
  const read=(kind,index,length,label)=>{runtime.check(wire.call('_record',mode,kind,index));return packet(runtime.output(),length,label);};
  const echo=read(0,0,mode===0?32:48,'original echo');if(!sameArray(echo,input))fail('original echo bits');
  let result;
  if(mode===0){if(a[7]!==0||a.slice(8,15).some(v=>!Object.is(v,0))||a[15]!==1)fail('held family fields');
    if(a[4]&&!sameArray(read(2,0,32,'held native snapshot'),encodeSphere(sphere,H,copyProfile(s,true))))fail('held native snapshot bits');
    result=decodeHeld(runtime,wire,mode,read,source,sphere,H,s,decodeMesh);
    if(a[1]!==statuses.indexOf(result.status)||a[2]!==reasons.indexOf(result.reason)||Boolean(a[4])!==Boolean(result.snapshot)||Boolean(a[5])!==(result.failedIndex!==null)||!Object.is(a[6],result.failedIndex??0))fail('held family link');
    sourcePackets(read,source,result.lastMesh!==null);result.originalInput={sphere:clone(sphere),horizon:H,triangles:copyTriangles(source),settings:copyProfile(s),echo};
  }else{
    let inflated=null;const tube=a[8]?decodeTube(read(6,0,24,'tube')):null;
    if(a[15]){if(!tube)fail('inflated without tube');const expected={id:body.id,position:body.position.slice(),velocity:body.velocity.slice(),mass:body.mass,force:body.force.slice(),gravity:gravity.slice(),radius:tube.guardRadius};inflated=decodeHeld(runtime,wire,mode,read,source,expected,H,s.heldLoad,decodeMesh);}
    result=guardResult(a,read,body,gravity,H,s,source,inflated,tube);sourcePackets(read,source,inflated?.lastMesh!==null&&inflated!==null);
    result.originalInput={body:clone(body),gravity:gravity.slice(),horizon:H,triangles:copyTriangles(source),settings:{heldLoad:copyProfile(s.heldLoad),maxAngularIncrement:s.maxAngularIncrement},echo};
  }
  return result;
}
export function querySphereTriangleMeshHeldLoad(runtime,sphere,triangles,horizon,settings={},decodeMesh){
  const wire=open(runtime),inputSphere=sphereInput(sphere),source=sourceInput(triangles),H=finite(horizon),s=profile(settings),input=encodeSphere(inputSphere,H,s);
  return execute(runtime,wire,0,input,source,inputSphere,null,null,H,s,decodeMesh);
}
export function querySphereTriangleMeshFreeFlightGuard(runtime,body,gravity,triangles,horizon,settings={},decodeMesh){
  const wire=open(runtime),inputBody=bodyInput(body),g=vector(gravity,'Guard gravity'),source=sourceInput(triangles),H=finite(horizon),value=object(settings,'Guard settings'),held=value.heldLoad,angle=value.maxAngularIncrement;
  const s={heldLoad:profile(defaulted(held,{})),maxAngularIncrement:finite(defaulted(angle,.5))},input=[...encodeBody(inputBody),...g,H,...encodeProfile(s.heldLoad),s.maxAngularIncrement,0,0];
  return execute(runtime,wire,1,input,source,null,inputBody,g,H,s,decodeMesh);
}


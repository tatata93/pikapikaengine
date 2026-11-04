// Wire/ownership validation only. Geometric certificates are produced by C++.
const prefix='_pp_sim_sphere_triangle_mesh_trajectory';
const statuses=['separated','penetration_witness','not_certified','invalid_input','unsupported_environment','numerical_failure'];
const reasons=['none','settings','surface_count','surface_id','duplicate_id','input_domain','surface_budget','mesh_query_failed','evaluation_budget','leaf_budget','depth_budget','sqrt_budget','parameter_resolution','nonfinite_intermediate','allocation_failure','environment','coverage_inconsistent'];
const outcomes=['pending','separated','split','penetration_witness','not_certified'];
const meshStatuses=['completed','invalid_input','budget_exceeded','row_failure','numerical_failure','unsupported_environment'];
const meshReasons=['none','settings','surface_count','surface_budget','surface_id','duplicate_id','input_domain','row_failed','aggregate_inconsistent','nonfinite_intermediate','allocation_failure','environment'];
const workKeys=['meshQueries','primitiveQueries','candidatesExamined','primitiveSqrtRefinements','enclosureSqrtRefinements','sqrtRefinements','sqrtRefinementsUpper','meshSqrtLimitedRows','enclosureSqrtCalls','enclosureSqrtLimitedCalls'];
const workMaxima=[255,16320,114240,8355840,261120,8616960,16777216,16320,510,510];
const fail=label=>{throw new Error('Invalid C++ sphere triangle mesh trajectory '+label);};
const uint=(value,label)=>{if(!Number.isInteger(value)||value<0||value>0xffffffff)throw new Error(label+' requires a uint32 integer');return value;};
const integer=(value,max)=>Number.isSafeInteger(value)&&!Object.is(value,-0)&&value>=0&&value<=max;
const flag=value=>Object.is(value,0)||value===1;
const finite=value=>{if(!Number.isFinite(value))throw new Error('Trajectory input requires finite numbers');return value;};
const vector=(value,label)=>{
  if(!(Array.isArray(value)||ArrayBuffer.isView(value))||value.length!==3)throw new Error(label+' requires three components');
  return [finite(value[0]),finite(value[1]),finite(value[2])];
};
const object=(value,label)=>{if(!value||typeof value!=='object'||Array.isArray(value)||ArrayBuffer.isView(value))throw new Error(label+' requires an object');return value;};
const copyTriangles=source=>source.map(t=>({id:t.id,vertices:t.vertices.map(v=>v.slice())}));
function profile(settings){
  object(settings,'Trajectory settings');const mesh=object(settings.mesh??{},'Trajectory mesh settings'),p=object(mesh.primitive??{},'Trajectory primitive settings');
  return {mesh:{maxSurfaces:uint(mesh.maxSurfaces??64,'maxSurfaces'),primitive:{
    maxCandidates:uint(p.maxCandidates??7,'maxCandidates'),sqrtRefinements:uint(p.sqrtRefinements??128,'sqrtRefinements'),maxTotalSqrtRefinements:uint(p.maxTotalSqrtRefinements??1024,'primitive maxTotalSqrtRefinements'),
    maximumLocalWidth:finite(p.maximumLocalWidth??1e-7),maximumNormalWidth:finite(p.maximumNormalWidth??1e-8),minimumSineSquared:finite(p.minimumSineSquared??1e-12)}},
    maxEvaluations:uint(settings.maxEvaluations??256,'maxEvaluations'),maxLeaves:uint(settings.maxLeaves??128,'maxLeaves'),maxDepth:uint(settings.maxDepth??16,'maxDepth'),
    enclosureSqrtRefinements:uint(settings.enclosureSqrtRefinements??128,'enclosureSqrtRefinements'),maxTotalSqrtRefinements:uint(settings.maxTotalSqrtRefinements??1000000,'maxTotalSqrtRefinements')};
}
function copyProfile(s,normalize=false){
  const u=x=>normalize&&x===0?0:x,p=s.mesh.primitive;
  return {mesh:{maxSurfaces:u(s.mesh.maxSurfaces),primitive:{maxCandidates:u(p.maxCandidates),sqrtRefinements:u(p.sqrtRefinements),maxTotalSqrtRefinements:u(p.maxTotalSqrtRefinements),maximumLocalWidth:p.maximumLocalWidth,maximumNormalWidth:p.maximumNormalWidth,minimumSineSquared:p.minimumSineSquared}},
    maxEvaluations:u(s.maxEvaluations),maxLeaves:u(s.maxLeaves),maxDepth:u(s.maxDepth),enclosureSqrtRefinements:u(s.enclosureSqrtRefinements),maxTotalSqrtRefinements:u(s.maxTotalSqrtRefinements)};
}
function packet(values,length,label){
  if(!(Array.isArray(values)||ArrayBuffer.isView(values))||values.length!==length)fail(label+' packet length');
  const a=Array.from(values);if(!a.every(Number.isFinite))fail(label+' finite/dense packet');return a;
}
function zeros(a,from,to,label){for(let i=from;i<to;++i)if(!Object.is(a[i],0))fail(label+' padding');}
function interval(a,offset){if(a[offset]>a[offset+1])fail('interval order');return a.slice(offset,offset+2);}
const bounds=(a,offset)=>[interval(a,offset),interval(a,offset+2),interval(a,offset+4)];
function optional(a,at,count,decode){
  if(!flag(a[at]))fail('optional flag');
  if(a[at])return decode(a,at+1);
  zeros(a,at+1,at+1+count,'absent optional');return null;
}
function index(a,has,at,count,label){
  if(!flag(a[has]))fail(label+' flag');
  if(a[has]){if(!integer(a[at],count-1))fail(label+' index');return a[at];}
  zeros(a,at,at+1,label);return null;
}
function cell(a,offset){
  const c={parameter:a.slice(offset,offset+2),depth:a[offset+2]};
  if(c.parameter[0]<0||c.parameter[0]>=c.parameter[1]||c.parameter[1]>1||!integer(c.depth,32))fail('cell domain');
  // All wire cells originate from the bounded dyadic partition, not geometry.
  const factor=2**c.depth;if(c.parameter[1]-c.parameter[0]!==1/factor||!Number.isInteger(c.parameter[0]*factor))fail('non-dyadic cell');
  return c;
}
const sameArray=(a,b)=>a.length===b.length&&a.every((x,i)=>Object.is(x,b[i]));
const sameBounds=(a,b)=>a.length===b.length&&a.every((x,i)=>sameArray(x,b[i]));
const sameCell=(a,b)=>a.depth===b.depth&&sameArray(a.parameter,b.parameter);
function work(a,offset){
  const w={};for(let i=0;i<10;++i){const value=a[offset+i];if(!integer(value,workMaxima[i]))fail('work counter');w[workKeys[i]]=value;}
  if(!flag(a[offset+10]))fail('work exact flag');w.workExact=Boolean(a[offset+10]);
  if(w.sqrtRefinements!==w.primitiveSqrtRefinements+w.enclosureSqrtRefinements||w.sqrtRefinements>w.sqrtRefinementsUpper||w.workExact&&w.sqrtRefinements!==w.sqrtRefinementsUpper||
    w.meshSqrtLimitedRows>w.primitiveQueries||w.enclosureSqrtLimitedCalls>w.enclosureSqrtCalls||w.candidatesExamined>7*w.primitiveQueries||w.primitiveSqrtRefinements>512*w.primitiveQueries)fail('work arithmetic');
  return w;
}
function audit(a,ordinal,sourceCount){
  if(a[0]!==ordinal||!integer(a[0],254)||!integer(a[5],4)||!flag(a[24]))fail('audit ordinal/outcome');
  zeros(a,61,64,'audit reserved');
  const c=cell(a,1),midpoint=a[4];if(midpoint!==(c.parameter[0]+c.parameter[1])/2)fail('audit midpoint');
  const r={cell:c,midpoint,outcome:outcomes[a[5]],pathBounds:optional(a,6,6,bounds),pointBounds:optional(a,13,6,bounds),anchor:optional(a,20,3,(v,o)=>v.slice(o,o+3)),meshQueried:Boolean(a[24]),
    meshStatus:optional(a,25,1,(v,o)=>{if(!integer(v[o],5))fail('audit mesh status');return meshStatuses[v[o]];}),
    meshReason:optional(a,27,1,(v,o)=>{if(!integer(v[o],11))fail('audit mesh reason');return meshReasons[v[o]];}),
    distance:optional(a,29,2,interval),displacementSquaredBound:optional(a,32,2,interval),errorSquaredBound:optional(a,35,2,interval),displacementRoot:optional(a,38,2,interval),errorRoot:optional(a,41,2,interval),
    clearanceCertificate:optional(a,44,2,interval),penetrationCertificate:optional(a,47,2,interval),work:work(a,50)};
  const w=r.work;
  if(w.meshQueries!==Number(r.meshQueried)||w.meshQueries>1||w.primitiveQueries>sourceCount||w.enclosureSqrtCalls>2||w.enclosureSqrtRefinements>1024||w.sqrtRefinementsUpper>sourceCount*512+1024||
    (r.meshStatus===null)!==(r.meshReason===null)||r.meshStatus!==null&&!r.meshQueried)fail('audit mesh work/flags');
  if(r.pathBounds===null&&r.pointBounds!==null||r.pointBounds===null&&r.anchor!==null||r.meshQueried&&r.anchor===null||r.meshStatus===null&&(w.primitiveQueries||w.candidatesExamined||w.primitiveSqrtRefinements||w.meshSqrtLimitedRows))fail('audit execution prefix');
  if(r.meshStatus!==null){const allowed=[[0],[1,2,4,5,6],[3],[7],[8,9,10],[11]];
    if(!allowed[meshStatuses.indexOf(r.meshStatus)].includes(meshReasons.indexOf(r.meshReason)))fail('audit mesh classification');}
  if(r.distance!==null&&(r.meshStatus!=='completed'||r.distance[0]<=0)||r.displacementSquaredBound!==null&&r.distance===null||r.errorSquaredBound!==null&&r.displacementSquaredBound===null||
    r.displacementRoot!==null&&r.displacementSquaredBound===null||r.errorRoot!==null&&(r.errorSquaredBound===null||r.displacementRoot===null)||
    r.clearanceCertificate!==null&&r.errorRoot===null||r.penetrationCertificate!==null&&r.clearanceCertificate===null)fail('audit numeric prefix');
  for(const key of ['displacementSquaredBound','errorSquaredBound'])if(r[key]&&r[key][1]<0)fail('audit squared bound');
  for(const key of ['displacementRoot','errorRoot'])if(r[key]&&r[key][0]<0)fail('audit nonnegative root');
  const returnedRoots=Number(r.displacementRoot!==null)+Number(r.errorRoot!==null);
  if(returnedRoots>w.enclosureSqrtCalls||w.workExact&&returnedRoots!==w.enclosureSqrtCalls||w.enclosureSqrtCalls>0&&r.errorSquaredBound===null||!w.workExact&&w.enclosureSqrtCalls>returnedRoots+1)fail('audit root call accounting');
  if(r.outcome==='separated'&&(!r.clearanceCertificate||r.clearanceCertificate[0]<=0)||r.outcome==='penetration_witness'&&(!r.penetrationCertificate||r.penetrationCertificate[1]>=0)||
    r.outcome==='split'&&(!r.penetrationCertificate||r.clearanceCertificate[0]>0||r.penetrationCertificate[1]<0))fail('audit outcome certificate');
  return r;
}
function validatePartition(result){
  const pending=[{parameter:[0,1],depth:0}],leafAudits=[];let partition=1,maximumDepth=0,blocked=null;
  for(let i=0;i<result.audits.length;++i){const a=result.audits[i],next=pending.shift();
    if(blocked||!next||!sameCell(a.cell,next))fail('audit traversal order');maximumDepth=Math.max(maximumDepth,next.depth);
    if(a.outcome==='split'){
      pending.unshift({parameter:[a.midpoint,next.parameter[1]],depth:next.depth+1});
      pending.unshift({parameter:[next.parameter[0],a.midpoint],depth:next.depth+1});partition++;
    }else if(a.outcome==='separated')leafAudits.push(i);
    else{blocked=a.cell;if(i!==result.audits.length-1)fail('audit after blocked cell');}
  }
  if(leafAudits.length!==result.certifiedLeaves.length)fail('leaf/audit count');
  let safe=0;
  for(let i=0;i<result.certifiedLeaves.length;++i){const l=result.certifiedLeaves[i],a=result.audits[l.auditIndex];
    if(l.auditIndex!==leafAudits[i]||!a||!sameCell(l.cell,a.cell)||!sameArray(l.lowerGapCertificate,a.clearanceCertificate)||l.lowerGapCertificate[0]<=0||l.cell.parameter[0]!==safe)fail('closed certified prefix');
    safe=l.cell.parameter[1];
  }
  if(Boolean(result.safePrefix)!==Boolean(result.certifiedLeaves.length)||result.safePrefix&&(!sameArray(result.safePrefix,[0,safe])))fail('safe prefix');
  if(result.current){
    if(blocked){if(!sameCell(blocked,result.current))fail('blocked current link');}
    else{const next=pending.shift();if(!next||!sameCell(result.current,next))fail('unexamined current link');maximumDepth=Math.max(maximumDepth,next.depth);}
  }else if(blocked)fail('missing blocked current');
  const beforePartition=result.snapshot&&result.audits.length===0&&!result.current&&result.frontier.length===0&&result.partitionLeaves===0&&result.status==='numerical_failure';
  if(!result.snapshot||beforePartition){if(result.audits.length||result.certifiedLeaves.length||result.current||result.frontier.length||result.partitionLeaves!==0||result.maximumDepth!==0)fail('pre-partition metadata');}
  else if(result.partitionLeaves!==partition||result.maximumDepth!==maximumDepth||pending.length!==result.frontier.length||pending.some((c,i)=>!sameCell(c,result.frontier[i])))fail('frontier/full partition');
  if(result.status==='separated'&&(!result.snapshot||!result.work.workExact||safe!==1||result.current||result.frontier.length||result.partitionLeaves!==result.certifiedLeaves.length))fail('incomplete separated cover');
}

// A dedicated, synchronous record is read in full before exposing any DTO.
// No JavaScript geometry, normal, or interval arithmetic substitutes for C++.
export function querySphereTriangleMeshTrajectory(runtime,path,triangles,settings={},decodeMesh){
  const m=runtime.native;
  for(const suffix of ['_begin','_append','','_record','_last_mesh','_candidate'])if(typeof m[prefix+suffix]!=='function')throw new Error('C++ sphere triangle mesh trajectory API unavailable; rebuild the common simulation SDK');
  object(path,'Trajectory path');
  if(!Array.isArray(triangles))throw new Error('Trajectory requires an array of at most 64 surfaces');
  const surfaceCount=triangles.length;
  if(surfaceCount>64)throw new Error('Trajectory requires an array of at most 64 surfaces');
  const source=[];
  for(let i=0;i<surfaceCount;++i){const t=object(triangles[i],'Static triangle'),id=t.id,vertices=t.vertices;
    if(!Number.isSafeInteger(id)||id<1)throw new Error('Surface ID requires an integer in 1..9007199254740991');
    if(!Array.isArray(vertices)||vertices.length!==3)throw new Error('Static triangle requires three vertices');
    const a=vertices[0],b=vertices[1],c=vertices[2];
    source.push({id,vertices:[vector(a,'Triangle vertex'),vector(b,'Triangle vertex'),vector(c,'Triangle vertex')]});
  }
  const start=vector(path.start,'Trajectory start'),end=vector(path.end,'Trajectory end'),radius=finite(path.radius),s=profile(settings),p=s.mesh.primitive;
  const input=[...start,...end,radius,s.mesh.maxSurfaces,p.maxCandidates,p.sqrtRefinements,p.maxTotalSqrtRefinements,p.maximumLocalWidth,p.maximumNormalWidth,p.minimumSineSquared,
    s.maxEvaluations,s.maxLeaves,s.maxDepth,s.enclosureSqrtRefinements,s.maxTotalSqrtRefinements,0,0,0,0,0];
  runtime.check(m[prefix+'_begin'](source.length));
  for(let offset=0;offset<source.length;offset+=6){const count=runtime.inputF64(source.slice(offset,offset+6).flatMap(t=>[t.id,...t.vertices.flat()]));runtime.check(m[prefix+'_append'](count));}
  runtime.check(m[prefix](runtime.inputF64(input)));
  const a=packet(runtime.output(),32,'header'),read=(kind,i,length,label)=>{runtime.check(m[prefix+'_record'](kind,i));return packet(runtime.output(),length,label);};
  if(!integer(a[0],5)||!integer(a[1],16)||a[2]!==source.length||!integer(a[2],64)||![3,4,9,12,13,14,15].every(i=>flag(a[i]))||!integer(a[6],128)||!integer(a[7],33)||!integer(a[8],255)||!integer(a[17],128)||!integer(a[18],32))fail('header metadata');
  zeros(a,30,32,'header reserved');const status=statuses[a[0]],reason=reasons[a[1]],allowed=[[0],[0],[6,7,8,9,10,11,12],[1,2,3,4,5],[15],[13,14,16]];
  if(!allowed[a[0]].includes(a[1])||Boolean(a[12])!==(status==='penetration_witness')||a[14]!==a[15])fail('header classification');
  const failedIndex=index(a,4,5,source.length,'failed source'),lastMeshAuditIndex=index(a,15,16,a[8],'last mesh audit'),safePrefix=a[9]?interval(a,10):null;
  if(!a[9])zeros(a,10,12,'absent prefix');
  if(failedIndex!==null&&(status!=='invalid_input'||![3,4,5].includes(a[1]))||status==='invalid_input'&&[3,4].includes(a[1])&&failedIndex===null)fail('failed source classification');
  if(['invalid_input','unsupported_environment'].includes(status)&&a[3]||['separated','penetration_witness','not_certified'].includes(status)&&!a[3])fail('snapshot classification');
  const echo=read(0,0,24,'input echo');if(!sameArray(echo,input))fail('original input bits');
  const originalInput={start:start.slice(),end:end.slice(),radius,triangles:copyTriangles(source),settings:copyProfile(s),echo};
  const snapshot=a[3]?{start:start.slice(),end:end.slice(),radius,triangles:copyTriangles(source),settings:copyProfile(s,true)}:null;
  const sourcePackets=[];
  for(let i=0;i<source.length;++i){const q=read(1,i,14,'original source'),expected=[i,source[i].id,...source[i].vertices.flat()];
    if(!expected.every((x,j)=>Object.is(x,q[j]))||![11,12,13].every(j=>flag(q[j]))||q[12]>q[11]||q[13]>q[12]||!a[14]&&q.slice(11).some(x=>!Object.is(x,0)))fail('original source bits/flags');sourcePackets.push(q);}
  const audits=[];for(let i=0;i<a[8];++i)audits.push(audit(read(2,i,64,'audit'),i,source.length));
  const certifiedLeaves=[];
  for(let i=0;i<a[6];++i){const q=read(3,i,6,'certified leaf');if(!integer(q[5],audits.length-1))fail('leaf audit index');certifiedLeaves.push({cell:cell(q,0),lowerGapCertificate:interval(q,3),auditIndex:q[5]});}
  const frontier=[];
  for(let i=0;i<a[7];++i){const q=read(4,i,4,'frontier');if(q[0]!==i||!integer(q[0],32))fail('frontier ordinal');frontier.push(cell(q,1));}
  let current=null,witness=null;
  if(a[13]){const q=read(5,0,4,'current');if(!Object.is(q[0],0))fail('current ordinal');current=cell(q,1);}
  if(a[12]){const q=read(6,0,18,'witness');if(!Object.is(q[0],0)||!integer(q[17],audits.length-1)||q[14]<0)fail('witness metadata');
    witness={cell:cell(q,1),parameter:q[4],exactPathBounds:bounds(q,5),anchor:q.slice(11,14),errorUpper:q[14],upperGapCertificate:interval(q,15),auditIndex:q[17]};}
  let lastMesh=null;
  if(a[14]){runtime.check(m[prefix+'_last_mesh'](0,0));const h=packet(runtime.output(),24,'last mesh header');
    lastMesh=decodeMesh(runtime,h,source,{source:i=>m[prefix+'_record'](1,i),row:i=>m[prefix+'_last_mesh'](1,i),candidate:(i,j)=>m[prefix+'_candidate'](i,j)});
  }
  const result={status,reason,failedIndex,snapshot,certifiedLeaves,safePrefix,witness,current,frontier,audits,lastMesh,lastMeshAuditIndex,work:work(a,19),partitionLeaves:a[17],maximumDepth:a[18],originalInput};
  const w=result.work,sums=Object.fromEntries(workKeys.map(k=>[k,0]));let exact=true;
  for(let i=0;i<audits.length;++i){const item=audits[i];for(const k of workKeys)sums[k]+=item.work[k];exact=exact&&item.work.workExact;
    if(!item.work.workExact&&i!==audits.length-1)fail('work after unknown block');}
  if(workKeys.some(k=>w[k]!==sums[k])||w.workExact!==exact)fail('work delta/global sums');
  if(snapshot&&(w.meshQueries>s.maxEvaluations||result.partitionLeaves>s.maxLeaves||result.maximumDepth>s.maxDepth||w.sqrtRefinementsUpper>s.maxTotalSqrtRefinements))fail('profile work budget');
  if(!snapshot&&(Object.values(sums).some(x=>x!==0)||!w.workExact||safePrefix||witness||current||lastMesh))fail('preflight diagnostics');
  if(lastMesh){const item=audits[lastMeshAuditIndex];if(!item||!item.meshQueried||item.meshStatus!==lastMesh.status||item.meshReason!==lastMesh.reason||
      item.work.primitiveQueries!==lastMesh.queries||item.work.candidatesExamined!==lastMesh.candidatesExamined||item.work.primitiveSqrtRefinements!==lastMesh.sqrtRefinements||item.work.meshSqrtLimitedRows!==lastMesh.sqrtLimitedRows||
      item.distance!==null&&(!lastMesh.nearest||!sameArray(item.distance,lastMesh.nearest.distance)))fail('last-mesh audit link');
    for(let i=lastMeshAuditIndex+1;i<audits.length;++i)if(audits[i].meshStatus!==null)fail('last-mesh is not the last returned call');
  }else if(audits.some(item=>item.meshStatus!==null))fail('missing returned last mesh');
  if(witness){const item=audits[witness.auditIndex];if(!item||item.outcome!=='penetration_witness'||!current||!sameCell(witness.cell,current)||!sameCell(witness.cell,item.cell)||
      !Object.is(witness.parameter,item.midpoint)||!item.pointBounds||!sameBounds(witness.exactPathBounds,item.pointBounds)||!item.anchor||!sameArray(witness.anchor,item.anchor)||
      !item.errorRoot||!Object.is(witness.errorUpper,item.errorRoot[1])||!item.penetrationCertificate||!sameArray(witness.upperGapCertificate,item.penetrationCertificate)||witness.upperGapCertificate[1]>=0)fail('strict witness link');}
  validatePartition(result);return result;
}

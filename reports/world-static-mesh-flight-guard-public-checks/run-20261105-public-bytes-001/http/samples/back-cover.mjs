import {loadSimulationRuntime} from '../engine/simulation.mjs';
import {parseSkinBindingSource,serializeSkinBindingSource,evaluateSkinBinding} from '../engine/skin-binding.mjs';
import {createDerivedMeshRenderData} from '../engine/derived-render.mjs';

const assetURL=new URL('../assets/robot-back-cover.skin.json',import.meta.url);
const build=new URL(import.meta.url).searchParams.get('build');if(build)assetURL.searchParams.set('build',build);
const errorRecord=error=>({name:error.name??'Error',message:error.message??String(error)});
const clamp=x=>Math.max(0,Math.min(1,x));
export const COVER_ID='robot/player/back-cover';
// Fixed policy; never lowered automatically after a slow frame. Cost acceptance
// and the observed missed/deferred requests are recorded separately.
export const COVER_UPDATE_TICKS=2;
export class RobotBackCover {
  constructor(renderer,{now=()=>performance.now(),onFatal=()=>{}}={}){
    this.renderer=renderer;this.now=now;this.onFatal=onFatal;this.generation=0;this.loadGeneration=0;
    this.disposed=false;this.visible=true;this.pending=null;this.state='loading';this.failure=null;
    this.records=[];this.errors=[];this.counts={scheduled:0,queries:0,reused:0,omittedScheduled:0,deferredFrames:0,checked:0,validated:0,recoveries:0};
    this.maximumTokenAgeSeconds=0;this.startup={};this.reset();
  }
  invalidate(reason){
    ++this.generation;this.renderer.dropMesh(COVER_ID);this.token=null;this.sampleClipSeconds=null;this.sampleTick=null;this.due=1;this.reason=reason;
    // A pending old check still occupies the one allowed slot until it settles.
  }
  reset(){this.invalidate('play reset');this.tick=0;this.u=0;this.previousU=0;this.recovery=false;if(this.readyAsset){this.failure=null;this.state='ready';}}
  stamp(){const value=this.now();if(!Number.isFinite(value)||(this.lastClock!==undefined&&value<this.lastClock))throw new Error('Invalid cover clock');this.lastClock=value;return value;}
  suspend(){this.visible=false;this.invalidate('hidden');}
  resume(){if(!this.visible){this.visible=true;this.invalidate('resume');}}
  dispose(){if(this.disposed)return;this.disposed=true;++this.loadGeneration;this.invalidate('dispose');this.state='disposed';}
  fail(stage,error){
    this.invalidate(stage);this.failure={stage,...errorRecord(error),generation:this.generation,tick:this.tick};this.state='failed';
    this.errors.push({...this.failure});if(this.errors.length>120)this.errors.shift();
  }
  async load({loadRuntime=loadSimulationRuntime,fetchSource=async()=>{
    const response=await fetch(assetURL);if(!response.ok)throw new Error('Cover asset HTTP '+response.status);return response.text();
  }}={}){
    if(this.disposed)return;const generation=++this.loadGeneration;this.invalidate('asset load');this.readyAsset=false;this.failure=null;this.state='loading';
    let stage='runtime';try{
      let start=this.stamp();const runtime=await loadRuntime();const runtimeMs=this.stamp()-start;
      if(this.disposed||generation!==this.loadGeneration)return;
      stage='asset';start=this.stamp();const text=await fetchSource(),assetFetchMs=this.stamp()-start;
      if(this.disposed||generation!==this.loadGeneration)return;
      start=this.stamp();const source=parseSkinBindingSource(text),assetParseMs=this.stamp()-start;
      if(source.target.objectId!==COVER_ID||source.mesh.positions.length!==6||source.mesh.triangles.length!==4||source.motion.clip.duration!==1)throw new Error('Unexpected back cover asset');
      for(const ms of [runtimeMs,assetFetchMs,assetParseMs])if(!Number.isFinite(ms)||ms<0)throw new Error('Invalid cover startup clock');
      this.runtime=runtime;this.source=source;this.authorSource=serializeSkinBindingSource(source);
      this.startup={runtimeMs,assetFetchMs,assetParseMs,assetURL:String(assetURL),diagnostics:runtime.diagnostics};this.readyAsset=true;this.state='ready';
    }catch(error){if(!this.disposed&&generation===this.loadGeneration)this.fail(stage,error);}
  }
  step(dt,{boostActive=false,horizontalSpeed=0}={}){
    if(dt!==1/120||!Number.isFinite(horizontalSpeed)||horizontalSpeed<0)throw new Error('Cover requires a finite 120 Hz drive state');
    // Authored visual idle band, not a tolerance in FK/LBS or a physics clamp.
    // Exponentially decaying controller velocities otherwise request new skins
    // forever even after the player has visibly stopped.
    this.previousU=this.u;const target=boostActive&&horizontalSpeed>1?1:horizontalSpeed<=.1?0:.25*clamp(horizontalSpeed/32);
    this.u=clamp(this.u+Math.max(-4*dt,Math.min(4*dt,target-this.u)));++this.tick;
    if(this.tick%COVER_UPDATE_TICKS===0){++this.due;++this.counts.scheduled;}
  }
  prepare(clipSeconds){
    let stage='source';const record={generation:this.generation,tick:this.tick,clipSeconds,state:'failed',sourceMs:null,derivedMs:null,tokenMs:null};
    try{
      let start=this.stamp();const value=evaluateSkinBinding(this.runtime,this.source,clipSeconds,{loop:false});record.sourceMs=this.stamp()-start;
      if(value.deformation.status!=='completed')throw new Error('Skin deformation '+value.deformation.status);
      stage='derived';start=this.stamp();const result=this.runtime.prepareDerivedMesh({positions:value.deformation.positions,triangles:this.source.mesh.triangles},{readback:'single'});record.derivedMs=this.stamp()-start;
      if(result.status!=='completed')throw new Error('Derived mesh '+result.status+': '+result.reason);
      stage='token';start=this.stamp();const token=createDerivedMeshRenderData(result);record.tokenMs=this.stamp()-start;
      for(const ms of [record.sourceMs,record.derivedMs,record.tokenMs])if(!Number.isFinite(ms)||ms<0)throw new Error('Invalid cover preparation clock');
      this.token=token;this.sampleClipSeconds=clipSeconds;this.sampleTick=this.tick;record.state='completed';this.state='ready';
      return true;
    }catch(error){record.error={stage,...errorRecord(error)};this.fail(stage,error);return false;}
    finally{++this.counts.queries;this.records.push(record);if(this.records.length>7200)this.records.shift();}
  }
  check(items,camera,time,{recovery=false}={}){
    const pending={generation:this.generation,recovery};this.pending=pending;++this.counts.checked;
    if(!recovery)this.state='pending';
    const fatal=error=>{try{this.onFatal(error.message??String(error));}catch{}};
    this.renderer.renderChecked(items,camera,time).then(()=>{
      if(this.pending!==pending)return;this.pending=null;
      if(this.disposed||pending.generation!==this.generation)return;
      if(recovery){this.recovery=false;++this.counts.recoveries;}else{this.state='ready';++this.counts.validated;}
    },error=>{
      if(this.pending!==pending)return;this.pending=null;
      if(this.disposed||pending.generation!==this.generation)return;
      if(recovery){this.recovery=false;fatal(error);}
      else{this.fail('gpu',error);this.recovery=true;}
    }).catch(fatal);
  }
  render(baseItems,camera,time,player,alpha=1,{paused=false}={}){
    if(this.disposed)throw new Error('Cover disposed');
    let fresh=false;const clipSeconds=this.previousU+(this.u-this.previousU)*clamp(alpha);
    if(this.pending)++this.counts.deferredFrames;
    if(this.visible&&this.state!=='loading'&&!this.failure&&!this.pending&&this.runtime&&this.source&&(this.due>0||!this.token||(paused&&clipSeconds!==this.sampleClipSeconds))){
      this.counts.omittedScheduled+=Math.max(0,this.due-1);this.due=0;
      if(this.token&&clipSeconds===this.sampleClipSeconds)++this.counts.reused;else fresh=this.prepare(clipSeconds);
    }
    let items=baseItems;
    if(this.visible&&this.token&&!this.failure){
      const p=player.previous.map((v,j)=>v+(player.p[j]-v)*clamp(alpha)),c=Math.cos(player.yaw),s=Math.sin(player.yaw);
      const cover={id:COVER_ID,type:'derived-mesh',mesh:this.token,position:[p[0]-1.32*s,p[1]+2.65,p[2]-1.32*c],yaw:player.yaw,scale:[1,1,1],color:[.95,.52,.13],emission:.16};
      try{if(baseItems.some(item=>item.id===COVER_ID))throw new Error('Cover render ID collides with level');this.renderer.validateBudget([...baseItems,cover]);items=[...baseItems,cover];}
      catch(error){this.fail('budget',error);fresh=false;}
      if(this.sampleTick!==null)this.maximumTokenAgeSeconds=Math.max(this.maximumTokenAgeSeconds,(this.tick-this.sampleTick)/120);
    }
    // A checked call contains the entire game frame and replaces its normal
    // submit once. Subsequent frames continue while its one promise is pending.
    if(this.visible&&!this.pending&&(fresh||this.recovery))this.check(items,camera,time,{recovery:this.recovery});
    else this.renderer.render(items,camera,time);
    return items;
  }
  status(){return {schema:1,state:this.state,failure:this.failure?{...this.failure}:null,generation:this.generation,
    visible:this.visible,updateEveryTicks:COVER_UPDATE_TICKS,simulationHz:120,tick:this.tick,opening:this.u,
    sampleClipSeconds:this.sampleClipSeconds,sampleTick:this.sampleTick,tokenAgeSeconds:this.sampleTick===null?null:(this.tick-this.sampleTick)/120,
    maximumTokenAgeSeconds:this.maximumTokenAgeSeconds,pending:this.pending?{...this.pending}:null,
    counts:{...this.counts}};}
  report(){return {...this.status(),startup:structuredClone(this.startup),authorSource:this.authorSource??null,
    renderer:{stats:{...this.renderer.stats},residentMeshes:this.renderer.meshBuffers?.size??null,disposed:Boolean(this.renderer.disposed),lost:Boolean(this.renderer.lost)},
    errors:this.errors.map(x=>({...x})),records:structuredClone(this.records),
    scope:'Decorative Source/FK/LBS animation; no hinge force, collision, heat or damage model. CPU stages and queue observations are not GPU timestamps or display FPS.'};}
}

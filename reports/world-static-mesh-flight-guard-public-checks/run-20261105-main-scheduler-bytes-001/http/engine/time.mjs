export class FixedClock {
  constructor(hz=120,maxSteps=24) { this.dt=1/hz; this.maxSteps=maxSteps; this.reset(); }
  reset() { this.accumulator=0; this.tick=0; this.droppedSeconds=0; }
  advance(elapsed,step) {
    if(!Number.isFinite(elapsed)||elapsed<0) throw new Error('Invalid elapsed seconds');
    this.accumulator+=elapsed;
    let count=0;
    while(this.accumulator+1e-10>=this.dt && count<this.maxSteps) {
      step(this.dt,this.tick++); this.accumulator-=this.dt; count++;
    }
    if(this.accumulator>=this.dt) {
      const drop=Math.floor(this.accumulator/this.dt)*this.dt;
      this.droppedSeconds+=drop; this.accumulator-=drop;
    }
    return Math.max(0,this.accumulator/this.dt);
  }
}
export class FrameLog {
  constructor(limit=7200) { this.limit=limit; this.samples=[]; this.total=0; this.consecutive=0; this.maxConsecutive=0; }
  record(frameMs,cpuMs,simulationMs,entities,projectiles) {
    this.total++;
    this.consecutive=frameMs>1000/60?this.consecutive+1:0;
    this.maxConsecutive=Math.max(this.maxConsecutive,this.consecutive);
    this.samples.push({frame:this.total,frameMs,cpuMs,simulationMs,entities,projectiles});
    if(this.samples.length>this.limit) this.samples.shift();
  }
  report(environment={}) {
    const values=this.samples.map(x=>x.frameMs).sort((a,b)=>a-b);
    const pct=p=>values[Math.max(0,Math.ceil(values.length*p)-1)]??0;
    return {schema:1,environment,measurement:'requestAnimationFrame interval + CPU submission; actual presentation and GPU duration unmeasured',budgetMs:1000/60,totalFrames:this.total,retainedFrames:values.length,median:pct(.5),p95:pct(.95),p99:pct(.99),max:values.at(-1)??0,overBudget:values.filter(x=>x>1000/60).length,maxConsecutiveOverBudget:this.maxConsecutive,gpuMs:null,memory:globalThis.performance?.memory?.usedJSHeapSize??null,samples:this.samples};
  }
}

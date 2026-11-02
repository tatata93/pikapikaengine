const finiteVector=(v,n)=>Array.isArray(v)&&v.length===n&&v.every(Number.isFinite);
export function validateScene(data) {
  if(data?.version!==1||data.units!=='m-s-kg'||data.axes!=='right-handed-y-up') throw new Error('Unsupported scene version, units or axes');
  if(!Array.isArray(data.entities)||data.entities.length>4096) throw new Error('Scene entity limit: 4096');
  const ids=new Set();
  for(const e of data.entities) {
    if(typeof e.id!=='string'||!e.id||e.id.length>96||ids.has(e.id)) throw new Error('Invalid or duplicate stable ID');
    ids.add(e.id);
    if(!finiteVector(e.position,3)||e.position.some(x=>Math.abs(x)>1e6)||!finiteVector(e.scale,3)||e.scale.some(x=>x<=0||x>1e6)||!Number.isFinite(e.yaw)||!finiteVector(e.color,3)||e.color.some(x=>x<0||x>1)) throw new Error(`Invalid transform or material: ${e.id}`);
    if(e.type!=='box') throw new Error(`Unsupported primitive: ${e.type}`);
    if(e.parent!==undefined&&e.parent!==null) throw new Error('Hierarchy not supported in scene v1');
  }
  return structuredClone(data);
}
export class Scene {
  constructor(data={version:1,units:'m-s-kg',axes:'right-handed-y-up',entities:[]}) { this.data=validateScene(data); this.history=[]; this.redoStack=[]; }
  get entities() { return this.data.entities; }
  save() { return JSON.stringify(this.data,null,2); }
  static load(text) { if(text.length>2e6) throw new Error('Scene file limit: 2 MB'); return new Scene(JSON.parse(text)); }
  edit(id,patch) {
    const next=structuredClone(this.data),entity=next.entities.find(x=>x.id===id);
    if(!entity) throw new Error(`Unknown ID: ${id}`);
    if('id' in patch||'type' in patch) throw new Error('Stable identity cannot be changed');
    Object.assign(entity,patch); this.commit(next);
  }
  add(entity) { this.commit({...this.data,entities:[...this.entities,entity]}); }
  commit(next) { const valid=validateScene(next); this.history.push(this.save()); this.data=valid; this.redoStack=[]; }
  undo() { if(this.history.length){this.redoStack.push(this.save());this.data=JSON.parse(this.history.pop());} }
  redo() { if(this.redoStack.length){this.history.push(this.save());this.data=JSON.parse(this.redoStack.pop());} }
}
export const box=(id,position,scale,color=[.25,.3,.35],yaw=0)=>({id,type:'box',position,scale,color,yaw});

import {createBoxMesh} from '../../engine/mesh.mjs';
import {hydrostaticForces} from '../../engine/hydrostatics.mjs';

export const LAB_DEFAULTS=Object.freeze({width:4,height:2,length:2,mass:8000,y:0,roll:0});
const fields=Object.freeze({width:{id:'box-width',min:0.5,max:6,label:'横幅'},height:{id:'box-height',min:0.5,max:6,label:'高さ'},length:{id:'box-length',min:0.5,max:6,label:'奥行'},mass:{id:'box-mass',min:100,max:60000,label:'質量'},y:{id:'box-y',min:-5,max:5,label:'箱中心の高さ'},roll:{id:'box-roll',min:-75,max:75,label:'傾き'}});
const density=1000,gravity=9.80665;

export function calculateBuoyancyCase(input={}) {
  const parameters={};
  for(const [name,field] of Object.entries(fields)) {
    const value=Number(input[name]??LAB_DEFAULTS[name]);
    if(!Number.isFinite(value)||value<field.min||value>field.max)throw new Error(`${field.label}が入力範囲外です。`);
    parameters[name]=value;
  }
  const {width,height,length,mass,y,roll}=parameters,angle=roll*Math.PI/180;
  const hydro=hydrostaticForces(createBoxMesh([width,height,length]),{density,gravity,waterLevel:0,position:[0,y,0],centerOfMass:[0,y,0],orientation:[0,0,Math.sin(angle/2),Math.cos(angle/2)]});
  const weight=mass*gravity,netForce=hydro.force[1]-weight;
  // These tolerances classify displayed residuals, not a performance or model-accuracy claim.
  const forceTolerance=Math.max(1e-6,Math.max(hydro.force[1],weight)*1e-10);
  const torqueTolerance=Math.max(1e-6,hydro.force[1]*Math.max(width,height)*1e-10);
  const balance=Math.abs(netForce)<=forceTolerance?'balanced':netForce>0?'up':'down';
  const rollTorque=hydro.torque[2];
  const rotation=Math.abs(rollTorque)<=torqueTolerance?'neutral':roll*rollTorque<0?'restoring':'overturning';
  return {parameters,hydro,weight,netForce,balance,rotation,centerOfMass:[0,y,0],density,gravity};
}

const format=(value,digits=2)=>new Intl.NumberFormat('ja-JP',{minimumFractionDigits:digits,maximumFractionDigits:digits}).format(Math.abs(value)<1e-9?0:value);
const pointText=point=>point?`(${point.map(value=>format(value,3)).join(', ')})`:'なし（排水体積0）';

function drawLab(canvas,state) {
  const ctx=canvas.getContext('2d');if(!ctx)throw new Error('2D図を描く機能が利用できません。');
  const {width,height,y,roll}=state.parameters,angle=roll*Math.PI/180,c=Math.cos(angle),s=Math.sin(angle);
  const corners=[[-width/2,-height/2],[width/2,-height/2],[width/2,height/2],[-width/2,height/2]].map(([x,yy])=>[c*x-s*yy,s*x+c*yy+y]);
  const extent=Math.max(3,...corners.map(p=>Math.abs(p[1])+0.8)),scale=170/extent,waterY=225;
  const project=([x,yy])=>[450+x*scale,waterY-yy*scale];
  ctx.clearRect(0,0,900,470);ctx.fillStyle='#0a1722';ctx.fillRect(0,0,900,470);
  ctx.fillStyle='#143649';ctx.fillRect(0,waterY,900,470-waterY);
  ctx.font='15px system-ui';ctx.lineWidth=1;
  const step=extent>6?2:1;
  for(let metre=-Math.ceil(extent);metre<=extent;metre+=step){const yy=project([0,metre])[1];if(yy<35||yy>430)continue;ctx.strokeStyle='#294356';ctx.beginPath();ctx.moveTo(55,yy);ctx.lineTo(845,yy);ctx.stroke();ctx.fillStyle='#a9c0d3';ctx.fillText(`${metre} m`,12,yy+5);}
  ctx.strokeStyle='#7ee1d1';ctx.lineWidth=2;ctx.setLineDash([8,5]);ctx.beginPath();ctx.moveTo(55,waterY);ctx.lineTo(845,waterY);ctx.stroke();ctx.setLineDash([]);
  ctx.fillStyle='#baf8ee';ctx.fillText('水面 y = 0 m',680,waterY-10);
  function polygon(){ctx.beginPath();corners.forEach((p,i)=>{const [xx,yy]=project(p);if(i===0)ctx.moveTo(xx,yy);else ctx.lineTo(xx,yy);});ctx.closePath();}
  polygon();ctx.fillStyle='#64717a';ctx.fill();
  ctx.save();ctx.beginPath();ctx.rect(0,waterY,900,470-waterY);ctx.clip();polygon();ctx.fillStyle='#367c8d';ctx.fill();ctx.restore();
  polygon();ctx.strokeStyle='#e6edf5';ctx.lineWidth=2;ctx.stroke();
  function arrow(from,to,color,label,labelSide=1){
    const dx=to[0]-from[0],dy=to[1]-from[1],angle=Math.atan2(dy,dx);
    ctx.strokeStyle=color;ctx.fillStyle=color;ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(...from);ctx.lineTo(...to);ctx.stroke();
    ctx.beginPath();ctx.moveTo(...to);ctx.lineTo(to[0]-10*Math.cos(angle-0.4),to[1]-10*Math.sin(angle-0.4));ctx.lineTo(to[0]-10*Math.cos(angle+0.4),to[1]-10*Math.sin(angle+0.4));ctx.closePath();ctx.fill();
    if(label){ctx.font='bold 16px system-ui';ctx.textAlign=labelSide<0?'right':'left';ctx.fillText(label,to[0]+labelSide*12,to[1]+(dy<0?-5:17));ctx.textAlign='left';}
  }
  const G=project(state.centerOfMass),B=state.hydro.centerOfBuoyancy?project(state.hydro.centerOfBuoyancy):null;
  const maxForce=Math.max(state.weight,state.hydro.force[1],1),forceScale=95/maxForce;
  arrow(G,[G[0],G[1]+state.weight*forceScale],'#ffbf75','重力 mg → 下',1);
  if(B)arrow(B,[B[0],B[1]-state.hydro.force[1]*forceScale],'#7ee1d1','浮力 Fᴮ → 上',-1);
  ctx.lineWidth=2;ctx.strokeStyle='#fff';ctx.fillStyle='#192532';ctx.beginPath();ctx.arc(...G,7,0,Math.PI*2);ctx.fill();ctx.stroke();ctx.fillStyle='#fff';ctx.font='bold 16px system-ui';ctx.fillText('G',G[0]+12,G[1]-10);
  if(B){ctx.fillStyle='#7ee1d1';ctx.strokeStyle='#07272b';ctx.beginPath();ctx.moveTo(B[0],B[1]-7);ctx.lineTo(B[0]+7,B[1]);ctx.lineTo(B[0],B[1]+7);ctx.lineTo(B[0]-7,B[1]);ctx.closePath();ctx.fill();ctx.stroke();ctx.fillText('B',B[0]+12,B[1]+19);}
  if(state.rotation!=='neutral') {
    const sign=Math.sign(state.hydro.torque[2]),start=-0.7,end=start-sign*1.3,radius=34;
    ctx.strokeStyle='#fff';ctx.lineWidth=2;ctx.beginPath();ctx.arc(...G,radius,start,end,sign>0);ctx.stroke();
    const tip=[G[0]+radius*Math.cos(end),G[1]+radius*Math.sin(end)],tangent=[sign*Math.sin(end),-sign*Math.cos(end)];
    arrow([tip[0]-tangent[0]*9,tip[1]-tangent[1]*9],tip,'#fff','');
  }
  ctx.font='15px system-ui';ctx.fillStyle='#c3d2e0';ctx.fillText(`横幅 ${format(width,1)} m / 高さ ${format(height,1)} m / 奥行 ${format(state.parameters.length,1)} m`,75,30);
  ctx.fillText(`傾き ${format(roll,0)}° / 断面・力の縮尺を自動調整`,75,450);
  canvas.setAttribute('aria-label',`箱中心y=${format(y)}m、傾き${format(roll,0)}度。浮力${format(state.hydro.force[1])}N、重力${format(state.weight)}N。重心G=${pointText(state.centerOfMass)}m、浮心B=${pointText(state.hydro.centerOfBuoyancy)}。`);
}

export function mountBuoyancyLab(doc) {
  const get=id=>doc.getElementById(id),controls=Object.fromEntries(Object.entries(fields).map(([name,field])=>[name,get(field.id)]));
  let state=null;
  function update() {
    try {
      const next=calculateBuoyancyCase(Object.fromEntries(Object.entries(controls).map(([name,element])=>[name,element.value])));
      drawLab(get('buoyancy-view'),next);
      state=next;
      for(const [name,field] of Object.entries(fields)){const digits=['width','height','length'].includes(name)?1:name==='y'?2:0;get(`${field.id}-value`).textContent=`${format(next.parameters[name],digits)} ${name==='mass'?'kg':name==='roll'?'°':'m'}`;}
      const metrics={'displaced-volume':next.hydro.submergedVolume,'buoyant-force':next.hydro.force[1],'weight-force':next.weight,'net-force':next.netForce,'roll-torque':next.hydro.torque[2],'total-volume':next.hydro.totalVolume};
      for(const [id,value] of Object.entries(metrics)){get(id).textContent=format(value,id==='displaced-volume'?3:2);get(id).dataset.value=String(value);}
      get('balance-message').textContent=next.balance==='balanced'?'鉛直合力はほぼ0です。この姿勢では浮力と重力が釣り合っています。':next.balance==='up'?'鉛直合力は上向きです。この姿勢では、浮力が重力を上回っています。':'鉛直合力は下向きです。この姿勢では、重力が浮力を上回っています。';
      const maximumMass=next.density*next.hydro.totalVolume;
      if(next.parameters.mass>maximumMass)get('balance-message').textContent+=' この箱では全没しても重さを支えきれません。';
      get('torque-message').textContent=next.rotation==='neutral'?'重心まわりの回転トルクはほぼ0です。':next.rotation==='restoring'?'トルクは傾きを戻す向き（復原）です。':'トルクは傾きを増す向きです。復原するとは限りません。';
      get('centers').textContent=`重心 G = ${pointText(next.centerOfMass)} m / 浮心 B = ${pointText(next.hydro.centerOfBuoyancy)}${next.hydro.centerOfBuoyancy?' m':''}`;
      get('lab-state').textContent='入力した姿勢で計算済み。箱は自動では動きません。';
      return next;
    } catch(error) {
      state=null;get('lab-state').textContent=`計算できません: ${error.message} 下の静的な図・説明を参照してください。`;
      const canvas=get('buoyancy-view');
      canvas.setAttribute('aria-label','現在の入力では図を表示できません。下の静的な図と説明をご覧ください。');
      try{canvas.getContext('2d')?.clearRect(0,0,canvas.width,canvas.height);}catch{}
      for(const id of ['displaced-volume','buoyant-force','weight-force','net-force','roll-torque','total-volume']){get(id).textContent='—';delete get(id).dataset.value;}
      get('balance-message').textContent='入力または表示機能を確認してください。';
      get('torque-message').textContent='';get('centers').textContent='';return null;
    }
  }
  for(const control of Object.values(controls))control.addEventListener('input',update);
  get('lab-reset').addEventListener('click',()=>{for(const [name,control] of Object.entries(controls))control.value=String(LAB_DEFAULTS[name]);update();});
  get('lab-controls').disabled=false;update();
  return {update,getState:()=>state};
}

if(typeof document!=='undefined')mountBuoyancyLab(document);

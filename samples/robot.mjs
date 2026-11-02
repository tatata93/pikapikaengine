import {clamp,normalize,sub,add,mul,length,seeded,sweepSphere,lerp} from '../engine/math.mjs';
import {moveController,sweepAabb,impactPoint} from '../engine/physics.mjs';
import {Scene,box,sceneNode} from '../engine/scene.mjs';

export function createArena(seed=93) {
  const rng=seeded(seed),scene=new Scene();
  scene.add(box('ground',[0,-2,0],[490,4,490],[.11,.16,.18]));
  for(let i=-4;i<=4;i++) {
    scene.add(box(`lane-x-${i}`,[i*50,.025,0],[.18,.04,480],[.19,.32,.33]));
    scene.add(box(`lane-z-${i}`,[0,.025,i*50],[480,.04,.18],[.19,.32,.33]));
  }
  for(let i=0;i<32;i++) {
    const x=(rng()-.5)*370,z=(rng()-.5)*370;
    if(Math.hypot(x,z)<42)continue;
    const h=8+rng()*46;
    scene.add(box(`structure-${i}`,[x,h/2,z],[10+rng()*10,h,10+rng()*10],[.19+rng()*.08,.25+rng()*.06,.27+rng()*.05]));
  }
  for(let i=0;i<4;i++)scene.add(box(`beacon-${i}`,[i<2?-235:235,5,i%2?-235:235],[3,10,3],[.08,.7,.65]));
  scene.add(sceneNode('main-camera','camera',[0,18,65]));
  scene.add(sceneNode('test-source','source',[-20,5,-10]));
  scene.add(sceneNode('test-listener','listener',[0,5,30]));
  scene.history=[];return scene;
}
export class RobotGame {
  constructor(scene=createArena(),seed=93) {this.scene=scene;this.seed=seed;this.reset();}
  reset() {
    this.rng=seeded(this.seed);this.time=0;this.player={p:[0,3,30],previous:[0,3,30],v:[0,0,0],yaw:Math.PI,hp:1000,energy:100,cooldown:0};
    this.enemies=[];this.projectiles=[];this.effects=[];this.events=[];this.kills=0;this.wave=1;this.score=0;this.state='ready';this.lock=0;this.shotId=0;
    this.spawnWave();
  }
  get obstacles() {return this.scene.entities.filter(e=>e.type==='box'&&e.solid!==false&&e.id!=='ground'&&!e.id.startsWith('lane-')&&e.sourceType!=='plane');}
  spawnWave() {
    for(let i=0;i<Math.min(4+this.wave,9);i++) {
      const angle=(i-(Math.min(4+this.wave,9)-1)/2)*.46,p=[Math.sin(angle)*125,5,-Math.cos(angle)*125];
      this.enemies.push({id:`w${this.wave}-unit${i}`,p,previous:[...p],v:[0,0,0],yaw:0,hp:120+this.wave*20,cooldown:1+this.rng()*2,phase:this.rng()*6.28});
    }
    this.lock=Math.floor(this.enemies.length/2);
  }
  target() {return this.enemies[this.lock%Math.max(1,this.enemies.length)];}
  cycleLock() {this.lock=(this.lock+1)%Math.max(1,this.enemies.length);}
  fire(source,target,friendly) {
    if(this.projectiles.length>=512)return;
    const direction=normalize(sub(target,source));
    this.projectiles.push({id:++this.shotId,p:[...source],previous:[...source],v:mul(direction,friendly?270:105),friendly,life:3});
    this.events.push({kind:'shot',p:[...source],friendly});
  }
  step(dt,input={}) {
    this.events=[]; if(this.state!=='playing')return;
    this.time+=dt;const p=this.player,obstacles=this.obstacles;p.previous=[...p.p];p.cooldown=Math.max(0,p.cooldown-dt);
    const boost=!!input.boost&&p.energy>2;
    const speed=boost?80:32;const yaw=input.yaw??0;
    let x=(input.right?1:0)-(input.left?1:0),z=(input.backward?1:0)-(input.forward?1:0);
    const mag=Math.hypot(x,z)||1;x/=mag;z/=mag;
    const wanted=[(x*Math.cos(yaw)+z*Math.sin(yaw))*speed,0,(-x*Math.sin(yaw)+z*Math.cos(yaw))*speed];
    const response=1-Math.exp(-dt*12);p.v[0]+=(wanted[0]-p.v[0])*response;p.v[2]+=(wanted[2]-p.v[2])*response;
    if(input.ascend&&p.energy>1){p.v[1]=25;p.energy-=22*dt;}else p.v[1]-=38*dt;
    if(boost&&(x||z)){p.energy-=28*dt;} else if(!input.ascend)p.energy+=20*dt;
    p.energy=clamp(p.energy,0,100);p.p=moveController(p.p,p.v,dt,obstacles);p.p[1]=Math.min(p.p[1],90);
    const target=this.target();
    if(target)p.yaw=Math.atan2(target.p[0]-p.p[0],target.p[2]-p.p[2]);
    if(input.fire&&p.cooldown<=0){
      const aim=target?add(target.p,mul(target.v,length(sub(target.p,p.p))/270)):add(p.p,[-Math.sin(yaw)*200,0,-Math.cos(yaw)*200]);
      this.fire(add(p.p,[0,2,0]),aim,true);p.cooldown=.13;
    }
    for(const e of this.enemies){
      e.previous=[...e.p];const delta=sub(p.p,e.p),distance=length(delta),toward=normalize([delta[0],0,delta[2]]),side=[-toward[2],0,toward[0]];
      const radial=distance>85?12:distance<48?-14:0;e.v=add(mul(toward,radial),mul(side,9*Math.sin(this.time*.6+e.phase)));
      e.v[1]=-9;e.p=moveController(e.p,e.v,dt,obstacles);e.yaw=Math.atan2(delta[0],delta[2]);e.cooldown-=dt;
      if(e.cooldown<=0&&distance<220){this.fire(add(e.p,[0,2,0]),add(p.p,mul(p.v,.2)),false);e.cooldown=1.7+this.rng()*.9;}
    }
    for(const b of this.projectiles){
      b.previous=[...b.p];const end=add(b.p,mul(b.v,dt));let time=1,hit=null;
      for(const e of obstacles){const t=sweepAabb(b.p,end,e.position,e.scale,.2);if(t!==null&&t<=time){time=t;hit='wall';}}
      const targets=b.friendly?this.enemies:[p];
      for(const e of targets){const relativeStart=sub(b.p,e.previous),relativeEnd=sub(end,e.p),t=sweepSphere(relativeStart,relativeEnd,[0,0,0],b.friendly?4.5:3.8);if(t!==null&&t<=time){time=t;hit=e;}}
      b.p=impactPoint(b.p,end,time);b.life-=dt;
      if(hit){b.life=0;if(hit!=='wall'){hit.hp-=b.friendly?34:38;this.events.push({kind:'hit',p:[...b.p],friendly:b.friendly});}
        if(this.effects.length<128)this.effects.push({p:[...b.p],life:.3,maxLife:.3,color:b.friendly?[.2,1,.8]:[1,.35,.12]});}
    }
    this.projectiles=this.projectiles.filter(b=>b.life>0&&b.p[1]>0);
    const dead=this.enemies.filter(e=>e.hp<=0);this.kills+=dead.length;this.score+=dead.length*100;
    for(const e of dead){this.events.push({kind:'destroy',p:[...e.p]});this.effects.push({p:[...e.p],life:.7,maxLife:.7,color:[1,.6,.15]});}
    this.enemies=this.enemies.filter(e=>e.hp>0);this.lock%=Math.max(1,this.enemies.length);
    for(const e of this.effects)e.life-=dt;this.effects=this.effects.filter(e=>e.life>0);
    if(p.hp<=0){p.hp=0;this.state='defeat';}
    else if(!this.enemies.length){this.wave++;p.hp=Math.min(1000,p.hp+160);p.energy=100;if(this.wave>3)this.state='victory';else this.spawnWave();}
  }
  view(alpha=1) {
    const items=this.scene.entities.filter(e=>e.type==='box'),p=this.player;
    const part=(position,scale,color,yaw=0,emission=0)=>items.push({position,scale,color,yaw,emission});
    const robot=(entity,color,player=false)=>{
      const center=lerp(entity.previous,entity.p,alpha),yaw=entity.yaw,c=Math.cos(yaw),s=Math.sin(yaw);
      const limb=(offset,scale,col=color,emission=0)=>part(add(center,[offset[0]*c+offset[2]*s,offset[1],-offset[0]*s+offset[2]*c]),scale,col,yaw,emission);
      limb([0,2,0],[3,2.7,2.2]);limb([0,4,0],[1.5,1.2,1.5]);limb([0,4, .8],[1,.28,.15],player?[.1,1,.85]:[1,.35,.1],3);
      for(const side of [-1,1]){
        const walk=Math.sin(this.time*9+side)*Math.min(1,Math.hypot(...entity.v)/20);
        limb([side*1.1,-.2,walk*.4],[1.1,2.4,1.25]);limb([side*1.1,-1.6,.65],[1.3,.7,2.4]);
        limb([side*2,2,.1],[1,2.2,1.3]);limb([side*2,1.8,1.3],[.6,.65,2.1],[.12,.17,.19]);
        limb([side*1.8,2.9,-1.2],[.8,1.8,.8],[.12,.16,.2]);
        if(player&&p.energy<99&&length(p.v)>40)limb([side*1.8,2.7,-2.3],[.4,.4,2.8],[.1,.8,1],3);
      }
      limb([0,.6,0],[2.5,.6,2],[.14,.18,.22]);
    };
    robot(p,[.64,.7,.67],true);for(const e of this.enemies)robot(e,[.4,.18,.13]);
    for(const b of this.projectiles)part(lerp(b.previous,b.p,alpha),[.25,.25,2.4],b.friendly?[.15,1,.7]:[1,.28,.08],Math.atan2(b.v[0],b.v[2]),4);
    for(const e of this.effects){const size=(1-e.life/e.maxLife)*7+.3;part(e.p,[size,size,size],e.color,this.time*4,2*e.life/e.maxLife);}
    return items;
  }
}

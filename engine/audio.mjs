import {getPortableCore} from './portable.mjs';
export const propagation=(distance,speed=343)=>{
  if(!Number.isFinite(distance)||distance<0||!Number.isFinite(speed)||speed<=0) throw new Error('Invalid propagation inputs');
  const core=getPortableCore();return {delaySeconds:core?core.pp_direct_delay(distance,speed):distance/speed,amplitude:core?core.pp_direct_pressure_gain(distance,1):1/Math.max(1,distance)};
};
// Generated dry pulse. Stereo panning is a presentation approximation, not HRTF.
export class SpatialAudio {
  constructor() { this.context=null; this.enabled=false; this.volume=.18; this.active=0; }
  async start() {
    if(!this.context) {
      this.context=new AudioContext(); this.master=this.context.createGain(); this.master.gain.value=this.volume;
      const limiter=this.context.createDynamicsCompressor();
      limiter.threshold.value=-10; limiter.ratio.value=12;
      this.master.connect(limiter).connect(this.context.destination);
    }
    await this.context.resume(); this.enabled=true;
  }
  mute(mute) { if(this.master) this.master.gain.setTargetAtTime(mute?0:this.volume,this.context.currentTime,.02); }
  pulse(distance,pan=0,frequency=110) {
    if(!this.enabled||this.active>=24) return;
    const {delaySeconds,amplitude}=propagation(distance),t=this.context.currentTime+Math.min(3,delaySeconds);
    const oscillator=this.context.createOscillator(),envelope=this.context.createGain(),panner=this.context.createStereoPanner();
    oscillator.type='triangle'; oscillator.frequency.setValueAtTime(frequency,t); oscillator.frequency.exponentialRampToValueAtTime(frequency*.4,t+.16);
    envelope.gain.setValueAtTime(.0001,t); envelope.gain.exponentialRampToValueAtTime(Math.max(.0002,amplitude),t+.006); envelope.gain.exponentialRampToValueAtTime(.0001,t+.2);
    panner.pan.value=Math.max(-1,Math.min(1,pan)); oscillator.connect(envelope).connect(panner).connect(this.master);
    this.active++; oscillator.onended=()=>{this.active--; oscillator.disconnect();envelope.disconnect();panner.disconnect();};
    oscillator.start(t); oscillator.stop(t+.21);
  }
}

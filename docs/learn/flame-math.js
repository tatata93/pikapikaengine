"use strict";
// Classic script: runs without module fetching on file:// as well as HTTP.
globalThis.PikaFlameMath = (() => {
  const defaults = Object.freeze({ amplitude: 24, frequency: 0.65, phase: 0,
    noise: 10, speed: 1.2, seed: 42, mode: "smooth" });
  const clamp = (value, min, max, fallback) => Number.isFinite(Number(value))
    ? Math.max(min, Math.min(max, Number(value))) : fallback;
  function parameters(p = {}) {
    return {
      amplitude: clamp(p.amplitude, 0, 60, defaults.amplitude),
      frequency: clamp(p.frequency, 0, 8, defaults.frequency),
      phase: clamp(p.phase, -Math.PI, Math.PI, defaults.phase),
      noise: clamp(p.noise, 0, 30, defaults.noise),
      speed: clamp(p.speed, 0, 12, defaults.speed),
      seed: Math.trunc(clamp(p.seed, 0, 4294967295, defaults.seed)) >>> 0,
      mode: ["sine", "multiple", "random", "smooth"].includes(p.mode) ? p.mode : defaults.mode
    };
  }
  // Integer hashing written for this demo; not a secure random generator.
  function randomAt(index, seed) {
    let bits = (index | 0) ^ (seed >>> 0) ^ 0x6d2b79f5;
    bits = Math.imul(bits ^ (bits >>> 16), 0x45d9f3b);
    bits = Math.imul(bits ^ (bits >>> 16), 0x45d9f3b);
    return ((bits ^ (bits >>> 16)) >>> 0) / 4294967295 * 2 - 1;
  }
  function smoothNoise(position, seed) {
    const index = Math.floor(position);
    const u = position - index;
    const blend = u * u * (3 - 2 * u);
    return randomAt(index, seed) * (1 - blend) + randomAt(index + 1, seed) * blend;
  }
  function sample(time, input = defaults) {
    const p = parameters(input);
    const t = Math.max(0, Number.isFinite(time) ? time : 0);
    const angle = 2 * Math.PI * p.frequency * t;
    const sine = p.amplitude * Math.sin(angle + p.phase);
    const multiple = p.amplitude * (0.65 * Math.sin(angle + p.phase)
      + 0.25 * Math.sin(angle * 1.71 + 0.7) + 0.1 * Math.sin(angle * 2.63 + 1.2));
    const random = p.noise * randomAt(Math.floor(t * p.speed), p.seed);
    const smooth = sine + p.noise * smoothNoise(t * p.speed, p.seed);
    return { sine, multiple, random, smooth, selected: { sine, multiple, random, smooth }[p.mode] };
  }
  return Object.freeze({ defaults, parameters, randomAt, smoothNoise, sample });
})();

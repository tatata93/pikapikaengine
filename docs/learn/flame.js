"use strict";
(() => {
  const math = globalThis.PikaFlameMath;
  const ids = ["amplitude", "frequency", "phase", "noise", "speed", "seed", "mode"];
  const controls = Object.fromEntries(ids.map(id => [id, document.getElementById(id)]));
  const flame = document.getElementById("flame");
  const graph = document.getElementById("graph");
  const fc = flame.getContext("2d");
  const gc = graph.getContext("2d");
  const play = document.getElementById("play");
  const status = document.getElementById("demo-status");
  if (!fc || !gc || !math) {
    status.textContent = "操作デモを開始できません。Canvas 2Dまたは計算スクリプトが利用できません。静的な説明・図を参照してください。";
    for (const element of document.querySelectorAll("button, input, select")) element.disabled = true;
    return;
  }
  let time = 0, running = false, runBase = 0, startTimestamp = null, lastPaint = -Infinity;
  const descriptions = {
    sine: "基本のsinのみ。ノイズの強さ・変化速度・シードは使用しません。",
    multiple: "3つのsinを合成。ノイズの強さ・変化速度・シードは使用しません。",
    random: "時間区間ごとに独立した疑似乱数。振幅A・周波数f・位相φは使用しません。",
    smooth: "sinへなめらかなノイズを足します。ノイズの強さ0で基本sinと一致します。"
  };
  function readParameters() {
    const raw = Object.fromEntries(ids.map(id => [id, controls[id].value]));
    return math.parameters(raw);
  }
  function showValues(p) {
    const values = { amplitude: `${p.amplitude} px`, frequency: `${p.frequency.toFixed(2)} Hz`,
      phase: `${p.phase.toFixed(2)} rad`, noise: `${p.noise} px`, speed: `${p.speed.toFixed(2)} 区間/s` };
    for (const [id, value] of Object.entries(values)) document.getElementById(`${id}-value`).textContent = value;
    document.getElementById("mode-description").textContent = descriptions[p.mode];
  }
  function draw() {
    const p = readParameters();
    const result = math.sample(time, p);
    const x = result.selected;
    fc.clearRect(0, 0, 280, 300);
    fc.strokeStyle = "#6c8199"; fc.lineWidth = 1; fc.setLineDash([4, 5]);
    fc.beginPath(); fc.moveTo(140, 25); fc.lineTo(140, 270); fc.stroke(); fc.setLineDash([]);
    const gradient = fc.createLinearGradient(0, 70, 0, 260);
    gradient.addColorStop(0, "#ffd5a2"); gradient.addColorStop(0.65, "#ffae65"); gradient.addColorStop(1, "#d77b4b");
    fc.fillStyle = gradient; fc.beginPath(); fc.moveTo(104, 252);
    fc.bezierCurveTo(65, 205, 130 + x * 0.7, 140, 140 + x, 65);
    fc.bezierCurveTo(147 + x * 0.3, 160, 215, 213, 176, 252);
    fc.quadraticCurveTo(140, 278, 104, 252); fc.fill();
    fc.fillStyle = "#ffe6b8"; fc.beginPath(); fc.moveTo(122, 251);
    fc.bezierCurveTo(100, 225, 133 + x * 0.3, 185, 140 + x * 0.45, 145);
    fc.bezierCurveTo(151, 210, 183, 227, 158, 251); fc.closePath(); fc.fill();
    fc.fillStyle = "#fff"; fc.beginPath(); fc.arc(140 + x, 65, 4, 0, Math.PI * 2); fc.fill();
    fc.font = "14px system-ui"; fc.fillStyle = "#afc2d5"; fc.fillText(`x = ${x.toFixed(2)} px`, 16, 26);
    gc.clearRect(0, 0, 720, 300);
    const left = 52, right = 700, top = 25, bottom = 258;
    const start = Math.max(0, time - 4), end = start + 4;
    const y = value => (top + bottom) / 2 - value / 100 * (bottom - top) / 2;
    gc.font = "13px system-ui"; gc.lineWidth = 1;
    for (const value of [-100, -50, 0, 50, 100]) {
      gc.strokeStyle = value === 0 ? "#617a91" : "#243a50"; gc.beginPath(); gc.moveTo(left, y(value)); gc.lineTo(right, y(value)); gc.stroke();
      gc.fillStyle = "#afc2d5"; gc.fillText(`${value}`, 10, y(value) + 4);
    }
    for (let i = 0; i <= 4; i++) {
      const xx = left + i / 4 * (right - left);
      gc.fillStyle = "#afc2d5"; gc.fillText(`${(start + i).toFixed(1)}s`, xx - 10, 281);
    }
    gc.fillText("x [px]", 5, 13);
    function plot(key, color, dash) {
      gc.strokeStyle = color; gc.lineWidth = key === "selected" ? 2.5 : 1.5; gc.setLineDash(dash); gc.beginPath();
      let started = false;
      for (let i = 0; i <= 648; i++) {
        const t = start + i / 648 * 4;
        if (t > time + 1e-8) break;
        const xx = left + i / 648 * (right - left), yy = y(math.sample(t, p)[key]);
        if (!started) { gc.moveTo(xx, yy); started = true; } else gc.lineTo(xx, yy);
      }
      gc.stroke(); gc.setLineDash([]);
    }
    plot("sine", "#ffbf75", [5, 5]); plot("selected", "#7ee1d1", []);
    const cursor = left + (time - start) / (end - start) * (right - left);
    gc.fillStyle = "#fff"; gc.beginPath(); gc.moveTo(cursor, y(x) - 5); gc.lineTo(cursor - 5, y(x) + 4); gc.lineTo(cursor + 5, y(x) + 4); gc.closePath(); gc.fill();
    status.textContent = `${running ? "再生中" : "停止中"} / t = ${time.toFixed(3)} s / x = ${x.toFixed(2)} px`;
    const commonTime = Math.floor(time + 1e-8);
    document.getElementById("comparison-time").textContent = `共通の同一時刻 t=${commonTime}秒で計算した横変位`;
    for (const fps of [30, 60, 120]) document.getElementById(`sample-${fps}`).textContent = `${math.sample(commonTime, p).selected.toFixed(4)} px`;
  }
  function setRunning(value) {
    running = value; runBase = time; startTimestamp = null; lastPaint = -Infinity;
    play.textContent = running ? "⏸ 停止" : "▶ 再生"; play.setAttribute("aria-pressed", String(running)); draw();
  }
  play.addEventListener("click", () => setRunning(!running));
  document.getElementById("step").addEventListener("click", () => { setRunning(false); time += 1 / 60; draw(); });
  document.getElementById("reset").addEventListener("click", () => {
    running = false; time = 0;
    for (const id of ids) controls[id].value = math.defaults[id];
    document.getElementById("sample-fps").value = "60";
    showValues(readParameters()); setRunning(false);
  });
  for (const id of ids) controls[id].addEventListener("input", () => { showValues(readParameters()); draw(); });
  controls.seed.addEventListener("change", () => { controls.seed.value = readParameters().seed; draw(); });
  document.addEventListener("visibilitychange", () => { if (document.hidden && running) setRunning(false); });
  function frame(timestamp) {
    if (running) {
      if (startTimestamp === null) startTimestamp = timestamp;
      time = runBase + Math.max(0, timestamp - startTimestamp) / 1000;
      const interval = 1000 / Number(document.getElementById("sample-fps").value);
      if (timestamp - lastPaint >= interval - 0.5) { lastPaint = timestamp; draw(); }
    }
    requestAnimationFrame(frame);
  }
  showValues(readParameters()); draw(); requestAnimationFrame(frame);
})();

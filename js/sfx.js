/** 选项点击音效（Web Audio，无需外部文件） */
const Sfx = (() => {
  let ctx = null;
  let enabled = true;

  function ac() {
    if (!ctx) ctx = new (window.AudioContext || window.webkitAudioContext)();
    return ctx;
  }

  function playChoiceClick() {
    if (!enabled) return;
    try {
      const c = ac();
      if (c.state === "suspended") c.resume();
      const t = c.currentTime;
      const osc = c.createOscillator();
      const gain = c.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(880, t);
      osc.frequency.exponentialRampToValueAtTime(1320, t + 0.06);
      gain.gain.setValueAtTime(0.0001, t);
      gain.gain.exponentialRampToValueAtTime(0.22, t + 0.01);
      gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.14);
      osc.connect(gain);
      gain.connect(c.destination);
      osc.start(t);
      osc.stop(t + 0.15);
      const osc2 = c.createOscillator();
      const g2 = c.createGain();
      osc2.type = "triangle";
      osc2.frequency.value = 2200;
      g2.gain.setValueAtTime(0.08, t);
      g2.gain.exponentialRampToValueAtTime(0.001, t + 0.08);
      osc2.connect(g2);
      g2.connect(c.destination);
      osc2.start(t);
      osc2.stop(t + 0.1);
    } catch (_) {}
  }

  function unlock() {
    try {
      ac();
    } catch (_) {}
  }

  return { playChoiceClick, unlock, setEnabled(v) { enabled = v; } };
})();

window.Sfx = Sfx;

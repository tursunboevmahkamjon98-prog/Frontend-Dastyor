




let ctx: AudioContext | null = null;




const SOUND_PREF_KEY = "dastyor_sound_enabled";
let soundEnabled = true;
if (typeof window !== "undefined") {
  const stored = window.localStorage.getItem(SOUND_PREF_KEY);
  if (stored !== null) soundEnabled = stored === "1";
}

export function isSoundEnabled(): boolean {
  return soundEnabled;
}

export function setSoundEnabled(value: boolean) {
  soundEnabled = value;
  if (typeof window !== "undefined") {
    window.localStorage.setItem(SOUND_PREF_KEY, value ? "1" : "0");
  }
}

function getCtx(): AudioContext | null {
  if (typeof window === "undefined") return null;
  if (!ctx) {
    const Ctor = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctor) return null;
    ctx = new Ctor();
  }
  if (ctx.state === "suspended") ctx.resume();
  return ctx;
}

function tone(freq: number, startOffset: number, duration: number, type: OscillatorType, gain: number) {
  if (!soundEnabled) return;
  const c = getCtx();
  if (!c) return;
  const osc = c.createOscillator();
  const g = c.createGain();
  osc.type = type;
  osc.frequency.value = freq;
  const t0 = c.currentTime + startOffset;
  g.gain.setValueAtTime(0, t0);
  g.gain.linearRampToValueAtTime(gain, t0 + 0.015);
  g.gain.exponentialRampToValueAtTime(0.001, t0 + duration);
  osc.connect(g).connect(c.destination);
  osc.start(t0);
  osc.stop(t0 + duration + 0.02);
}

export const sfx = {
  click: () => tone(520, 0, 0.08, "triangle", 0.18),
  correct: () => {
    tone(660, 0, 0.12, "sine", 0.22);
    tone(880, 0.09, 0.16, "sine", 0.22);
  },
  wrong: () => {
    tone(220, 0, 0.14, "sawtooth", 0.16);
    tone(160, 0.08, 0.18, "sawtooth", 0.16);
  },
  tick: () => tone(880, 0, 0.04, "square", 0.06),
  countdown: () => tone(440, 0, 0.09, "square", 0.15),
  buzz: (player: 1 | 2) => tone(player === 1 ? 740 : 500, 0, 0.1, "square", 0.2),
  levelUp: () => {
    [523, 659, 784, 1047].forEach((f, i) => tone(f, i * 0.09, 0.18, "sine", 0.2));
  },
  win: () => {
    [523, 659, 784, 1047, 1319].forEach((f, i) => tone(f, i * 0.1, 0.28, "sine", 0.22));
  },
  lose: () => {
    [392, 349, 294, 262].forEach((f, i) => tone(f, i * 0.14, 0.3, "sine", 0.18));
  },
  
  
  
  wheelTick: (gain: number) => tone(1200, 0, 0.025, "square", Math.max(0.02, gain * 0.14)),
  wheelStop: () => {
    tone(392, 0, 0.1, "triangle", 0.18);
    tone(523, 0.08, 0.22, "triangle", 0.2);
  },
  
  
  
  
  
  
  laugh: () => {
    if (!soundEnabled) return;
    const c = getCtx();
    if (!c) return;
    const now = c.currentTime;
    const offsets = [0, 0.17, 0.34, 0.53, 0.76];
    offsets.forEach((offset, i) => {
      const t0 = now + offset;
      const osc = c.createOscillator();
      const g = c.createGain();
      osc.type = "sawtooth";
      const startFreq = 460 + i * 15;
      osc.frequency.setValueAtTime(startFreq, t0);
      osc.frequency.exponentialRampToValueAtTime(startFreq * 0.55, t0 + 0.17);
      g.gain.setValueAtTime(0, t0);
      g.gain.linearRampToValueAtTime(0.3, t0 + 0.02);
      g.gain.exponentialRampToValueAtTime(0.001, t0 + 0.18);
      osc.connect(g).connect(c.destination);
      osc.start(t0);
      osc.stop(t0 + 0.2);
    });
  },
  
  
  shuffleSwap: () => tone(300 + Math.random() * 200, 0, 0.08, "triangle", 0.12),
  
  
  
  
  boxOpen: () => {
    [700, 950, 1300].forEach((f, i) => tone(f, i * 0.05, 0.1, "triangle", 0.16));
  },
  
  
  star: () => tone(1567, 0, 0.14, "sine", 0.16),
};

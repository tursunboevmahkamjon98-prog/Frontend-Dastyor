// Tiny synthesized sound effects via WebAudio — no asset files to fetch/host,
// so the game has audio feedback from the first click with zero network
// dependency. One shared AudioContext, created lazily on the first call
// (never at module load) so it's always created inside a real user gesture
// and browsers' autoplay-blocking never triggers.
let ctx: AudioContext | null = null;

// Global mute gate — one flag for every sfx.* call across the game engine
// AND the Random Wheel, backed by localStorage so "🔊 Звук: ВЫКЛ" survives
// a refresh instead of resetting every time a teacher reopens the wheel.
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
  // Random Wheel — a single rapid tick per detent the pointer crosses while
  // spinning (pitch/gain passed in by the caller so it can fade as the
  // wheel decelerates, matching a real prize wheel's clatter).
  wheelTick: (gain: number) => tone(1200, 0, 0.025, "square", Math.max(0.02, gain * 0.14)),
  wheelStop: () => {
    tone(392, 0, 0.1, "triangle", 0.18);
    tone(523, 0.08, 0.22, "triangle", 0.2);
  },
  // BoxGame's jester — five "ha" syllables, each one a real pitch-drop
  // (starts bright, slides down) rather than a flat tone, which is what
  // actually reads as a voice/laugh instead of a chime: a buzzy sawtooth
  // for vocal texture, louder than the other one-shot effects since this
  // one is meant to carry the room, and a slightly widening gap between
  // the last couple of "ha"s the way a real laugh trails off.
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
  // A quick, soft "whoosh" for each shuffle swap — distinct from click/tick
  // so a run of them reads as playful shuffling, not button-mashing.
  shuffleSwap: () => tone(300 + Math.random() * 200, 0, 0.08, "triangle", 0.12),
  // "Қуттиҳои сеҳрнок" box-opening pop — a fast rising three-note sparkle,
  // distinct from correct/levelUp so opening a box reads as its own small
  // event rather than borrowing the "you got it right" sound before the
  // question has even appeared.
  boxOpen: () => {
    [700, 950, 1300].forEach((f, i) => tone(f, i * 0.05, 0.1, "triangle", 0.16));
  },
  // One earned star — a single bright, short chime, cheap enough to fire
  // once per star without ever feeling like a duplicate of `correct`.
  star: () => tone(1567, 0, 0.14, "sine", 0.16),
};

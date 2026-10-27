/* The mascot's vocabulary of states, and what each one means in both of
 * the ways the mascot can be drawn.
 *
 * There are two renderers — a procedural 3D robot and the official 2D
 * poses cut from the brand sheet — and they have to agree, so neither one
 * owns the state list. A state declares its sprite, its rig targets and
 * whether it is a moment or a condition; the renderers read that.
 *
 * `sprite` maps onto the six poses the brand sheet actually ships
 * ("Maskot har xil holatlarda"). There are twelve states and six poses, so
 * some share: the point is that every state has an honest piece of
 * official art behind it, not that each gets its own.
 *
 * `holdMs` marks the states that are moments. A moment plays and then
 * falls back to whatever the screen's resting state is. A mascot left
 * cheering for forty seconds stops reading as encouragement and starts
 * reading as a stuck animation, which is exactly what the previous mascot
 * did while a material generated.
 */

export type MascotState =
  | "idle"
  | "greeting"
  | "thinking"
  | "listening"
  | "speaking"
  | "explaining"
  | "celebrating"
  | "success"
  | "error"
  | "waving"
  | "pointing"
  | "working";

/** The six poses on the brand sheet, by file name in /public/mascot. */
export type MascotPose =
  | "greeting"
  | "thinking"
  | "working"
  | "success"
  | "celebrating"
  | "knowledge";

/** Eye shape drawn on the visor. The character's eyes are curved arcs, so
 *  an expression is which way the arc bends and how open it is. */
export type EyeShape = "happy" | "neutral" | "focused" | "wide" | "low";

export interface MascotStateSpec {
  /** Official pose to show when the 3D renderer is not in use. */
  sprite: MascotPose;
  /** How long a moment lasts before falling back; absent means a condition. */
  holdMs?: number;
  eyes: EyeShape;
  /** Vertical float, in model units and hertz. */
  bobAmp: number;
  bobHz: number;
  /** Resting pose of the rig, in radians. */
  headTilt: number;
  headTurn: number;
  bodyLean: number;
  armL: number;
  armR: number;
  /** One-shot gesture layered on top of the resting pose. */
  gesture?: "wave" | "point" | "cheer" | "tap" | "shrug" | "nod";
  /** Emissive strength of the eyes and chest emblem, 1 = resting. */
  glow: number;
}

export const MASCOT_STATES: Record<MascotState, MascotStateSpec> = {
  idle: {
    sprite: "knowledge",
    eyes: "happy",
    bobAmp: 0.022, bobHz: 0.5,
    headTilt: 0, headTurn: 0, bodyLean: 0,
    armL: 0, armR: 0,
    glow: 1,
  },
  greeting: {
    sprite: "greeting", holdMs: 2600,
    eyes: "happy",
    bobAmp: 0.03, bobHz: 0.8,
    headTilt: -0.05, headTurn: 0.1, bodyLean: 0.02,
    armL: 0, armR: -1.5,
    gesture: "wave",
    glow: 1.25,
  },
  waving: {
    sprite: "greeting", holdMs: 2000,
    eyes: "happy",
    bobAmp: 0.03, bobHz: 0.9,
    headTilt: -0.04, headTurn: 0.08, bodyLean: 0,
    armL: 0, armR: -1.5,
    gesture: "wave",
    glow: 1.2,
  },
  thinking: {
    sprite: "thinking",
    eyes: "focused",
    bobAmp: 0.014, bobHz: 0.35,
    headTilt: 0.16, headTurn: -0.22, bodyLean: 0.04,
    armL: 0.1, armR: -0.95,
    glow: 0.85,
  },
  listening: {
    sprite: "thinking",
    eyes: "wide",
    bobAmp: 0.016, bobHz: 0.45,
    headTilt: -0.08, headTurn: 0.14, bodyLean: 0.03,
    armL: 0, armR: 0,
    glow: 1.15,
  },
  speaking: {
    sprite: "greeting",
    eyes: "happy",
    bobAmp: 0.02, bobHz: 0.6,
    headTilt: -0.03, headTurn: 0, bodyLean: 0,
    armL: -0.18, armR: -0.18,
    gesture: "nod",
    glow: 1.3,
  },
  explaining: {
    sprite: "working",
    eyes: "neutral",
    bobAmp: 0.018, bobHz: 0.5,
    headTilt: -0.02, headTurn: 0.06, bodyLean: 0.01,
    armL: -0.3, armR: -0.7,
    gesture: "point",
    glow: 1.1,
  },
  working: {
    sprite: "working",
    eyes: "focused",
    bobAmp: 0.012, bobHz: 0.42,
    headTilt: 0.22, headTurn: 0.04, bodyLean: 0.06,
    armL: -0.8, armR: -0.8,
    gesture: "tap",
    glow: 0.95,
  },
  celebrating: {
    sprite: "celebrating", holdMs: 2400,
    eyes: "happy",
    bobAmp: 0.055, bobHz: 1.6,
    headTilt: -0.12, headTurn: 0, bodyLean: -0.04,
    armL: -2.1, armR: -2.1,
    gesture: "cheer",
    glow: 1.5,
  },
  success: {
    sprite: "success", holdMs: 2200,
    eyes: "happy",
    bobAmp: 0.03, bobHz: 0.9,
    headTilt: -0.06, headTurn: 0.05, bodyLean: 0,
    armL: 0, armR: -1.1,
    glow: 1.35,
  },
  pointing: {
    sprite: "celebrating", holdMs: 2000,
    eyes: "wide",
    bobAmp: 0.02, bobHz: 0.6,
    headTilt: -0.14, headTurn: 0.12, bodyLean: -0.02,
    armL: 0, armR: -2.3,
    gesture: "point",
    glow: 1.3,
  },
  error: {
    sprite: "thinking", holdMs: 3000,
    eyes: "low",
    bobAmp: 0.01, bobHz: 0.3,
    headTilt: 0.3, headTurn: -0.08, bodyLean: 0.08,
    armL: 0.2, armR: 0.2,
    gesture: "shrug",
    glow: 0.7,
  },
};

export const POSE_SRC: Record<MascotPose, string> = {
  greeting: "/mascot/greeting.webp",
  thinking: "/mascot/thinking.webp",
  working: "/mascot/working.webp",
  success: "/mascot/success.webp",
  celebrating: "/mascot/celebrating.webp",
  knowledge: "/mascot/knowledge.webp",
};

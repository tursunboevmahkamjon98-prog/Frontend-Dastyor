"use client";

import { sfx } from "../game/sound";

// ---------------------------------------------------------------------------
// Sound hooks for "Лабораторияи махфӣ".
//
// Every effect has a named hook, so real audio files can be dropped in later
// by editing ONLY this file — no game or scene code refers to a sound by
// anything other than these names. Today each maps onto the project's
// existing synthesized WebAudio effects (components/game/sound.ts), which
// means audio works from the first click with no asset loading and the
// site-wide mute already applies for free.
// ---------------------------------------------------------------------------

export const labSfx = {
  /** Any UI button. */
  click: () => sfx.click(),
  /** Hovering a reagent bottle — the quietest effect available, since this
   * can fire repeatedly as the pointer crosses the bench. */
  hover: () => sfx.tick(),
  /** A new experiment begins. */
  roundStart: () => sfx.levelUp(),
  /** The chosen bottle lifts off the bench. */
  lift: () => sfx.boxOpen(),
  /** Liquid pouring into the big flask. */
  pour: () => sfx.shuffleSwap(),
  /** The reaction succeeds. */
  success: () => sfx.correct(),
  /** The reaction fails / fizzles out. */
  fizzle: () => sfx.wrong(),
  /** A point award landing. */
  reward: () => sfx.star(),
  /** The final experiment completes. */
  finale: () => sfx.win(),
};

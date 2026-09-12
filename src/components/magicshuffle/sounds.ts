"use client";

import { sfx } from "../game/sound";

// ---------------------------------------------------------------------------
// Sound hooks for "Қуттиҳои сеҳрнок".
//
// Every effect the game needs has a named hook here, so real audio files can
// be dropped in later by changing ONLY this file — no game or component code
// references a sound by anything other than these names. Today each one is
// backed by the project's existing synthesized WebAudio effects (components/
// game/sound.ts), which means the game has audio from the first click with no
// asset loading, no network dependency, and the site's existing global mute
// (dastyor_sound_enabled) already applies to all of it for free.
//
// To swap in real files later: keep the exported names, replace each body
// with a play() call against a preloaded HTMLAudioElement/AudioBuffer, and
// gate it on the same isSoundEnabled() the shared module exports.
// ---------------------------------------------------------------------------

export const magicSfx = {
  /** Any button press (start, next, replay). */
  click: () => sfx.click(),
  /** Hovering a magic box — deliberately very quiet: this can fire many
   * times per second as the mouse crosses the row, so it uses the smallest
   * effect available rather than a distinct new one. */
  hover: () => sfx.tick(),
  /** The clown waves the wand to hide the prize / begin a round. */
  wand: () => sfx.levelUp(),
  /** One box swapping places with another during the shuffle. */
  swoosh: () => sfx.shuffleSwap(),
  /** Each 3 / 2 / 1 beat. */
  countdown: () => sfx.countdown(),
  /** Shuffle has settled — boxes are now clickable. */
  ready: () => sfx.wheelStop(),
  /** A box lid lifting. */
  lidOpen: () => sfx.boxOpen(),
  /** A box lid dropping shut. */
  lidClose: () => sfx.wheelStop(),
  /** Right answer. */
  correct: () => sfx.correct(),
  /** Wrong answer or empty box. */
  wrong: () => sfx.wrong(),
  /** A star / combo bonus landing. */
  reward: () => sfx.star(),
  /** End-of-run fanfare. */
  victory: () => sfx.win(),
};

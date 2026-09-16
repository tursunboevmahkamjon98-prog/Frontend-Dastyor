"use client";

import { sfx } from "../game/sound";

















export const magicSfx = {
  
  click: () => sfx.click(),
  
  hover: () => sfx.tick(),
  
  wand: () => sfx.levelUp(),
  
  swoosh: () => sfx.shuffleSwap(),
  
  countdown: () => sfx.countdown(),
  
  ready: () => sfx.wheelStop(),
  
  lidOpen: () => sfx.boxOpen(),
  
  lidClose: () => sfx.wheelStop(),
  
  correct: () => sfx.correct(),
  
  wrong: () => sfx.wrong(),
  
  reward: () => sfx.star(),
  
  victory: () => sfx.win(),
};

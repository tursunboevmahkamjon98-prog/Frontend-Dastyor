"use client";

import { sfx } from "../game/sound";












export const labSfx = {
  
  click: () => sfx.click(),
  
  hover: () => sfx.tick(),
  
  roundStart: () => sfx.levelUp(),
  
  lift: () => sfx.boxOpen(),
  
  pour: () => sfx.shuffleSwap(),
  
  success: () => sfx.correct(),
  
  fizzle: () => sfx.wrong(),
  
  reward: () => sfx.star(),
  
  finale: () => sfx.win(),
};

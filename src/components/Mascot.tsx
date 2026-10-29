"use client";

import Image from "next/image";

export type MascotMood = "idle" | "writing" | "happy" | "celebrating" | "sad";

const MASCOT_IMAGES: Record<MascotMood, string> = {
  idle: "/mascot/greeting.webp",
  writing: "/mascot/working.webp",
  happy: "/mascot/success.webp",
  celebrating: "/mascot/celebrating.webp",
  sad: "/mascot/thinking.webp",
};

/** Official Dastyor 3D robot poses with a restrained float animation. */
export default function Mascot({
  mood = "idle",
  size = 96,
}: {
  mood?: MascotMood;
  size?: number;
}) {
  return (
    <div
      data-mascot
      aria-hidden="true"
      className="pointer-events-none relative isolate select-none"
      style={{ width: size, height: size * 1.12 }}
    >
      <span className="absolute inset-x-[18%] bottom-[3%] -z-10 h-[24%] rounded-full bg-primary/15 blur-2xl" />
      <Image
        src={MASCOT_IMAGES[mood]}
        alt=""
        width={430}
        height={484}
        priority={size >= 180}
        draggable={false}
        className="mascot-float h-full w-full object-contain drop-shadow-[0_16px_18px_rgba(116,63,57,0.16)]"
      />
    </div>
  );
}

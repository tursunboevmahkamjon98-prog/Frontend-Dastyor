"use client";

/** Fixed dust-mote spots — hardcoded rather than randomised per render so
 * the ambience never re-randomises on a state change (which would read as
 * flickering), and so there's no per-frame JS at all: 8 spans on staggered
 * CSS animations is the whole effect. */
const DUST = [
  { left: "8%", delay: 0, dur: 7 },
  { left: "22%", delay: 2.4, dur: 9 },
  { left: "37%", delay: 1.1, dur: 8 },
  { left: "51%", delay: 3.6, dur: 10 },
  { left: "64%", delay: 0.7, dur: 7.5 },
  { left: "78%", delay: 2.9, dur: 9.5 },
  { left: "88%", delay: 1.8, dur: 8.5 },
  { left: "95%", delay: 4.2, dur: 11 },
];

/** The magical classroom the whole game plays inside. Uses the project's
 * existing illustrated classroom art (chalkboard, desks, blue chairs,
 * books, plants, clock, bunting, sunlit windows are all in the picture) —
 * a real illustration rather than a CSS approximation of one.
 *
 * On top of it: a violet "magic show" wash so the scene reads as enchanted
 * rather than an ordinary lesson, a warm sunbeam from the window side, a
 * floor pool of light under the boxes, and drifting dust motes. A slow Ken
 * Burns drift on the photo itself keeps the room feeling alive without a
 * single frame of JS animation. */
export default function ClassroomScene({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative flex h-full w-full flex-col overflow-hidden bg-[#1b0f3a]">
      {/* eslint-disable-next-line @next/next/no-img-element -- full-bleed static background, not a Next/Image candidate */}
      <img
        src="/game-backgrounds/classroom.png"
        alt=""
        className="pointer-events-none absolute inset-0 h-full w-full object-cover"
        style={{ animation: "game-kenburns 30s ease-in-out infinite alternate" }}
      />

      {/* Magic wash — light enough that the classroom detail still reads. */}
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-[#2e1065]/45 via-[#4c1d95]/35 to-[#1b0f3a]/75" />

      {/* Sunbeam through the window (left side of the art). */}
      <div
        className="pointer-events-none absolute -left-10 top-0 h-full w-1/2 opacity-40"
        style={{
          background: "linear-gradient(115deg, rgba(255,236,180,0.55) 0%, rgba(255,236,180,0) 55%)",
        }}
      />

      {/* Stage pool of light where the boxes sit. */}
      <div
        className="pointer-events-none absolute bottom-0 left-1/2 h-64 w-[min(760px,95%)] -translate-x-1/2 rounded-[50%] opacity-45 blur-3xl"
        style={{ background: "radial-gradient(ellipse at center, rgba(216,180,254,0.75) 0%, rgba(216,180,254,0) 70%)" }}
      />

      {/* Drifting magic dust. */}
      {DUST.map((d, i) => (
        <span
          key={i}
          className="pointer-events-none absolute bottom-1/4 text-amber-200/70"
          style={{
            left: d.left,
            fontSize: 10,
            animation: `mbox-dust ${d.dur}s linear ${d.delay}s infinite`,
          }}
          aria-hidden
        >
          ✦
        </span>
      ))}

      <div className="relative z-10 flex h-full w-full flex-1 flex-col">{children}</div>
    </div>
  );
}

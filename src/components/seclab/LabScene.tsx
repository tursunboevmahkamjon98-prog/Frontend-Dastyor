"use client";

/** Fixed decorative positions — hardcoded rather than randomised per render
 * so the ambience never re-randomises on a state change (which reads as
 * flickering), and so there is no per-frame JS at all: a handful of spans on
 * staggered CSS animations is the whole effect. */
const MOTES = [
  { left: "12%", delay: 0, dur: 9, mx: 20 },
  { left: "27%", delay: 2.6, dur: 11, mx: -14 },
  { left: "44%", delay: 1.2, dur: 10, mx: 24 },
  { left: "61%", delay: 3.8, dur: 12, mx: -18 },
  { left: "76%", delay: 0.9, dur: 9.5, mx: 16 },
  { left: "89%", delay: 2.1, dur: 11.5, mx: -22 },
];

const SMOKE = [
  { left: "18%", delay: 0, dur: 8 },
  { left: "48%", delay: 3, dur: 9.5 },
  { left: "78%", delay: 5.5, dur: 8.5 },
];

/** Shelf jars behind the bench — pure background dressing. */
const SHELF_JARS = ["#38bdf8", "#a855f7", "#34d399", "#fb923c", "#f472b6", "#facc15"];

/** The laboratory the whole game plays inside: a deep, lit room with a
 * back wall of shelves, hanging lamps, a workbench slab in front, drifting
 * vapour and dust in the light.
 *
 * Built entirely from gradients and positioned elements rather than a flat
 * illustration, so it composes with the interactive glassware on top of it
 * and can react to the game (see `flare`, which brightens the lamps on a
 * successful reaction). Depth comes from three stacked planes — back wall,
 * mid shelves, foreground bench — each darker/blurrier the further back it
 * sits. */
export default function LabScene({
  children,
  /** Momentarily brightens the lamps — used when a reaction succeeds. */
  flare = false,
  /** Camera state: pushes in at the start of a round, pulls back for the
   * closing experiment. */
  camera = "idle",
}: {
  children: React.ReactNode;
  flare?: boolean;
  camera?: "idle" | "in" | "out";
}) {
  const cameraAnim =
    camera === "in"
      ? "lab-camera-in 1.3s cubic-bezier(0.22,1,0.36,1)"
      : camera === "out"
        ? "lab-camera-out 3s cubic-bezier(0.22,1,0.36,1) forwards"
        : undefined;

  return (
    <div className="relative flex h-full w-full flex-col overflow-hidden bg-[#070c1a]">
      {/* ---- Plane 1: back wall ---- */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(120% 80% at 50% 0%, #1e3a5f 0%, #12203c 42%, #0a1226 72%, #070c1a 100%)",
        }}
      />
      {/* Faint tiling to read as a tiled lab wall */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.07]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.6) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.6) 1px, transparent 1px)",
          backgroundSize: "64px 64px",
        }}
      />

      {/* ---- Overhead lamps ---- */}
      {[28, 50, 72].map((left, i) => (
        <div key={left} className="pointer-events-none absolute top-0" style={{ left: `${left}%` }}>
          {/* cable + housing */}
          <div className="mx-auto h-10 w-px bg-white/25" />
          <div className="mx-auto h-2.5 w-16 rounded-b-lg bg-gradient-to-b from-slate-300 to-slate-500 shadow-lg" />
          {/* cone of light */}
          <div
            className="mx-auto h-64 w-40 -translate-y-0.5"
            style={{
              background: "linear-gradient(to bottom, rgba(186,230,253,0.5), rgba(186,230,253,0))",
              clipPath: "polygon(42% 0, 58% 0, 100% 100%, 0% 100%)",
              opacity: flare ? 0.95 : 0.35,
              transition: "opacity 0.4s ease",
              animation: flare ? `lab-lamp-flare 0.9s ease-out ${i * 0.08}s` : undefined,
            }}
          />
        </div>
      ))}

      {/* ---- Plane 2: shelves of jars, slightly blurred = further away ---- */}
      <div className="pointer-events-none absolute inset-x-0 top-[16%] flex flex-col gap-10 opacity-70 blur-[1.5px]">
        {[0, 1].map((row) => (
          <div key={row} className="relative mx-auto w-[78%]">
            <div className="flex items-end justify-around px-6">
              {SHELF_JARS.map((c, i) => {
                const h = 26 + ((i * 7 + row * 11) % 18);
                return (
                  <span key={i} className="relative block w-6 rounded-t-md rounded-b-sm bg-white/10" style={{ height: h + 14 }}>
                    {/* liquid inside */}
                    <span
                      className="absolute inset-x-0 bottom-0 rounded-b-sm"
                      style={{ height: h * 0.6, background: c, opacity: 0.55 }}
                    />
                    <span className="absolute inset-y-0 left-1 w-1 rounded-full bg-white/40" />
                  </span>
                );
              })}
            </div>
            <div className="h-1.5 w-full rounded-full bg-gradient-to-b from-amber-900/80 to-amber-950/90 shadow-md" />
          </div>
        ))}
      </div>

      {/* ---- Vapour drifting up from behind the bench ---- */}
      {SMOKE.map((s, i) => (
        <span
          key={i}
          className="pointer-events-none absolute bottom-[26%] h-24 w-24 rounded-full bg-cyan-200/25 blur-2xl"
          style={{ left: s.left, animation: `lab-smoke ${s.dur}s linear ${s.delay}s infinite` }}
          aria-hidden
        />
      ))}

      {/* ---- Dust motes in the lamp light ---- */}
      {MOTES.map((m, i) => (
        <span
          key={i}
          className="pointer-events-none absolute bottom-[30%] h-1 w-1 rounded-full bg-cyan-100"
          style={{
            left: m.left,
            ["--mx" as string]: `${m.mx}px`,
            animation: `lab-mote ${m.dur}s linear ${m.delay}s infinite`,
          }}
          aria-hidden
        />
      ))}

      {/* ---- The scene's contents, under the camera transform ---- */}
      <div
        className="relative z-10 flex h-full w-full flex-1 flex-col"
        style={{ animation: cameraAnim, transformOrigin: "50% 70%" }}
      >
        {children}
      </div>

      {/* ---- Plane 3: the workbench slab, foreground ---- */}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 z-0 h-[22%]">
        {/* worktop edge */}
        <div className="h-3 w-full bg-gradient-to-b from-slate-300 to-slate-500 shadow-[0_-6px_18px_rgba(0,0,0,0.5)]" />
        {/* cabinet front */}
        <div className="h-full w-full bg-gradient-to-b from-[#1b2b45] to-[#0c1526]">
          <div className="mx-auto flex h-full w-[86%] items-start justify-around pt-3">
            {[0, 1, 2, 3].map((i) => (
              <span key={i} className="h-10 w-1/5 rounded-md border border-white/5 bg-white/[0.03]">
                <span className="mx-auto mt-4 block h-1 w-8 rounded-full bg-white/20" />
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Vignette — pulls the eye to the centre of the bench. */}
      <div
        className="pointer-events-none absolute inset-0 z-20"
        style={{ background: "radial-gradient(90% 70% at 50% 55%, transparent 50%, rgba(0,0,0,0.55) 100%)" }}
      />
    </div>
  );
}

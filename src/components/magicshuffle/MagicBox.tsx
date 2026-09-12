"use client";

import { magicSfx } from "./sounds";

/** The ONE look every box wears. Deliberately a single shared theme rather
 * than one per box: if the boxes differed in colour, glow, size or number,
 * a player could learn "the question I want is in the blue one" and the
 * shuffle would stop mattering. Three identical boxes is the whole point —
 * after the lids close there is nothing on screen that distinguishes them.
 *
 * Every value is a literal string rather than a `${color}-500` template:
 * Tailwind's scanner only emits CSS for classes it can see written out in
 * full, so an interpolated name would silently produce no styles. */
export interface BoxTheme {
  /** Lid — lighter than the body so the two read as separate slabs. */
  lid: string;
  lidEdge: string;
  body: string;
  bodyShade: string;
  glow: string;
  ribbon: string;
}

export const BOX_THEME: BoxTheme = {
  lid: "linear-gradient(160deg,#d8b4fe 0%,#a855f7 45%,#7e22ce 100%)",
  lidEdge: "#581c87",
  body: "linear-gradient(165deg,#c084fc 0%,#9333ea 40%,#6b21a8 100%)",
  bodyShade: "#4c1d95",
  glow: "#a855f7",
  ribbon: "#fde68a",
};

/** One magical treasure box. Purely presentational — it knows nothing about
 * rounds or scoring; the parent tells it where to sit (`x`, in px, animated
 * by a CSS transition, which is what makes the shuffle visible), whether
 * it's the absorbing/picked/opening one, and what to call when clicked.
 *
 * Built from stacked gradient slabs (lid + body + front face + ribbon)
 * rather than one flat rounded div, with a separate lid element that can
 * hinge open on its own — a single square can't do the "lid lifts off"
 * beat the opening animation needs. */
export default function MagicBox({
  x,
  swapMs,
  absorbing,
  lidUp,
  lidClosing,
  shuffling,
  dimmed,
  opening,
  opened,
  clickable,
  showPrize,
  lidDelayMs,
  onPick,
  label,
}: {
  /** Horizontal offset in px from the row's left edge. */
  x: number;
  /** How long a position change should take — matches the round's swap
   * pacing so the transition and the logic stay in step. */
  swapMs: number;
  /** Playing the "just swallowed the question" squash+flash. */
  absorbing: boolean;
  /** Lid is held open while the questions are being posted in — every box
   * does this at once, so it reveals nothing about which holds what. */
  lidUp: boolean;
  /** Lid is coming back down after the questions went in. */
  lidClosing: boolean;
  /** Boxes are mid-shuffle: adds the hop/tilt that turns a flat slide into
   * a shell-game move. */
  shuffling: boolean;
  /** A non-chosen box after someone has picked — pushed back visually. */
  dimmed: boolean;
  /** Currently playing its shake → lid-open animation. */
  opening: boolean;
  /** Lid is already off (stays open through the question/feedback beats). */
  opened: boolean;
  clickable: boolean;
  /** Light + stars pour out — only once this box has been opened AND it
   * really was the one holding the question. */
  showPrize: boolean;
  /** Small stagger on the lid opening/closing so the three lids don't move
   * in robotic lockstep. Assigned by SCREEN POSITION, never by box id, and
   * only ever applied during the insert beat — so it can't be used to
   * follow a particular box through the shuffle. */
  lidDelayMs: number;
  onPick: () => void;
  label: string;
}) {
  const theme = BOX_THEME;
  const lidOff = opening || opened || lidUp;

  return (
    <button
      type="button"
      disabled={!clickable}
      onClick={onPick}
      onMouseEnter={() => clickable && magicSfx.hover()}
      aria-label={label}
      // `left-0` is load-bearing: without an explicit inset an absolutely
      // positioned element falls back to its *static* position, which for
      // three sibling buttons is wherever they'd have landed in normal
      // flow — so the translateX below would be measured from three
      // different origins and the row would drift off-centre.
      className={`absolute bottom-0 left-0 h-[132px] w-[104px] origin-bottom transition-[transform,opacity,filter] ${
        clickable ? "cursor-pointer" : "cursor-default"
      }`}
      style={{
        // Position (the shuffle) and the hover lift are combined into one
        // transform, so a box being hovered mid-row still sits at the right
        // x — two competing transform sources would fight each other.
        transform: `translateX(${x}px)`,
        transitionDuration: `${swapMs}ms`,
        transitionTimingFunction: "cubic-bezier(0.34, 1.3, 0.64, 1)",
        opacity: dimmed ? 0.35 : 1,
        filter: dimmed ? "saturate(0.5) brightness(0.7)" : undefined,
        zIndex: opening || opened || absorbing ? 30 : shuffling ? 20 - x / 1000 : 10,
      }}
    >
      {/* Inner wrapper carries every animation EXCEPT the position, so the
          idle float / swap hop never clobbers the translateX above. */}
      <div
        className="relative h-full w-full"
        style={{
          animation: absorbing
            ? "mbox-absorb 0.5s ease-out"
            : opening
              ? "mbox-shake 0.45s ease-in-out"
              : shuffling
                ? `mbox-swap-hop ${swapMs}ms ease-in-out infinite`
                : // No per-box delay: three boxes bobbing on different
                  // phases would give each one a recognisable rhythm to
                  // track through the shuffle. They breathe in unison.
                  "mbox-float 3s ease-in-out infinite",
        }}
      >
        {/* Ground shadow — anchors the box to the classroom floor. */}
        <span
          className="pointer-events-none absolute -bottom-2 left-1/2 h-3 w-[86px] -translate-x-1/2 rounded-[50%] bg-black/45 blur-[6px]"
          aria-hidden
        />

        {/* Magical glow halo. */}
        <span
          className="pointer-events-none absolute inset-x-1 bottom-2 top-6 rounded-[26px] blur-xl"
          style={{
            background: theme.glow,
            animation: `mbox-glow ${absorbing ? "0.5s" : "2.4s"} ease-in-out infinite`,
          }}
          aria-hidden
        />

        {/* Escaping light + stars, only while/after the lid comes off and
            this box actually held the prize. */}
        {/* Light + stars pouring out. During the posting beat EVERY box
            does this (they all receive a question); after a pick, only the
            opened one does. */}
        {(showPrize || lidUp) && lidOff && (
          <>
            <span
              className="pointer-events-none absolute bottom-[62px] left-1/2 h-24 w-16 origin-bottom -translate-x-1/2"
              style={{
                background: `linear-gradient(to top, ${theme.glow}, transparent)`,
                clipPath: "polygon(30% 100%, 70% 100%, 100% 0, 0 0)",
                animation: "mbox-lightbeam 1.2s ease-out forwards",
              }}
              aria-hidden
            />
            {[
              { sx: -34, sy: -78 },
              { sx: 30, sy: -88 },
              { sx: -8, sy: -104 },
              { sx: 46, sy: -58 },
              { sx: -50, sy: -50 },
            ].map((s, i) => (
              <span
                key={i}
                className="pointer-events-none absolute bottom-[68px] left-1/2 text-lg"
                style={{
                  ["--sx" as string]: `${s.sx}px`,
                  ["--sy" as string]: `${s.sy}px`,
                  animation: `mbox-starfly 0.9s ease-out ${i * 0.07}s forwards`,
                }}
                aria-hidden
              >
                ⭐
              </span>
            ))}
          </>
        )}

        {/* ---- Box body ---- */}
        <span
          className="absolute inset-x-0 bottom-0 h-[92px] rounded-b-2xl rounded-t-md shadow-[0_10px_0_rgba(0,0,0,0.25),0_18px_28px_rgba(0,0,0,0.4)]"
          style={{ background: theme.body, border: `2px solid ${theme.bodyShade}` }}
          aria-hidden
        >
          {/* Vertical ribbon down the front. */}
          <span className="absolute inset-y-0 left-1/2 w-4 -translate-x-1/2 opacity-90" style={{ background: theme.ribbon }} />
          {/* Glossy highlight sweep — what makes it read as shiny, not matte. */}
          <span className="absolute inset-y-1 left-2 w-4 rounded-full bg-white/30 blur-[2px]" />
          {/* Question mark on the front face. */}
          <span
            className="absolute inset-0 flex items-center justify-center text-4xl font-black text-white"
            style={{ textShadow: "0 2px 0 rgba(0,0,0,0.35), 0 0 14px rgba(255,255,255,0.6)" }}
          >
            ?
          </span>
        </span>

        {/* ---- Lid ---- separate element so it can hinge away on its own. */}
        <span
          className="absolute inset-x-[-6px] bottom-[86px] h-[30px] rounded-lg shadow-[0_5px_0_rgba(0,0,0,0.25)]"
          style={{
            background: theme.lid,
            border: `2px solid ${theme.lidEdge}`,
            transformOrigin: "center bottom",
            animation: lidOff
              ? "mbox-lid-open 0.55s cubic-bezier(0.3,1.2,0.6,1) forwards"
              : lidClosing
                ? "mbox-lid-close 0.5s cubic-bezier(0.4,0,0.6,1) backwards"
                : undefined,
            animationDelay: opening ? "0.4s" : `${lidDelayMs}ms`,
          }}
          aria-hidden
        >
          <span className="absolute inset-x-0 top-1 h-1.5 bg-white/25" />
          <span className="absolute left-1/2 top-[-10px] h-3 w-8 -translate-x-1/2 rounded-t-full" style={{ background: theme.ribbon }} />
        </span>
      </div>
    </button>
  );
}

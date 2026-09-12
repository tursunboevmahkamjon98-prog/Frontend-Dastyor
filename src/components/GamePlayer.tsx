"use client";

import { useState, type CSSProperties } from "react";
import { Unbounded } from "next/font/google";
import { Users } from "lucide-react";
import { materialsApi } from "@/lib/api";
import { useT } from "@/lib/i18n";
import GameEngine from "./game/GameEngine";
import { TEMPLATE_META } from "./game/types";
import type { Round, GameTemplate } from "./game/types";
import MagicShuffleCard from "./magicshuffle/MagicShuffleCard";
import MagicShuffleGame from "./magicshuffle/MagicShuffleGame";

// A chunky geometric display face for the game-mode wordmarks below — the
// site's own body font (Geist, see app/layout.tsx) is a normal-weight UI
// sans, nothing in it reads as a "game logo" no matter how it's colored.
// Needs its own cyrillic subset (not just latin): every label here
// ("Классика", "Гонка", ...) is Cyrillic, and most bold display faces
// (Baloo 2, Fredoka, Bangers, ...) simply don't ship Cyrillic glyphs at
// all — Unbounded does.
const gameFont = Unbounded({ weight: "800", subsets: ["cyrillic"] });

// No image/illustration and no card/glow behind the text (per explicit
// product ask, after a few rounds of trying both) — the "game logo" look
// comes entirely from typography: a heavy display font, a dark comic-style
// outline (-webkit-text-stroke), an offset drop shadow, a gradient fill,
// and small sharp-edged decorations (never blurred — a blur reads as a
// shadow, which is exactly what got rejected on the race tile). Each
// template gets its own themed decoration below rather than sharing one
// generic treatment, same as RaceLogo's speed-lines/flag.
const GALLERY_ORDER: GameTemplate[] = ["classic", "race", "goldrush", "battle", "classroom"];

// Bigger, chunkier outline + a layered (not blurred) double drop-shadow —
// two solid offset copies read as an extruded/3D logo edge, a blurred one
// would read as the "shadow" already rejected on the race tile.
const OUTLINE =
  "[-webkit-text-stroke:2.5px_#1e1b2e] [filter:drop-shadow(2px_2px_0_#1e1b2e)_drop-shadow(5px_5px_0_rgba(0,0,0,0.35))]";
// Fluid rather than a fixed text-3xl: at 360px the 30px version plus its
// out-of-box decorations (see RaceLogo's speed lines and flag ribbon,
// which are positioned OUTSIDE the wordmark's own box) made the row wider
// than the viewport, which is what put a horizontal scrollbar on the
// whole material page.
const WORDMARK = `${gameFont.className} relative inline-block bg-clip-text text-[clamp(1.35rem,7vw,1.875rem)] uppercase leading-none text-transparent ${OUTLINE}`;

// Idle twinkle/shimmer for decorations (sparkles, coins, speed lines) —
// reuses the Random Wheel's existing "lit bulb" keyframe (opacity+scale
// pulse, see globals.css) rather than inventing a new one. Kept off the
// wordmark text itself (only on the small decoration elements) so it never
// fights the tile button's own hover scale/rotate transform.
function twinkle(delay: number): CSSProperties {
  return { animation: `wheel-bulb-twinkle 1.6s ease-in-out ${delay}s infinite` };
}

/** RACING — forward skew, speed lines instead of a blurred flame glow, a
 * checkered-flag ribbon underneath. */
function RaceLogo({ label }: { label: string }) {
  return (
    <span className="relative inline-block px-4 py-1">
      <span className="pointer-events-none absolute -left-1 top-1/2 flex -translate-x-full -translate-y-1/2 flex-col items-end gap-1" aria-hidden>
        <span className="h-0.5 w-4 rounded-full bg-orange-500/80" style={twinkle(0)} />
        <span className="h-0.5 w-7 rounded-full bg-orange-500" style={twinkle(0.2)} />
        <span className="h-0.5 w-4 rounded-full bg-orange-500/80" style={twinkle(0.4)} />
      </span>
      <span className={`${WORDMARK} skew-x-[-10deg] bg-gradient-to-b from-yellow-300 via-orange-500 to-red-600`}>{label}</span>
      <span
        className="absolute -bottom-1.5 left-1/2 h-3 w-[125%] -translate-x-1/2 rotate-1 border-y border-black/60"
        style={{
          backgroundImage: "repeating-conic-gradient(#111 0% 25%, #f5f5f5 0% 50%)",
          backgroundSize: "10px 10px",
          clipPath: "polygon(3% 0, 97% 0, 100% 50%, 97% 100%, 3% 100%, 0% 50%)",
        }}
        aria-hidden
      />
    </span>
  );
}

/** A small 4-point sparkle — plain CSS (two overlapping rotated bars, no
 * blur), reused by Classic and Goldrush below for their "glint" accents. */
function Sparkle({ className, delay = 0 }: { className?: string; delay?: number }) {
  return (
    <span className={`pointer-events-none absolute ${className}`} style={twinkle(delay)} aria-hidden>
      <span className="absolute inset-0 rotate-45 rounded-full bg-current" style={{ clipPath: "polygon(50% 0, 65% 35%, 100% 50%, 65% 65%, 50% 100%, 35% 65%, 0 50%, 35% 35%)" }} />
    </span>
  );
}

/** КЛАССИКА — violet-to-fuchsia gradient with three twinkling sparkle
 * glints, like a shining star badge rather than a flat fill. */
function ClassicLogo({ label }: { label: string }) {
  return (
    <span className="relative inline-block px-3 py-1">
      <Sparkle className="-left-2 -top-1 h-3.5 w-3.5 text-yellow-300" delay={0} />
      <Sparkle className="-bottom-1 -right-2 h-3 w-3 text-yellow-300" delay={0.5} />
      <Sparkle className="right-1/3 -top-2 h-2 w-2 text-yellow-200" delay={0.9} />
      <span className={`${WORDMARK} bg-gradient-to-b from-fuchsia-300 via-violet-500 to-violet-700`}>{label}</span>
    </span>
  );
}

/** ЗОЛОТАЯ ЛИХОРАДКА — amber-to-brown gradient with small twinkling gold
 * coin dots scattered around it instead of a glow. */
function GoldrushLogo({ label }: { label: string }) {
  return (
    <span className="relative inline-block px-3 py-1">
      <span className="pointer-events-none absolute -left-2 top-0 h-3.5 w-3.5 rounded-full border border-amber-700 bg-yellow-300" style={twinkle(0.1)} aria-hidden />
      <span className="pointer-events-none absolute -right-2 top-1/2 h-2.5 w-2.5 -translate-y-1/2 rounded-full border border-amber-700 bg-yellow-300" style={twinkle(0.6)} aria-hidden />
      <span className="pointer-events-none absolute -right-1 -bottom-2 h-2 w-2 rounded-full border border-amber-700 bg-yellow-200" style={twinkle(1)} aria-hidden />
      <Sparkle className="-bottom-1.5 left-1/3 h-2.5 w-2.5 text-yellow-200" delay={0.3} />
      <span className={`${WORDMARK} bg-gradient-to-b from-yellow-300 via-amber-500 to-amber-800`}>{label}</span>
    </span>
  );
}

/** БИТВА — dark red gradient with a sharp-edged (unblurred), gently
 * pulsing impact burst behind it, standing in for a clash-of-swords spark. */
function BattleLogo({ label }: { label: string }) {
  return (
    <span className="relative inline-block px-3 py-1">
      <span
        className="pointer-events-none absolute -inset-2.5 -z-10 bg-red-500"
        style={{
          clipPath:
            "polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%)",
          animation: "wheel-bulb-twinkle 1.4s ease-in-out infinite",
        }}
        aria-hidden
      />
      <span className={`${WORDMARK} bg-gradient-to-b from-red-400 via-red-600 to-red-900`}>{label}</span>
    </span>
  );
}

/** УРОК — green-to-emerald gradient with a dashed chalk-underline instead
 * of a solid accent bar, plus a small twinkling "chalk dust" glint. */
function ClassroomLogo({ label }: { label: string }) {
  return (
    <span className="relative inline-block px-3 py-1">
      <Sparkle className="-right-2 -top-1.5 h-2.5 w-2.5 text-white" delay={0.4} />
      <span className={`${WORDMARK} bg-gradient-to-b from-emerald-300 via-emerald-500 to-emerald-800`}>{label}</span>
      <span className="absolute -bottom-1.5 left-1/2 h-0 w-[85%] -translate-x-1/2 border-t-2 border-dashed border-white" aria-hidden />
    </span>
  );
}

const LOGO_COMPONENT: Record<GameTemplate, (props: { label: string }) => React.JSX.Element> = {
  classic: ClassicLogo,
  race: RaceLogo,
  goldrush: GoldrushLogo,
  battle: BattleLogo,
  classroom: ClassroomLogo,
};

const GALLERY_ROTATE: Record<GameTemplate, string> = {
  classic: "-rotate-3",
  race: "rotate-2",
  goldrush: "-rotate-2",
  battle: "rotate-3",
  classroom: "-rotate-2",
};

/** Entry point for the "Igra" material — mounted by the material viewer
 * (dashboard/materials/[type]/[id]) same as any other type's body renderer,
 * but a game earns none of the PDF/print treatment the others get (see that
 * page's downloadFormats comment) so this is the entire view for that type.
 *
 * Two states: an inline "cover" card sitting in the page's normal layout
 * (so the material page around it — header, favorite/share — still reads
 * as a page), and, once launched, a fixed full-viewport overlay housing the
 * actual start/solo/duel/result state machine (GameEngine) — "a real game
 * screen," not a widget embedded in the site chrome, per product ask.
 * Closing the overlay drops back to the cover rather than navigating away,
 * so "Играть снова" round-trips without ever leaving this page.
 *
 * `content` is kept as local state (seeded from the prop) rather than read
 * straight from it, because a reroll (see `regenerate` below) replaces it
 * in place — a second pupil playing the same lesson's game gets a fresh
 * 12 rounds instead of the exact questions the first pupil just saw,
 * without the teacher having to leave this page and create a whole new
 * material for it. */
export default function GamePlayer({
  content: initialContent,
  materialId,
}: {
  content: Record<string, unknown>;
  materialId: string;
}) {
  const t = useT();
  const [launched, setLaunched] = useState(false);
  const [launchedShuffle, setLaunchedShuffle] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<GameTemplate>("classic");
  const [content, setContent] = useState(initialContent);
  const [regenerating, setRegenerating] = useState(false);

  const description = content.description as string | undefined;
  const rounds = ((content.rounds as Round[] | undefined) ?? []).filter(
    (r) => r && typeof r === "object" && "type" in r
  );
  const title = (content.title as string | undefined) ?? t("game.defaultTitle");


  async function regenerate() {
    setRegenerating(true);
    try {
      const language = typeof content.language === "string" ? content.language : "Русский";
      const updated = await materialsApi.rerollGame(materialId, { language });
      const raw = updated.game_json ?? "{}";
      try {
        setContent(JSON.parse(raw));
      } catch {
        // leave the old rounds in place if the response somehow isn't valid JSON
      }
    } finally {
      setRegenerating(false);
    }
  }

  if (rounds.length === 0) {
    return <p className="text-sm text-text-secondary">{t("game.noRounds")}</p>;
  }

  function pick(tpl: GameTemplate) {
    setSelectedTemplate(tpl);
    setLaunched(true);
  }

  return (
    <>
      <div className="mb-4 text-center">
        <h3 className="text-lg font-extrabold text-text-primary">{title}</h3>
        {description && <p className="mx-auto mt-1 max-w-sm text-sm text-text-secondary">{description}</p>}
        <p className="mt-1.5 flex items-center justify-center gap-1.5 text-xs font-medium text-text-tertiary">
          <Users className="h-3.5 w-3.5" />
          {rounds.length} {t("game.roundsCount")} · {t("game.playTogetherHint")}
        </p>
      </div>

      <p className="mb-2.5 text-xs font-bold uppercase tracking-wide text-text-tertiary">{t("game.chooseTemplate")}</p>
      <div className="mb-8 flex flex-wrap items-end justify-center gap-x-6 gap-y-8 overflow-x-clip px-2 py-4 sm:gap-x-12 sm:gap-y-10">
        {GALLERY_ORDER.map((tpl) => {
          const meta = TEMPLATE_META[tpl];
          const Logo = LOGO_COMPONENT[tpl];
          return (
            <button
              key={tpl}
              onClick={() => pick(tpl)}
              // Only scale on hover, never de-rotate — resetting rotate-N
              // to rotate-0 on :hover shifts the whole tile several pixels
              // right as the mouse arrives, which can carry the pointer
              // off the tile before the click actually lands (real bug:
              // a click that visually landed on the tile registered on
              // whatever was newly underneath it instead).
              className={`origin-center scale-100 transition-transform duration-150 hover:scale-105 active:scale-95 ${GALLERY_ROTATE[tpl]}`}
            >
              <Logo label={meta.label} />
            </button>
          );
        })}
      </div>

      {/* A separate game, not another template skin — its loop is
          watch-the-shuffle → pick a box → answer, which shares no phase
          structure with the engine's straight question runs above. Always
          offered: it can source questions from this material, from the
          teacher typing them, or from the AI (see SetupScreen). */}
      <div className="mb-8 flex justify-center">
        <MagicShuffleCard onPlay={() => setLaunchedShuffle(true)} />
      </div>

      {launchedShuffle && (
        <div className="fixed inset-0 z-[200] bg-[#1b0f3a]">
          <MagicShuffleGame
            defaultSubject={content.subject as string | undefined}
            defaultTopic={title}
            defaultGrade={content.grade as string | undefined}
            onClose={() => setLaunchedShuffle(false)}
          />
        </div>
      )}

      {launched && (
        <div className="fixed inset-0 z-[200] bg-[#1e1033]">
          <GameEngine
            title={title}
            rounds={rounds}
            materialId={materialId}
            initialTemplate={selectedTemplate}
            onClose={() => setLaunched(false)}
            onRegenerate={regenerate}
            regenerating={regenerating}
          />
        </div>
      )}
    </>
  );
}

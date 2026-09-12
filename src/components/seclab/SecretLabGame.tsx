"use client";

import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import ExplanationCard from "./ExplanationCard";
import LabHUD from "./LabHUD";
import LabResultScreen from "./LabResultScreen";
import LabScene from "./LabScene";
import LabSetupScreen from "./LabSetupScreen";
import ReactionFlask from "./ReactionFlask";
import ReagentBottle from "./ReagentBottle";
import { LabQuestion, REAGENT_COLORS, reactionConfig } from "./types";
import { useLabGame } from "./useLabGame";

/** Horizontal spacing between reagent slots, used to work out how far the
 * chosen bottle has to travel to reach the flask. Matches the flex gap +
 * bottle width below; kept as constants because the flight is a CSS
 * transform and can't read layout. */
const SLOT_W_DESKTOP = 108;
const SLOT_W_MOBILE = 88;
/** How far above the bench the flask sits relative to the bottles. */
const FLASK_RISE = 132;

/** "Лабораторияи махфӣ" — a secret-laboratory quiz. Each round the AI asks a
 * question and the bench fills with reagent bottles, one per answer option.
 * Picking one physically carries it to the big flask and pours it in; the
 * reaction that follows is the feedback.
 *
 * All rules and timing live in useLabGame; this file is composition and
 * layout. The one thing it owns is the responsive slot width, since that's a
 * presentation concern the logic must not know about. */
export default function SecretLabGame({
  defaultSubject,
  defaultTopic,
  defaultGrade,
  onClose,
}: {
  defaultSubject?: string;
  defaultTopic?: string;
  defaultGrade?: string;
  onClose: () => void;
}) {
  const game = useLabGame();
  const { user } = useAuth();
  const playerName = user?.full_name?.trim() || "Меҳмон";

  /** Kept so "Аз нав бозӣ кардан" can replay the same set instead of
   * silently spending another AI call. */
  const [lastSet, setLastSet] = useState<LabQuestion[]>([]);

  const [slotW, setSlotW] = useState(SLOT_W_DESKTOP);
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 640px)");
    const apply = () => setSlotW(mq.matches ? SLOT_W_DESKTOP : SLOT_W_MOBILE);
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  // ---- Setup / brewing ----
  if (game.phase === "setup" || game.phase === "brewing") {
    return (
      <LabScene>
        <CloseButton onClose={onClose} />
        <LabSetupScreen
          defaultSubject={defaultSubject}
          defaultTopic={defaultTopic}
          defaultGrade={defaultGrade}
          onBrewingStart={game.setBrewing}
          onReady={(qs) => {
            setLastSet(qs);
            game.start(qs);
          }}
        />
      </LabScene>
    );
  }

  // ---- Result ----
  if (game.phase === "result") {
    return (
      <LabScene>
        <CloseButton onClose={onClose} />
        <LabResultScreen
          score={game.score}
          correctCount={game.correctCount}
          wrongCount={game.wrongCount}
          roundsPlayed={game.correctCount + game.wrongCount}
          outOfLives={game.lives <= 0}
          onReplay={() => game.start(lastSet)}
          onExit={onClose}
        />
      </LabScene>
    );
  }

  const q = game.question;
  const cfg = reactionConfig(game.round, game.totalRounds);
  const optionCount = q?.options.length ?? 0;

  // Flask visual state follows the game phase.
  const flaskState =
    game.phase === "pouring"
      ? "filling"
      : game.phase === "finale"
        ? "finale"
        : game.phase === "reacting" || game.phase === "explaining"
          ? game.answerCorrect
            ? "success"
            : "fail"
          : "idle";

  // Tint = the colour of whichever reagent went in. Falls back to the first
  // colour before anything has been poured.
  const tint = REAGENT_COLORS[(game.picked ?? 0) % REAGENT_COLORS.length].liquid;

  const camera = game.phase === "roundIntro" ? "in" : game.phase === "finale" ? "out" : "idle";
  const flare = (game.phase === "reacting" && game.answerCorrect === true) || game.phase === "finale";

  /** Where the bottle at `index` has to travel to reach the flask: the flask
   * sits centred above the row, so the delta is the bottle's own offset from
   * the row centre, negated, plus the rise. */
  function flyTo(index: number) {
    const centre = (optionCount - 1) / 2;
    return { x: (centre - index) * slotW, y: -FLASK_RISE };
  }

  return (
    <LabScene flare={flare} camera={camera}>
      <CloseButton onClose={onClose} />
      <LabHUD
        playerName={playerName}
        round={game.round}
        totalRounds={game.totalRounds}
        score={game.score}
        lives={game.lives}
        scorePops={game.scorePops}
      />

      {/* Column layout, not absolute positioning, for the three stacked
          zones: the question panel reserves its own height at the top, the
          flask takes whatever is left in the middle, and the bench sits at
          the bottom. Floating the panel over the scene instead had it
          landing on top of the flask whenever the question ran long. */}
      <div className="relative flex h-full w-full flex-1 flex-col items-center overflow-hidden px-3 pb-24 pt-8 sm:pb-28 sm:pt-12">
        {/* ---- "Таҷрибаи нав!" banner ---- */}
        {game.phase === "roundIntro" && (
          <div className="pointer-events-none absolute inset-0 z-40 flex items-center justify-center">
            <span
              className="rounded-2xl border border-cyan-300/40 bg-[#0c1526]/80 px-7 py-3 text-2xl font-black text-cyan-100 shadow-[0_0_40px_rgba(56,189,248,0.5)] backdrop-blur-md sm:text-3xl"
              style={{ animation: "lab-panel-in 0.6s cubic-bezier(0.22,1,0.36,1)" }}
            >
              Таҷрибаи нав! 🧪
            </span>
          </div>
        )}

        {/* ---- Question panel ---- floating glass, the focus of the screen. */}
        {q && game.phase !== "roundIntro" && (
          <div
            className="pointer-events-none z-30 flex w-full shrink-0 justify-center"
            style={{ animation: "lab-panel-in 0.55s cubic-bezier(0.22,1,0.36,1)" }}
          >
            <div className="relative no-scrollbar max-h-[22vh] w-full max-w-2xl overflow-y-auto overflow-x-hidden rounded-[26px] border border-white/20 bg-white/[0.08] px-5 py-3 text-center shadow-[0_20px_50px_rgba(0,0,0,0.55)] backdrop-blur-xl sm:py-4">
              <span
                className="pointer-events-none absolute -inset-px rounded-[26px] opacity-60"
                style={{ background: "linear-gradient(135deg, rgba(56,189,248,0.35), transparent 60%)" }}
                aria-hidden
              />
              <p className="relative text-[10px] font-black uppercase tracking-[0.2em] text-cyan-300/80">Савол</p>
              <p className="relative mt-1.5 text-sm font-black leading-snug text-white sm:text-lg">{q.question}</p>
            </div>
          </div>
        )}

        {/* ---- Success banner ---- */}
        {game.phase === "reacting" && game.answerCorrect === true && (
          <div className="pointer-events-none absolute inset-x-0 top-[42%] z-40 flex flex-col items-center gap-1.5 px-4">
            <span
              className="rounded-2xl bg-gradient-to-br from-emerald-400 to-green-600 px-6 py-2.5 text-xl font-black text-white shadow-[0_0_36px_rgba(52,211,153,0.7)]"
              style={{ animation: "mascot-pop 0.5s ease-out" }}
            >
              Офарин! 🎉
            </span>
            <span className="text-sm font-bold text-emerald-200" style={{ animation: "lab-panel-in 0.5s ease-out 0.15s backwards" }}>
              Ҷавоби дуруст! ✅
            </span>
            <span
              className="mt-0.5 text-xs font-semibold text-emerald-100/80"
              style={{ animation: "lab-panel-in 0.5s ease-out 0.3s backwards" }}
            >
              Таҷриба бомуваффақият анҷом ёфт!
            </span>
          </div>
        )}

        {/* Elastic spacer: soaks up whatever height is left between the
            question panel and the bench, so the bench group below keeps its
            natural size instead of being squeezed. */}
        <div className="min-h-0 flex-1" />

        {/* ---- The flask, standing on the bench ---- */}
        <div className="relative z-20 flex shrink-0 origin-bottom flex-col items-center [@media(max-height:760px)]:scale-[0.7]">
          <ReactionFlask state={flaskState} config={cfg} tint={tint} />
        </div>

        {/* ---- Prompt above the reagents ---- */}
        {game.phase === "question" && (
          <p
            className="relative z-20 mb-1.5 mt-1.5 shrink-0 text-[11px] font-black uppercase tracking-widest text-cyan-200/90 sm:text-sm"
            style={{ animation: "lab-panel-in 0.5s ease-out" }}
          >
            Реагентро интихоб кунед!
          </p>
        )}

        {/* ---- The reagent bottles: one per answer option ---- */}
        {q && game.phase !== "finale" && (
          <div className="relative z-20 flex shrink-0 origin-bottom items-end justify-center gap-2 sm:gap-4 [@media(max-height:760px)]:scale-[0.78]">
            {q.options.map((opt, i) => (
              <ReagentBottle
                key={i}
                index={i}
                label={opt}
                interactive={game.phase === "question"}
                flying={game.picked === i && game.phase === "pouring"}
                dimmed={game.picked !== null && game.picked !== i && game.phase !== "question"}
                reveal={
                  // Once the reaction has played, the bench itself shows the
                  // verdict: the right bottle greens, a wrong pick reds.
                  game.phase === "reacting" || game.phase === "explaining"
                    ? i === q.correctIndex
                      ? "correct"
                      : game.picked === i
                        ? "wrong"
                        : null
                    : null
                }
                flyTo={flyTo(i)}
                onPick={() => game.pickReagent(i)}
              />
            ))}
          </div>
        )}

        {/* ---- Finale ---- */}
        {game.phase === "finale" && (
          <div className="pointer-events-none absolute inset-0 z-40 flex flex-col items-center justify-center gap-2">
            <span className="text-5xl" style={{ animation: "mbox-trophy-in 0.9s cubic-bezier(0.3,1.4,0.6,1)" }}>
              ✨
            </span>
            <span
              className="rounded-2xl border border-cyan-300/40 bg-[#0c1526]/80 px-6 py-3 text-xl font-black text-cyan-100 shadow-[0_0_50px_rgba(56,189,248,0.6)] backdrop-blur-md sm:text-2xl"
              style={{ animation: "lab-panel-in 0.7s cubic-bezier(0.22,1,0.36,1) 0.2s backwards" }}
            >
              Таҷрибаи бузург анҷом ёфт!
            </span>
          </div>
        )}

        {/* ---- Explanation ---- wrong answers only. */}
        {game.phase === "explaining" && q && (
          <ExplanationCard question={q} picked={game.picked} onContinue={game.next} />
        )}
      </div>
    </LabScene>
  );
}

function CloseButton({ onClose }: { onClose: () => void }) {
  return (
    <button
      type="button"
      onClick={onClose}
      aria-label="Пӯшидан"
      className="absolute right-3 top-3 z-50 flex h-10 w-10 items-center justify-center rounded-xl border border-white/15 bg-white/10 text-white backdrop-blur-md transition hover:bg-white/20"
    >
      <X className="h-4 w-4" />
    </button>
  );
}

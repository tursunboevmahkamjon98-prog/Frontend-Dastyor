"use client";

import { useEffect, useRef, useState } from "react";
import { Zap, GripVertical } from "lucide-react";
import { Round, BASE_TIME_SECONDS, DuelResult, GameTemplate, P1_KEYS, P2_KEYS } from "./types";
import { DuelHud, TemplateScene } from "./templates";
import { sfx } from "./sound";

type Side = 1 | 2;

// A matched pair's drawn connector — same shape/technique as SoloGame.tsx's
// MatchLine (see that file's doc comment); kept as its own copy here since
// the two screens don't otherwise share a component module.
interface MatchLine {
  key: number;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

// Every per-side Tailwind class spelled out literally (not built from a
// `${accent}-100` template) — Tailwind's JIT scanner only picks up classes
// that appear as literal substrings in the source, so an interpolated
// accent name would silently generate no CSS at all. See THEME below.
interface SideTheme {
  halfBg: string;
  badgeBg: string;
  badgeText: string;
  idle: string;
  active: string;
  gradient: string;
}
const THEME: Record<Side, SideTheme> = {
  1: {
    halfBg: "bg-sky-950/20",
    badgeBg: "bg-sky-500/20",
    badgeText: "text-sky-300",
    idle: "border-sky-100 bg-sky-50/50",
    active: "border-sky-400 bg-sky-100",
    gradient: "from-sky-500 to-sky-600",
  },
  2: {
    halfBg: "bg-pink-950/20",
    badgeBg: "bg-pink-500/20",
    badgeText: "text-pink-300",
    idle: "border-pink-100 bg-pink-50/50",
    active: "border-pink-400 bg-pink-100",
    gradient: "from-pink-500 to-pink-600",
  },
};

/** Two kids, one screen, one question at a time — both sides see the exact
 * same round and race to answer on their own half (see product decision:
 * "Duel/Buzzer"). The screen splits left/right on anything roomy enough for
 * two hands (tablet/desktop/landscape phone) and top/bottom on a narrow
 * portrait phone, since a literal side-by-side split there would leave each
 * zone too cramped to tap accurately.
 *
 * Touch needs nothing special for simultaneous presses: each half's buttons
 * are separate DOM elements, and two fingers landing on two different
 * elements at once already dispatch two independent pointer events — no
 * custom multi-touch handling required. Keyboard gets an explicit split
 * instead (P1_KEYS/P2_KEYS, far enough apart on a real keyboard that two
 * hands don't collide) since two keydowns for the same physical key can't
 * otherwise be told apart.
 *
 * DuelGame itself only owns what must survive across rounds — the two
 * scores and which round we're on. Everything scoped to a single round
 * (the countdown, who's locked out, the winner banner) lives in DuelRound
 * below, which React remounts fresh every round via `key={index}` — that
 * remount IS the reset, so no effect-driven "resync state to the new round"
 * logic is needed anywhere here. */
export default function DuelGame({
  rounds,
  template,
  onFinish,
}: {
  rounds: Round[];
  template: GameTemplate;
  onFinish: (result: DuelResult) => void;
}) {
  const [index, setIndex] = useState(0);
  const [scoreP1, setScoreP1] = useState(0);
  const [scoreP2, setScoreP2] = useState(0);

  function handleRoundDone(winner: Side | 0) {
    const newP1 = winner === 1 ? scoreP1 + 1 : scoreP1;
    const newP2 = winner === 2 ? scoreP2 + 1 : scoreP2;
    if (winner !== 0) {
      if (winner === 1) setScoreP1(newP1);
      else setScoreP2(newP2);
    }
    if (index + 1 >= rounds.length) {
      onFinish({ mode: "duel", scoreP1: newP1, scoreP2: newP2, winner: newP1 === newP2 ? 0 : newP1 > newP2 ? 1 : 2 });
    } else {
      setIndex((i) => i + 1);
    }
  }

  return (
    <DuelRound
      key={index}
      round={rounds[index]}
      index={index}
      total={rounds.length}
      scoreP1={scoreP1}
      scoreP2={scoreP2}
      template={template}
      onDone={handleRoundDone}
    />
  );
}

function DuelRound({
  round,
  index,
  total,
  scoreP1,
  scoreP2,
  template,
  onDone,
}: {
  round: Round;
  index: number;
  total: number;
  scoreP1: number;
  scoreP2: number;
  template: GameTemplate;
  onDone: (winner: Side | 0) => void;
}) {
  const timeBudget = BASE_TIME_SECONDS[round.type];
  const [timeLeft, setTimeLeft] = useState(timeBudget);
  const [banner, setBanner] = useState<{ winner: Side | 0 } | null>(null);
  const resolvedRef = useRef(false);

  function award(winner: Side | 0) {
    if (resolvedRef.current) return;
    resolvedRef.current = true;
    if (winner === 1) sfx.buzz(1);
    else if (winner === 2) sfx.buzz(2);
    setBanner({ winner });
    setTimeout(() => onDone(winner), 1300);
  }

  useEffect(() => {
    if (banner) return;
    if (timeLeft <= 0) {
      award(0);
      return;
    }
    const t = setTimeout(() => setTimeLeft((s) => s - 1), 1000);
    if (timeLeft <= 3) sfx.tick();
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeLeft, banner]);

  return (
    <TemplateScene template={template}>
    <div className="relative flex h-full w-full flex-col">
      <div className="z-10 bg-black/20 backdrop-blur-sm">
        <DuelHud
          template={template}
          scoreP1={scoreP1}
          scoreP2={scoreP2}
          totalRounds={total}
          roundLabel={
            <>
              <p className="text-[11px] font-medium text-white/50">
                Раунд {index + 1} / {total}
              </p>
              <p className="text-sm font-extrabold text-white">{timeLeft}с</p>
            </>
          }
        />
      </div>

      <div className="relative flex min-h-0 flex-1 flex-col overflow-hidden sm:flex-row">
        <PlayerHalf side={1} round={round} locked={banner !== null} timeLeft={timeLeft} onWin={() => award(1)} />
        <div className="h-px w-full bg-white/10 sm:h-auto sm:w-px" />
        <PlayerHalf side={2} round={round} locked={banner !== null} timeLeft={timeLeft} onWin={() => award(2)} />

        {banner && (
          <div className="pointer-events-none absolute inset-0 z-20 flex items-center justify-center">
            <div className="mx-4 max-w-[calc(100vw-2rem)] rounded-2xl bg-white px-5 py-3 text-center shadow-2xl sm:px-7 sm:py-4" style={{ animation: "mascot-pop 0.45s ease-out" }}>
              <p className="text-base font-extrabold text-[#6d28d9] sm:text-xl">
                {banner.winner === 0 ? "Никто не успел!" : `Очко Игроку ${banner.winner}! ⚡`}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
    </TemplateScene>
  );
}

function PlayerHalf({
  side,
  round,
  locked,
  timeLeft,
  onWin,
}: {
  side: Side;
  round: Round;
  locked: boolean;
  timeLeft: number;
  onWin: () => void;
}) {
  const theme = THEME[side];
  const keys = side === 1 ? P1_KEYS : P2_KEYS;

  return (
    <div
      className={`relative flex min-h-0 flex-1 flex-col items-center justify-center gap-2 overflow-y-auto px-3 py-3 sm:gap-4 sm:px-4 sm:py-6 ${theme.halfBg}`}
    >
      <span className={`absolute left-3 top-3 rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide ${theme.badgeBg} ${theme.badgeText}`}>
        Игрок {side}
      </span>
      <div className="w-full max-w-sm" style={{ animation: "game-round-in 0.3s ease-out" }}>
        <DuelStage round={round} keys={keys} locked={locked} timeLeft={timeLeft} onWin={onWin} theme={theme} />
      </div>
    </div>
  );
}

function DuelStage({
  round,
  keys,
  locked,
  timeLeft,
  onWin,
  theme,
}: {
  round: Round;
  keys: string[];
  locked: boolean;
  timeLeft: number;
  onWin: () => void;
  theme: SideTheme;
}) {
  const [picked, setPicked] = useState<number | boolean | null>(null);
  const [wrongFlash, setWrongFlash] = useState(false);

  function tryAnswer(correct: boolean, chosen: number | boolean) {
    if (locked || picked !== null) return;
    if (correct) {
      setPicked(chosen);
      onWin();
    } else {
      setWrongFlash(true);
      sfx.wrong();
      setTimeout(() => setWrongFlash(false), 300);
      setPicked(chosen); // locks this side out of the round, doesn't award
    }
  }

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const key = e.key.toLowerCase();
      // Speed round has no options to index into — its own key (keys[0],
      // same one that doubles as the buzz button's on-screen hint) just
      // buzzes directly, same as tapping it.
      if (round.type === "speed") {
        if (key === keys[0] && !locked) onWin();
        return;
      }
      const idx = keys.indexOf(key);
      if (idx === -1) return;
      if (round.type === "quiz" && idx < round.options.length) tryAnswer(idx === round.correct_index, idx);
      if (round.type === "true_false" && idx < 2) {
        const val = idx === 0;
        tryAnswer(val === round.answer, val);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [locked, picked]);

  // Same last-3-seconds heartbeat SoloGame's Stage uses — only quiz/
  // true_false actually fail on timeout, so only they pulse.
  const urgent = (round.type === "quiz" || round.type === "true_false") && !locked && timeLeft <= 3;
  const cardCls = `rounded-2xl bg-white/95 p-4 shadow-lg ${wrongFlash ? "animate-[game-shake_0.3s_ease-in-out]" : ""}`;
  const cardStyle = urgent ? { animation: "game-urgent-pulse 0.6s ease-in-out infinite" } : undefined;

  if (round.type === "quiz") {
    return (
      <div className={cardCls} style={cardStyle}>
        <p className="mb-3 text-center text-sm font-bold text-[#3b0764]">{round.question}</p>
        <div className="space-y-2">
          {round.options.map((opt, j) => (
            <button
              key={j}
              disabled={locked || picked !== null}
              onClick={() => tryAnswer(j === round.correct_index, j)}
              className={`flex w-full items-center gap-2 rounded-xl border-2 px-3 py-2 text-left text-xs font-semibold transition disabled:opacity-70 ${
                picked === j
                  ? j === round.correct_index
                    ? "border-emerald-400 bg-emerald-50 text-emerald-700"
                    : "border-red-400 bg-red-50 text-red-700"
                  : `${theme.idle} text-[#3b0764]`
              }`}
            >
              <kbd className="rounded bg-white px-1.5 py-0.5 text-[9px] font-bold uppercase text-gray-500 shadow-sm">{keys[j]}</kbd>
              {opt}
            </button>
          ))}
        </div>
      </div>
    );
  }

  if (round.type === "true_false") {
    return (
      <div className={cardCls} style={cardStyle}>
        <p className="mb-3 text-center text-sm font-bold text-[#3b0764]">{round.statement}</p>
        <div className="flex gap-2">
          {[true, false].map((val, j) => (
            <button
              key={String(val)}
              disabled={locked || picked !== null}
              onClick={() => tryAnswer(val === round.answer, val)}
              className={`flex-1 rounded-xl border-2 py-2.5 text-xs font-bold transition disabled:opacity-70 ${
                picked === val
                  ? val === round.answer
                    ? "border-emerald-400 bg-emerald-50 text-emerald-700"
                    : "border-red-400 bg-red-50 text-red-700"
                  : `${theme.idle} text-[#3b0764]`
              }`}
            >
              <kbd className="mr-1 rounded bg-white px-1.5 py-0.5 text-[9px] font-bold uppercase text-gray-500 shadow-sm">{keys[j]}</kbd>
              {val ? "Верно" : "Неверно"}
            </button>
          ))}
        </div>
      </div>
    );
  }

  if (round.type === "matching") return <DuelMatching round={round} locked={locked} onWin={onWin} cardCls={cardCls} theme={theme} />;
  if (round.type === "order") return <DuelOrder round={round} locked={locked} onWin={onWin} cardCls={cardCls} theme={theme} />;

  // Speed round: pure buzzer, no correctness check (matches SoloGame's
  // treatment of this type — see its doc comment).
  return (
    <div className={cardCls}>
      <p className="mb-3 text-center text-sm font-bold text-[#3b0764]">{round.question}</p>
      <button
        disabled={locked}
        onClick={onWin}
        className={`mx-auto flex items-center gap-2 rounded-xl bg-gradient-to-r ${theme.gradient} px-4 py-2.5 text-xs font-bold text-white shadow-md disabled:opacity-60`}
      >
        <Zap className="h-3.5 w-3.5" />
        Buzz! ({keys[0].toUpperCase()})
      </button>
    </div>
  );
}

function DuelMatching({
  round,
  locked,
  onWin,
  cardCls,
  theme,
}: {
  round: Extract<Round, { type: "matching" }>;
  locked: boolean;
  onWin: () => void;
  cardCls: string;
  theme: SideTheme;
}) {
  // Lazy useState initializer rather than useMemo: this component is
  // already fresh-mounted once per round (DuelRound above is keyed by
  // round index), so there's no "recompute when round changes" case to
  // serve — just a one-time shuffle at mount, which is exactly what a
  // lazy initializer is for (and, unlike useMemo, isn't flagged as an
  // impure render call since it only ever runs once).
  const [rightShuffled] = useState(() => [...round.pairs.map((p) => p.right)].sort(() => Math.random() - 0.5));
  const [selectedLeft, setSelectedLeft] = useState<number | null>(null);
  const [matched, setMatched] = useState<Record<number, string>>({});
  const [wrongLeft, setWrongLeft] = useState<number | null>(null);
  const [lines, setLines] = useState<MatchLine[]>([]);
  const containerRef = useRef<HTMLDivElement>(null);
  const leftRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const rightRefs = useRef<Record<string, HTMLButtonElement | null>>({});
  const wonRef = useRef(false);
  const done = Object.keys(matched).length === round.pairs.length;

  useEffect(() => {
    if (done && !wonRef.current) {
      wonRef.current = true;
      onWin();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [done]);

  function pickRight(right: string) {
    if (locked || selectedLeft === null) return;
    const leftIndex = selectedLeft;
    if (round.pairs[leftIndex].right === right) {
      setMatched((m) => ({ ...m, [leftIndex]: right }));
      const container = containerRef.current;
      const leftEl = leftRefs.current[leftIndex];
      const rightEl = rightRefs.current[right];
      if (container && leftEl && rightEl) {
        const c = container.getBoundingClientRect();
        const l = leftEl.getBoundingClientRect();
        const r = rightEl.getBoundingClientRect();
        setLines((prev) => [
          ...prev,
          { key: leftIndex, x1: l.right - c.left, y1: l.top + l.height / 2 - c.top, x2: r.left - c.left, y2: r.top + r.height / 2 - c.top },
        ]);
      }
    } else {
      setWrongLeft(leftIndex);
      setTimeout(() => setWrongLeft(null), 350);
    }
    setSelectedLeft(null);
  }

  return (
    <div ref={containerRef} className={`relative ${cardCls}`}>
      <svg className="pointer-events-none absolute inset-0 h-full w-full">
        {lines.map((l) => (
          <line
            key={l.key}
            x1={l.x1}
            y1={l.y1}
            x2={l.x2}
            y2={l.y2}
            stroke="#10b981"
            strokeWidth={2}
            strokeLinecap="round"
            pathLength={1}
            style={{ strokeDasharray: 1, strokeDashoffset: 1, animation: "game-line-draw 0.35s ease-out forwards" }}
          />
        ))}
      </svg>
      <div className="relative grid grid-cols-2 gap-2">
        <div className="space-y-1.5">
          {round.pairs.map((p, i) => (
            <button
              key={i}
              ref={(el) => {
                leftRefs.current[i] = el;
              }}
              disabled={locked || matched[i] !== undefined}
              onClick={() => setSelectedLeft(i)}
              className={`w-full rounded-lg border-2 px-2 py-1.5 text-left text-[11px] font-medium transition ${
                matched[i] !== undefined
                  ? "border-emerald-300 bg-emerald-50 text-emerald-700"
                  : selectedLeft === i
                    ? theme.active
                    : wrongLeft === i
                      ? "animate-[game-shake_0.3s_ease-in-out] border-red-300 bg-red-50 text-red-700"
                      : theme.idle
              }`}
            >
              {p.left}
            </button>
          ))}
        </div>
        <div className="space-y-1.5">
          {rightShuffled.map((right, i) => {
            const used = Object.values(matched).includes(right);
            return (
              <button
                key={i}
                ref={(el) => {
                  rightRefs.current[right] = el;
                }}
                disabled={locked || used}
                onClick={() => pickRight(right)}
                className={`w-full rounded-lg border-2 px-2 py-1.5 text-left text-[11px] font-medium ${
                  used ? "border-emerald-300 bg-emerald-50 text-emerald-700" : theme.idle
                }`}
              >
                {right}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function DuelOrder({
  round,
  locked,
  onWin,
  cardCls,
  theme,
}: {
  round: Extract<Round, { type: "order" }>;
  locked: boolean;
  onWin: () => void;
  cardCls: string;
  theme: SideTheme;
}) {
  const [items, setItems] = useState(() => {
    const s = [...round.items].sort(() => Math.random() - 0.5);
    if (round.items.length > 1 && s.every((it, i) => it === round.items[i])) {
      [s[0], s[1]] = [s[1], s[0]];
    }
    return s;
  });
  const [draggingIndex, setDraggingIndex] = useState<number | null>(null);
  const [dragOffset, setDragOffset] = useState(0);
  const rowRefs = useRef<(HTMLDivElement | null)[]>([]);
  const dragRef = useRef<{ index: number; startY: number } | null>(null);
  const wonRef = useRef(false);
  const correct = items.every((it, i) => it === round.items[i]);

  useEffect(() => {
    if (correct && !wonRef.current) {
      wonRef.current = true;
      onWin();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [correct]);

  // Same Pointer Events drag-reorder as SoloGame.tsx's OrderStage (see its
  // doc comment on why not native HTML5 drag-and-drop) — duplicated rather
  // than shared since this side's version also has to respect `locked`.
  function onPointerDown(e: React.PointerEvent, index: number) {
    if (locked || correct) return;
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    dragRef.current = { index, startY: e.clientY };
    setDraggingIndex(index);
    setDragOffset(0);
  }

  function onPointerMove(e: React.PointerEvent) {
    const drag = dragRef.current;
    if (!drag) return;
    setDragOffset(e.clientY - drag.startY);
    for (let i = 0; i < rowRefs.current.length; i++) {
      if (i === drag.index) continue;
      const row = rowRefs.current[i];
      if (!row) continue;
      const rect = row.getBoundingClientRect();
      const mid = rect.top + rect.height / 2;
      const movingDown = i > drag.index && e.clientY > mid;
      const movingUp = i < drag.index && e.clientY < mid;
      if (movingDown || movingUp) {
        // See SoloGame.tsx's OrderStage for why the old index has to be
        // captured before drag.index is mutated below.
        const fromIndex = drag.index;
        setItems((prev) => {
          const next = [...prev];
          const [moved] = next.splice(fromIndex, 1);
          next.splice(i, 0, moved);
          return next;
        });
        drag.index = i;
        drag.startY = e.clientY;
        setDraggingIndex(i);
        break;
      }
    }
  }

  function onPointerUp() {
    dragRef.current = null;
    setDraggingIndex(null);
    setDragOffset(0);
  }

  return (
    <div className={cardCls}>
      <div className="space-y-1.5">
        {items.map((item, i) => (
          <div
            key={item}
            ref={(el) => {
              rowRefs.current[i] = el;
            }}
            onPointerDown={(e) => onPointerDown(e, i)}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onPointerCancel={onPointerUp}
            style={{
              touchAction: "none",
              transform: draggingIndex === i ? `translateY(${dragOffset}px) scale(1.03)` : undefined,
              zIndex: draggingIndex === i ? 10 : undefined,
              transition: draggingIndex === i ? "none" : "transform 0.15s ease-out",
            }}
            className={`relative flex cursor-grab items-center gap-1.5 rounded-lg border-2 px-2 py-1.5 text-[11px] font-medium select-none active:cursor-grabbing ${
              correct ? "border-emerald-300 bg-emerald-50 text-emerald-700" : theme.idle
            }`}
          >
            <GripVertical className="h-3 w-3 shrink-0 opacity-50" />
            {item}
          </div>
        ))}
      </div>
    </div>
  );
}

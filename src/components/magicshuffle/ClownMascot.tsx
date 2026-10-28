"use client";

export type ClownMood = "idle" | "reveal" | "casting" | "shuffling" | "waiting" | "happy" | "sad" | "surprised";


const BODY_ANIMATION: Record<ClownMood, string | undefined> = {
  idle: "mascot-bob 2.8s ease-in-out infinite",
  reveal: "mascot-bob 2.4s ease-in-out infinite",
  casting: "mascot-tilt 0.8s ease-in-out infinite",
  shuffling: "mbox-clown-shuffle 0.42s ease-in-out infinite",
  waiting: "mascot-bob 2.2s ease-in-out infinite",
  happy: "mascot-celebrate 0.7s ease-in-out infinite",
  sad: "mascot-tilt 1.6s ease-in-out infinite",
  surprised: "mascot-pop 0.5s ease-out",
};


const BUBBLE: Record<ClownMood, string | null> = {
  idle: null,
  reveal: "Саволро хуб дар хотир гиред!",
  casting: "Савол қутӣга ҷойгир шуд!",
  shuffling: "Қуттиҳо омехта мешаванд...",
  waiting: "Ҳоло қуттиро интихоб кунед!",
  happy: "Офарин! 🎉",
  sad: "Ин қутӣ холӣ аст! 🙈",
  surprised: "Оҳ! ✨",
};

export default function ClownMascot({ mood, size = 200 }: { mood: ClownMood; size?: number }) {
  const bubble = BUBBLE[mood];
  const wandActive = mood === "casting" || mood === "shuffling" || mood === "surprised";

  return (
    <div className="pointer-events-none relative flex flex-col items-center">
      {bubble && (
        <div
          key={bubble}
          className="relative mb-2 max-w-[280px] rounded-2xl bg-white/95 px-4 py-2 text-center text-sm font-bold text-[#3b0764] shadow-xl"
          style={{ animation: "mascot-pop 0.4s ease-out" }}
        >
          {bubble}
          {}
          <span className="absolute -bottom-1.5 left-1/2 h-3 w-3 -translate-x-1/2 rotate-45 bg-white/95" aria-hidden />
        </div>
      )}

      <div className="relative" style={{ animation: BODY_ANIMATION[mood] }}>
        {}
        <img src="/game-backgrounds/jester.png" alt="" className="w-auto drop-shadow-2xl" style={{ height: size }} />

        {}
        {wandActive && (
          <span
            className="absolute right-[-6px] top-[45%] origin-bottom-left text-3xl"
            style={{ animation: "mbox-wand-wave 0.45s ease-in-out infinite" }}
            aria-hidden
          >
            🪄
          </span>
        )}

        {}
        {mood === "shuffling" && (
          <span
            className="absolute -bottom-2 left-1/2 -translate-x-1/2 text-2xl"
            style={{ animation: "mbox-clown-shuffle 0.5s ease-in-out infinite reverse" }}
            aria-hidden
          >
            👐
          </span>
        )}

        {}
        {wandActive &&
          [0, 0.25, 0.5].map((d, i) => (
            <span
              key={i}
              className="absolute right-0 top-[35%] text-sm"
              style={{ animation: `mascot-sparkle 0.9s ease-out ${d}s infinite`, marginRight: i * 10 }}
              aria-hidden
            >
              ✨
            </span>
          ))}

        {mood === "happy" &&
          [0, 0.15, 0.3, 0.45].map((d, i) => (
            <span
              key={i}
              className="absolute text-lg"
              style={{
                left: `${12 + i * 24}%`,
                top: "-8%",
                animation: `mascot-sparkle 0.8s ease-out ${d}s infinite`,
              }}
              aria-hidden
            >
              🎉
            </span>
          ))}
      </div>
    </div>
  );
}

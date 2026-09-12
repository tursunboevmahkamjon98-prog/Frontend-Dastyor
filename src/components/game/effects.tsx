"use client";

import { useMemo, useState } from "react";

// A capped confetti burst for win screens — plain absolutely-positioned divs
// animated with transform/opacity only (GPU-cheap, no canvas/library needed).
// Count is capped at 40 so this stays fine even on low-end phones.
const CONFETTI_COLORS = ["#7c3aed", "#a855f7", "#f472b6", "#fbbf24", "#34d399", "#60a5fa"];

export function Confetti({ count = 36 }: { count?: number }) {
  // Lazy useState initializer, not useMemo: ResultScreen only ever mounts
  // Confetti once per game-over (it's not kept around across re-renders
  // with a changing `count`), so this is a one-time randomization at mount
  // — exactly what a lazy initializer is for, and unlike useMemo it isn't
  // flagged as an impure render call since it only runs once.
  const [pieces] = useState(() =>
    Array.from({ length: count }, (_, i) => ({
      left: Math.random() * 100,
      delay: Math.random() * 0.6,
      duration: 2.2 + Math.random() * 1.4,
      rotate: Math.random() * 360,
      color: CONFETTI_COLORS[i % CONFETTI_COLORS.length],
      size: 6 + Math.random() * 7,
      drift: (Math.random() - 0.5) * 120,
    }))
  );
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {pieces.map((p, i) => (
        <span
          key={i}
          style={{
            position: "absolute",
            left: `${p.left}%`,
            top: "-5%",
            width: p.size,
            height: p.size * 0.4,
            background: p.color,
            borderRadius: 2,
            opacity: 0,
            transform: `rotate(${p.rotate}deg)`,
            animation: `game-confetti-fall ${p.duration}s ease-in ${p.delay}s infinite`,
            // Drift travels sideways via a CSS custom property the keyframe reads.
            ["--drift" as string]: `${p.drift}px`,
          }}
        />
      ))}
    </div>
  );
}

// A short-lived radial burst of little stars from one point — used on a
// correct answer / round win so the feedback reads as a tiny celebration
// rather than just a color flash. `playKey` should change every trigger
// (e.g. round index) so React remounts it and the one-shot animation replays.
export function Burst({ playKey, color = "#fbbf24" }: { playKey: string | number; color?: string }) {
  const dots = useMemo(
    () =>
      Array.from({ length: 10 }, (_, i) => {
        const angle = (i / 10) * Math.PI * 2;
        return { x: Math.cos(angle) * 46, y: Math.sin(angle) * 46, delay: i * 0.012 };
      }),
    []
  );
  return (
    <div key={playKey} className="pointer-events-none absolute inset-0 flex items-center justify-center">
      {dots.map((d, i) => (
        <span
          key={i}
          style={{
            position: "absolute",
            width: 7,
            height: 7,
            borderRadius: "9999px",
            background: color,
            ["--bx" as string]: `${d.x}px`,
            ["--by" as string]: `${d.y}px`,
            animation: `game-burst 0.55s ease-out ${d.delay}s`,
          }}
        />
      ))}
    </div>
  );
}

"use client";

import { useMemo, useState } from "react";




const CONFETTI_COLORS = ["#7c3aed", "#a855f7", "#f472b6", "#fbbf24", "#34d399", "#60a5fa"];

export function Confetti({ count = 36 }: { count?: number }) {
  
  
  
  
  
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
            
            ["--drift" as string]: `${p.drift}px`,
          }}
        />
      ))}
    </div>
  );
}





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

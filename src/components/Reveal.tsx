"use client";

import { useEffect, useRef, useState } from "react";

/** Fades+lifts its children into place the first time they scroll into
 * view (landing-reveal keyframe in globals.css) — a plain IntersectionObserver
 * rather than a scroll library, since this is the only place on the whole
 * site that needs one. Disconnects after the first trigger: a landing page
 * section should tell its story once, not replay every time a visitor
 * scrolls back up past it. `delay` (ms) staggers siblings in a grid so they
 * don't all snap in on the same frame. */
export default function Reveal({
  children,
  delay = 0,
  className = "",
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    // Respect the OS-level reduced-motion preference by just showing the
    // content immediately rather than skipping the observer entirely —
    // the layout must still appear, only the animation is what's optional.
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setShown(true);
      return;
    }
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setShown(true);
          io.disconnect();
        }
      },
      { threshold: 0.15 }
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={className}
      style={{
        opacity: shown ? 1 : 0,
        animation: shown ? `landing-reveal 0.7s ease-out ${delay}ms both` : undefined,
      }}
    >
      {children}
    </div>
  );
}

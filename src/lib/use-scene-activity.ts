"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";

function subscribeToVisibility(onChange: () => void) {
  document.addEventListener("visibilitychange", onChange);
  return () => document.removeEventListener("visibilitychange", onChange);
}

const isPageVisible = () => document.visibilityState === "visible";
const serverVisibility = () => false;

// Responsive layouts contain both desktop and mobile illustrations. Mount
// only the one that becomes visible, and pause rendering while off screen.
export function useSceneActivity() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  const [entered, setEntered] = useState(false);
  const pageVisible = useSyncExternalStore(subscribeToVisibility, isPageVisible, serverVisibility);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const observer = new IntersectionObserver(([entry]) => {
      const shown = entry.isIntersecting
        && entry.intersectionRect.width > 0 && entry.intersectionRect.height > 0;
      setVisible(shown);
      if (shown) setEntered(true);
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  return { containerRef, entered, active: visible && pageVisible };
}

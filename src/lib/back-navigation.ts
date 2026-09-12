/** Telling "the browser's Back/Forward button was just pressed" apart from
 * "a fresh visit" — for pages that restore in-progress work (the create
 * screen's just-generated results, say) only on the former.
 *
 * Why not `performance.getEntriesByType("navigation")[0].type`
 * -------------------------------------------------------------
 * That was the first attempt, and it doesn't work: a Performance
 * Navigation Timing entry is created once per real browser navigation
 * (a full document load), not per client-side route change. Next.js's
 * App Router handles both forward clicks (`router.push`) and Back/Forward
 * with the History API inside the SAME document — no new entry is ever
 * created for either — so `.type` keeps reporting how the CURRENT TAB's
 * very first page load happened ("navigate", almost always) no matter how
 * many client-side back-navigations happen afterward. The check that read
 * that value was consequently dead code: it (almost) never saw
 * "back_forward", so the restore it gated never ran, and pressing Back
 * from a just-created material always landed on a blank form instead of
 * the results list.
 *
 * What actually fires on Back/Forward in an SPA is the `popstate` event —
 * including for History-API-driven client navigation, not just full page
 * loads. So a listener mounted once near the app's root (see
 * markBackNavigationListener, called from the dashboard layout, which
 * stays mounted across every client-side route change under /dashboard)
 * stamps a per-tab flag the instant Back/Forward is pressed, and the page
 * that remounts a moment later reads it in its very first render.
 *
 * sessionStorage, not a module-level variable, because the page that
 * consumes the flag is a different React tree than the layout that set
 * it — they don't share JS state across that boundary the way two
 * components in the same tree would, but they do share the tab's
 * sessionStorage.
 */
const FLAG_KEY = "dastyor:nav:back_forward";

/** Call once, from a component that stays mounted across every
 * client-side route change (a layout, not a page — a page unmounts on
 * the very navigation this needs to observe). Safe to call from more
 * than one such layout; the listener is idempotent per `window`. */
export function markBackNavigationListener(): () => void {
  if (typeof window === "undefined") return () => {};
  const onPopState = () => {
    try {
      sessionStorage.setItem(FLAG_KEY, "1");
    } catch {
      // Storage unavailable — the page this was for simply starts blank,
      // same as it always did before this existed.
    }
  };
  window.addEventListener("popstate", onPopState);
  return () => window.removeEventListener("popstate", onPopState);
}

/** True exactly once per Back/Forward press — reading it clears it, so a
 * page that restores state from it and is then left via a forward click
 * doesn't restore again on some LATER, unrelated Back press. Call this
 * from a lazy `useState(() => ...)` initializer so it runs during the
 * page's first render, before anything else needs to know. */
export function consumeWasBackNavigation(): boolean {
  if (typeof window === "undefined") return false;
  try {
    if (sessionStorage.getItem(FLAG_KEY) !== "1") return false;
    sessionStorage.removeItem(FLAG_KEY);
    return true;
  } catch {
    return false;
  }
}

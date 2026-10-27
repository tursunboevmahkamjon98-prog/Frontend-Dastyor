export type Theme = "light" | "dark";

export const THEME_STORAGE_KEY = "dastyor_web_theme";

/* Runs synchronously as the first child of <body>, before React and before
 * first paint, so the stored choice is already on <html> and the page never
 * flashes the wrong theme. */
export const THEME_INIT_SCRIPT = `(function(){var d=document.documentElement;try{var t=localStorage.getItem(${JSON.stringify(
  THEME_STORAGE_KEY,
)});t=(t==="light"||t==="dark")?t:(window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light");d.setAttribute("data-theme",t);}catch(e){d.setAttribute("data-theme","light");}})();`;

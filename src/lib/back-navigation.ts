
const FLAG_KEY = "dastyor:nav:back_forward";


export function markBackNavigationListener(): () => void {
  if (typeof window === "undefined") return () => {};
  const onPopState = () => {
    try {
      sessionStorage.setItem(FLAG_KEY, "1");
    } catch {
      
      
    }
  };
  window.addEventListener("popstate", onPopState);
  return () => window.removeEventListener("popstate", onPopState);
}


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

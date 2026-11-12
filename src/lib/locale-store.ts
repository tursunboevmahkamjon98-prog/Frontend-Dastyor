import { MESSAGES, MessageKey, Locale } from "./messages";

// The chosen interface language, shared by the React provider (i18n.tsx)
// and by plain modules such as api.ts that cannot call hooks.

export const LOCALE_STORAGE_KEY = "dastyor_web_locale";
export const DEFAULT_LOCALE: Locale = "ru";

// Fallback when localStorage is unavailable (private mode, blocked storage).
let memoryLocale: Locale = DEFAULT_LOCALE;

export function readStoredLocale(): Locale {
  if (typeof window === "undefined") return DEFAULT_LOCALE;
  try {
    const stored = localStorage.getItem(LOCALE_STORAGE_KEY) as Locale | null;
    return stored && stored in MESSAGES ? stored : memoryLocale;
  } catch {
    return memoryLocale;
  }
}

export function hasStoredLocale(): boolean {
  try {
    return Boolean(localStorage.getItem(LOCALE_STORAGE_KEY));
  } catch {
    return false;
  }
}

export function storeLocale(next: Locale) {
  memoryLocale = next;
  try {
    localStorage.setItem(LOCALE_STORAGE_KEY, next);
  } catch {
    // Storage blocked: the choice only lasts this page view.
  }
}

// Translate outside React, in the language the user picked last.
export function translate(key: MessageKey): string {
  return MESSAGES[readStoredLocale()][key];
}

"use client";

import { createContext, useCallback, useContext, useEffect, useState, ReactNode } from "react";
import { MESSAGES, MessageKey, Locale, localeFromAccountLanguage } from "./messages";

const STORAGE_KEY = "dastyor_web_locale";

interface LocaleContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: MessageKey) => string;
}

const LocaleContext = createContext<LocaleContextValue | null>(null);

/** Renders children under a chosen UI language.
 *
 * Server-render and first client paint both use "ru" so the two agree —
 * reading localStorage during render would produce markup the server
 * cannot match and React would throw a hydration error. The stored (or
 * account) choice is applied in an effect immediately after mount. */
export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("ru");

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY) as Locale | null;
    if (stored && stored in MESSAGES) setLocaleState(stored);
  }, []);

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    localStorage.setItem(STORAGE_KEY, next);
  }, []);

  const t = useCallback((key: MessageKey) => MESSAGES[locale][key], [locale]);

  return <LocaleContext.Provider value={{ locale, setLocale, t }}>{children}</LocaleContext.Provider>;
}

export function useLocale() {
  const ctx = useContext(LocaleContext);
  if (!ctx) throw new Error("useLocale must be used within LocaleProvider");
  return ctx;
}

/** Shorthand for the common case of only needing the lookup function. */
export function useT() {
  return useLocale().t;
}

/** Adopts the account's own language the first time a signed-in user is
 * seen, unless they already picked a UI language on this device — an
 * explicit choice in the browser should outrank the account default.
 * Call once, high in the tree, below both providers. */
export function useAccountLocale(accountLanguage: string | null | undefined) {
  const { setLocale } = useLocale();
  useEffect(() => {
    if (!accountLanguage) return;
    if (localStorage.getItem(STORAGE_KEY)) return;
    setLocale(localeFromAccountLanguage(accountLanguage));
  }, [accountLanguage, setLocale]);
}

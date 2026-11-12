"use client";

import { createContext, useCallback, useContext, useEffect, useSyncExternalStore, ReactNode } from "react";
import { MESSAGES, MessageKey, Locale, localeFromAccountLanguage } from "./messages";
import { DEFAULT_LOCALE, hasStoredLocale, readStoredLocale, storeLocale } from "./locale-store";

interface LocaleContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: MessageKey) => string;
}

const LocaleContext = createContext<LocaleContextValue | null>(null);

const LOCALE_EVENT = "dastyor-locale-change";

function subscribeLocale(onChange: () => void) {
  // "storage" keeps other tabs in sync; the custom event covers this tab.
  window.addEventListener("storage", onChange);
  window.addEventListener(LOCALE_EVENT, onChange);
  return () => {
    window.removeEventListener("storage", onChange);
    window.removeEventListener(LOCALE_EVENT, onChange);
  };
}


export function LocaleProvider({ children }: { children: ReactNode }) {
  // The server renders the default locale; the stored choice replaces it
  // right after hydration without a mismatch.
  const locale = useSyncExternalStore(subscribeLocale, readStoredLocale, () => DEFAULT_LOCALE);

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const setLocale = useCallback((next: Locale) => {
    storeLocale(next);
    window.dispatchEvent(new Event(LOCALE_EVENT));
  }, []);

  const t = useCallback((key: MessageKey) => MESSAGES[locale][key], [locale]);

  return <LocaleContext.Provider value={{ locale, setLocale, t }}>{children}</LocaleContext.Provider>;
}

export function useLocale() {
  const ctx = useContext(LocaleContext);
  if (!ctx) throw new Error("useLocale must be used within LocaleProvider");
  return ctx;
}


export function useT() {
  return useLocale().t;
}


export function useAccountLocale(accountLanguage: string | null | undefined) {
  const { setLocale } = useLocale();
  useEffect(() => {
    if (!accountLanguage) return;
    if (hasStoredLocale()) return;
    setLocale(localeFromAccountLanguage(accountLanguage));
  }, [accountLanguage, setLocale]);
}

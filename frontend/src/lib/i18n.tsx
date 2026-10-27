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


export function useT() {
  return useLocale().t;
}


export function useAccountLocale(accountLanguage: string | null | undefined) {
  const { setLocale } = useLocale();
  useEffect(() => {
    if (!accountLanguage) return;
    if (localStorage.getItem(STORAGE_KEY)) return;
    setLocale(localeFromAccountLanguage(accountLanguage));
  }, [accountLanguage, setLocale]);
}

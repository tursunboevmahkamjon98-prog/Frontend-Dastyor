"use client";

import { useEffect, useState } from "react";
import { Download, X } from "lucide-react";

const DISMISS_KEY = "dastyor_apk_notice_dismissed";

export default function AppUpdateBanner() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => {
      if (localStorage.getItem(DISMISS_KEY) === "1") return;
      if (!/android/i.test(navigator.userAgent)) return;
      setShow(true);
    }, 0);
    return () => clearTimeout(t);
  }, []);

  if (!show) return null;

  return (
    <div className="flex items-start gap-3 border-b border-border-light bg-primary-50 px-4 py-2.5 text-sm sm:px-6">
      <Download className="mt-0.5 h-4 w-4 shrink-0 text-primary-dark" />
      <p className="flex-1 text-text-primary">
        Вышла новая версия приложения Dastyor.{" "}
        <a href="/dastyor.apk" className="font-medium text-primary-dark underline">
          Скачать
        </a>{" "}
        <span className="text-text-secondary">
          — установите поверх старой, она обновится сама.
        </span>
      </p>
      <button
        onClick={() => {
          localStorage.setItem(DISMISS_KEY, "1");
          setShow(false);
        }}
        aria-label="Закрыть"
        className="shrink-0 rounded p-0.5 text-text-tertiary hover:text-text-primary"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

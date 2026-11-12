"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useT } from "@/lib/i18n";

// Shown when a page throws while rendering. Without this file Next.js
// falls back to its own bare error screen.
// "error" can be any thrown value, not only an Error (see the Next.js error.js docs).
export default function ErrorPage({ error, retry }: { error: unknown; retry: () => void }) {
  const t = useT();

  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="mx-auto flex min-h-[60vh] max-w-md flex-col items-center justify-center px-4 py-16 text-center">
      <h1 className="text-2xl font-bold text-text-primary">{t("errorPage.title")}</h1>
      <p className="mt-3 text-sm text-text-secondary">{t("errorPage.text")}</p>
      <div className="mt-6 flex flex-wrap justify-center gap-3">
        <button
          type="button"
          onClick={() => retry()}
          className="rounded-[1rem] bg-primary px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-primary-dark"
        >
          {t("errorPage.retry")}
        </button>
        <Link
          href="/"
          className="rounded-[1rem] border border-border bg-white px-5 py-2.5 text-sm font-semibold text-text-primary transition-colors hover:bg-surface-muted"
        >
          {t("errorPage.home")}
        </Link>
      </div>
    </main>
  );
}

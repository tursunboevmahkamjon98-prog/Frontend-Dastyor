"use client";

import Link from "next/link";
import { useT } from "@/lib/i18n";

export default function NotFound() {
  const t = useT();

  return (
    <main className="mx-auto flex min-h-[60vh] max-w-md flex-col items-center justify-center px-4 py-16 text-center">
      <p className="text-5xl font-bold text-primary">404</p>
      <h1 className="mt-4 text-2xl font-bold text-text-primary">{t("notFound.title")}</h1>
      <p className="mt-3 text-sm text-text-secondary">{t("notFound.text")}</p>
      <Link
        href="/"
        className="mt-6 rounded-[1rem] bg-primary px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-primary-dark"
      >
        {t("errorPage.home")}
      </Link>
    </main>
  );
}

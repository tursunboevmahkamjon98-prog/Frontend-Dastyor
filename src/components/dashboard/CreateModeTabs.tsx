"use client";

import Link from "next/link";
import { BookOpen, Sparkles } from "lucide-react";
import { useT } from "@/lib/i18n";

export default function CreateModeTabs({ mode }: { mode: "ai" | "book" }) {
  const t = useT();
  return <nav aria-label={t("book.modeLabel")} className="mb-7 grid gap-2 rounded-2xl border border-border bg-surface p-1.5 sm:grid-cols-2">
    <Link href="/dashboard/create" aria-current={mode === "ai" ? "page" : undefined}
      className={`flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold transition-colors ${mode === "ai" ? "bg-primary text-white shadow-sm" : "text-text-secondary hover:bg-surface-muted"}`}>
      <Sparkles className="h-5 w-5 shrink-0" />{t("book.aiMode")}
    </Link>
    <Link href="/dashboard/create/book" aria-current={mode === "book" ? "page" : undefined}
      className={`flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold transition-colors ${mode === "book" ? "bg-primary text-white shadow-sm" : "text-text-secondary hover:bg-surface-muted"}`}>
      <BookOpen className="h-5 w-5 shrink-0" />{t("book.bookMode")}
    </Link>
  </nav>;
}

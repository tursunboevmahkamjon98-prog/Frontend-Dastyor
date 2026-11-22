"use client";

import Link from "next/link";
import { Sparkles, ArrowRight } from "lucide-react";
import { useT } from "@/lib/i18n";

/* The bold top strip above the nav — matches the reference marketing
 * page's announcement bar (solid brand colour, icon + line + CTA link).
 * Separate from Header so the sticky header itself stays simple. */
export default function AnnouncementBar() {
  const t = useT();
  return (
    <Link
      href="/register"
      className="group flex items-center justify-center gap-2 bg-primary px-4 py-2.5 text-center text-xs font-semibold text-white transition hover:bg-primary-dark sm:text-sm"
    >
      <Sparkles className="h-3.5 w-3.5 shrink-0" />
      <span className="truncate">{t("landing.announcement.text")}</span>
      <span className="inline-flex shrink-0 items-center gap-1 underline underline-offset-2">
        {t("landing.announcement.cta")}
        <ArrowRight className="h-3.5 w-3.5 transition group-hover:translate-x-0.5" />
      </span>
    </Link>
  );
}

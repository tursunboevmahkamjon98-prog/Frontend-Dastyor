"use client";

import { useT } from "@/lib/i18n";

/* A quiet library count beside the page heading. The composer remains the
 * primary action; this number only appears after a material exists. */
export default function QuickStats({ total }: { total: number | null }) {
  const t = useT();
  if (total === null || total === 0) return null;

  return (
    <div className="hidden items-center gap-3 border-l border-border pl-5 sm:flex">
      <span className="text-heading font-semibold tabular-nums text-primary-accent">{total}</span>
      <span className="max-w-28 text-micro font-medium leading-snug text-text-secondary">
        {t("home.totalLabel")}
      </span>
    </div>
  );
}

"use client";

import { useT } from "@/lib/i18n";
import { LIBRARY_TYPES, MATERIAL_TYPE_CONFIG, MATERIAL_TYPE_LABEL_KEY } from "@/lib/material-types";

export default function MaterialOverview({ className, values }: { className?: string; values?: number[] }) {
  const t = useT();
  const ready = values?.length === LIBRARY_TYPES.length;
  const counts = LIBRARY_TYPES.map((_, i) => ready && Number.isFinite(values![i]) ? Math.max(0, values![i]) : 0);
  const total = counts.reduce((sum, n) => sum + n, 0);
  const max = Math.max(1, ...counts);

  return (
    <section className={`rounded-2xl border border-slate-200/80 bg-white p-4 shadow-[0_8px_30px_-20px_rgba(15,23,42,0.2)] ${className ?? ""}`}>
      <div className="mb-4 flex items-end justify-between gap-4 border-b border-slate-100 pb-3">
        <div>
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-400">RAHNAMO</p>
          <p className="text-sm font-medium text-slate-500">{t("home.totalShort")}</p>
        </div>
        <p className="text-4xl font-semibold leading-none tracking-tight tabular-nums text-slate-900">{ready ? total : "—"}</p>
      </div>
      <dl className="space-y-2.5">
        {LIBRARY_TYPES.map((type, i) => {
          const Icon = MATERIAL_TYPE_CONFIG[type].icon;
          const leading = counts[i] > 0 && counts[i] === max;
          return (
            <div key={type}>
              <div className="mb-1 flex items-center gap-2">
                <Icon aria-hidden="true" className={`h-3.5 w-3.5 shrink-0 ${leading ? "text-red-600" : "text-slate-400"}`} />
                <dt className="min-w-0 flex-1 text-xs leading-snug text-slate-600">{t(MATERIAL_TYPE_LABEL_KEY[type])}</dt>
                <dd className="shrink-0 text-xs font-semibold tabular-nums text-slate-900">{ready ? counts[i] : "—"}</dd>
              </div>
              <div aria-hidden="true" className="ml-5.5 h-1 overflow-hidden rounded-full bg-slate-100">
                <div className={`h-full rounded-full ${leading ? "bg-red-600" : "bg-slate-300"}`} style={{ width: `${counts[i] / max * 100}%` }} />
              </div>
            </div>
          );
        })}
      </dl>
    </section>
  );
}

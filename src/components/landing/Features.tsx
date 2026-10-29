"use client";

import { Check, Layers } from "lucide-react";
import Reveal from "@/components/Reveal";
import { useT } from "@/lib/i18n";
import { FEATURES, featureTitleKey, featureDescKey, ALL_AT_ONCE_POINTS } from "./constants";

/* All six feature cards are deliberately uniform — a mixed-span bento grid
 * sounds nice until the spanned cell has no extra content to fill the
 * extra space with, which is exactly the dead-white-space bug a first pass
 * at this hit. The only size variation left is the closing cell below,
 * which has enough real content (the old standalone "all at once" section)
 * to actually earn being wide. */
export default function Features() {
  const t = useT();

  return (
    <section id="features" className="mx-auto w-full max-w-6xl px-4 pb-16 sm:px-6 sm:pb-24">
      <Reveal className="mx-auto mb-12 max-w-xl text-center">
        <h2 className="text-2xl font-bold text-text-primary sm:text-3xl">{t("landing.features.title")}</h2>
        <p className="mt-3 text-text-secondary">{t("landing.features.subtitle")}</p>
      </Reveal>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map(({ id, icon: Icon, bg, color }, i) => (
          <Reveal
            key={id}
            delay={(i % 3) * 100}
            className="group flex flex-col rounded-2xl border border-border-light bg-white p-5 shadow-[0_3px_0_0_var(--color-border-light),0_14px_28px_-10px_rgba(0,0,0,0.08)] transition hover:-translate-y-1.5 hover:border-primary/25 hover:shadow-[0_4px_0_0_var(--color-primary-50),0_20px_32px_-10px_rgba(220,38,38,0.2)]"
          >
            <div className={`mb-4 flex h-11 w-11 items-center justify-center rounded-xl ${bg} shadow-[inset_0_-2px_4px_rgba(0,0,0,0.08),inset_0_1px_1px_rgba(255,255,255,0.8)] transition group-hover:scale-110`}>
              <Icon className={`h-5 w-5 ${color}`} />
            </div>
            <h3 className="mb-1.5 font-semibold text-text-primary">{t(featureTitleKey(id))}</h3>
            <p className="text-sm leading-relaxed text-text-secondary">{t(featureDescKey(id))}</p>
          </Reveal>
        ))}

        {/* Wide closing cell — formerly the standalone "all at once" section */}
        <Reveal className="sm:col-span-2 lg:col-span-3">
          <div className="overflow-hidden rounded-2xl border border-border-light bg-white shadow-[0_3px_0_0_var(--color-border-light),0_14px_28px_-10px_rgba(220,38,38,0.1)]">
            <div className="grid gap-6 p-6 sm:p-8 lg:grid-cols-2 lg:items-center">
              <div>
                <div className="mb-4 inline-flex items-center gap-1.5 rounded-full border border-primary/15 bg-primary-50 px-3.5 py-1.5 text-xs font-semibold text-primary-dark">
                  <Layers className="h-3.5 w-3.5" />
                  {t("landing.all.badge")}
                </div>
                <h3 className="mb-3 text-xl font-bold text-text-primary sm:text-2xl">
                  {t("landing.all.title")}
                </h3>
                <p className="mb-5 text-sm text-text-secondary sm:text-base">
                  {t("landing.all.desc")}
                </p>
                <ul className="space-y-2.5">
                  {ALL_AT_ONCE_POINTS.map((point) => (
                    <li key={point} className="flex items-start gap-2.5 text-sm text-text-secondary">
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                      {t(point)}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-2">
                {FEATURES.map(({ id, icon: Icon, bg, color }) => (
                  <div
                    key={id}
                    className="flex items-center gap-2.5 rounded-xl border border-border-light bg-white px-3 py-3 shadow-[0_2px_0_0_var(--color-border-light)]"
                  >
                    <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${bg} shadow-[inset_0_-2px_3px_rgba(0,0,0,0.08),inset_0_1px_1px_rgba(255,255,255,0.8)]`}>
                      <Icon className={`h-4.5 w-4.5 ${color}`} />
                    </span>
                    <span className="text-xs font-semibold leading-tight text-text-primary">{t(featureTitleKey(id))}</span>
                  </div>
                ))}
                <div className="flex items-center justify-center rounded-xl border border-dashed border-primary/30 bg-primary-50/50 px-3 py-3 text-center text-xs font-semibold text-primary-dark">
                  {t("landing.all.oneTopic")}
                </div>
              </div>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

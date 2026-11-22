"use client";

import Reveal from "@/components/Reveal";
import { useT } from "@/lib/i18n";
import { FEATURES, featureTitleKey, featureDescKey } from "./constants";

const ROW_1 = [0, 2, 4] as const;
const ROW_2 = [1, 3, 5] as const;

function Card({ id }: { id: (typeof FEATURES)[number]["id"] }) {
  const t = useT();
  const feature = FEATURES.find((f) => f.id === id)!;
  const Icon = feature.icon;
  return (
    <div className="flex w-72 shrink-0 items-start gap-3 rounded-2xl border border-border-light bg-white px-4 py-4 shadow-[0_2px_0_0_var(--color-border-light),0_12px_24px_-16px_rgba(41,19,21,0.18)] transition hover:-translate-y-0.5 hover:shadow-[0_3px_0_0_var(--color-primary-50),0_16px_28px_-14px_rgba(220,38,38,0.22)]">
      <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${feature.bg} shadow-[inset_0_-2px_4px_rgba(0,0,0,0.08),inset_0_1px_1px_rgba(255,255,255,0.8)]`}>
        <Icon className={`h-4.5 w-4.5 ${feature.color}`} />
      </span>
      <span className="min-w-0">
        <span className="block text-sm font-semibold text-text-primary">{t(featureTitleKey(id))}</span>
        <span className="mt-0.5 line-clamp-2 block text-xs leading-relaxed text-text-tertiary">{t(featureDescKey(id))}</span>
      </span>
    </div>
  );
}

function Row({ ids, reverse }: { ids: readonly number[]; reverse?: boolean }) {
  const order = ids.map((i) => FEATURES[i].id);
  const track = [...order, ...order, ...order];
  return (
    <div className="flex w-max gap-4" style={{ animation: `${reverse ? "landing-marquee-right" : "landing-marquee-left"} 38s linear infinite` }}>
      {track.map((id, i) => (
        <Card key={`${id}-${i}`} id={id} />
      ))}
    </div>
  );
}

export default function FeatureMarquee() {
  const t = useT();
  return (
    <section id="features" className="border-y border-border-light bg-surface-muted/60 py-14 sm:py-16">
      <Reveal className="mx-auto mb-10 max-w-xl px-4 text-center">
        <h2 className="text-2xl font-bold text-text-primary sm:text-3xl">{t("landing.features.title")}</h2>
        <p className="mt-3 text-text-secondary">{t("landing.features.subtitle")}</p>
      </Reveal>

      <div className="group relative overflow-hidden">
        <div
          className="flex flex-col gap-4 [mask-image:linear-gradient(to_right,transparent,black_6%,black_94%,transparent)] [&_*]:group-hover:[animation-play-state:paused]"
        >
          <Row ids={ROW_1} />
          <Row ids={ROW_2} reverse />
        </div>
      </div>
    </section>
  );
}

"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import Reveal from "@/components/Reveal";
import SamplesGallery from "@/components/SamplesGallery";
import { useT } from "@/lib/i18n";

export default function Samples() {
  const t = useT();

  return (
    <section id="samples" className="mx-auto w-full max-w-6xl px-4 pb-16 sm:px-6 sm:pb-24">
      <Reveal className="mx-auto mb-10 max-w-xl text-center">
        <h2 className="text-2xl font-bold text-text-primary sm:text-3xl">{t("landing.samples.title")}</h2>
        <p className="mt-3 text-text-secondary">
          {t("landing.samples.subtitle")}
        </p>
      </Reveal>
      <Reveal>
        <SamplesGallery />
      </Reveal>
      <Reveal className="mt-8 text-center">
        <Link
          href="/register"
          className="group inline-flex items-center gap-2 rounded-xl bg-gradient-to-b from-primary-light to-primary px-6 py-3 text-sm font-semibold text-white shadow-[0_4px_0_0_var(--color-primary-dark),0_10px_24px_-6px_rgba(220,38,38,0.45)] transition-all duration-150 hover:-translate-y-0.5 hover:shadow-[0_5px_0_0_var(--color-primary-dark),0_14px_28px_-6px_rgba(220,38,38,0.5)] active:translate-y-0.5 active:shadow-[0_1px_0_0_var(--color-primary-dark),0_4px_10px_-4px_rgba(220,38,38,0.4)]"
        >
          {t("landing.samples.cta")}
          <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
        </Link>
      </Reveal>
    </section>
  );
}

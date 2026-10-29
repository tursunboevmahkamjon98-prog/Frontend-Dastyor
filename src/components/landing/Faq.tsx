"use client";

import Reveal from "@/components/Reveal";
import LandingFaq from "@/components/LandingFaq";
import { useT } from "@/lib/i18n";

export default function Faq() {
  const t = useT();

  return (
    <section id="faq" className="mx-auto w-full max-w-4xl px-4 pb-20 sm:px-6 sm:pb-28">
      <Reveal className="mx-auto mb-10 max-w-xl text-center">
        <h2 className="text-2xl font-bold text-text-primary sm:text-3xl">{t("landing.faq.title")}</h2>
      </Reveal>
      <Reveal>
        <LandingFaq />
      </Reveal>
    </section>
  );
}

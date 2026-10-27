"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";
import {
  ArrowRight, Check, Clock, FolderOpen, Languages, Settings2, Smartphone, Sparkles,
} from "lucide-react";
import LandingFaq from "@/components/LandingFaq";
import SamplesGallery from "@/components/SamplesGallery";
import LocaleSwitcher from "@/components/LocaleSwitcher";
import Logo from "@/components/Logo";
import HeroDocuments from "@/components/HeroDocuments";
import LandingNav from "@/components/landing/LandingNav";
import ProductPreview from "@/components/landing/ProductPreview";
import SubjectStrip from "@/components/landing/SubjectStrip";
import { FEATURES, NAV_LINKS, featureDescKey, featureTitleKey } from "@/components/landing/sections";
import { useT } from "@/lib/i18n";
import { useAuth } from "@/lib/auth-context";
import type { MessageKey } from "@/lib/messages";

/* The public page.
 *
 * Shape, in order: hero over the real output; a preview band pairing what
 * the teacher gains with the screen they gain it on; three numbered steps;
 * a dark features band closing on the subject list; the real generated
 * files; FAQ; a closing call to action; a three-column footer.
 *
 * Two sections were folded away in the polish pass rather than deleted.
 * Benefits moved into the preview band's text column — the claim and the
 * screen that backs it now sit side by side instead of 900px apart — and
 * the subject list became the base of the features band, which is where
 * "is my subject in there?" actually comes up. Both kept all their
 * content; the page lost about 1,400px of heading-and-padding scaffolding.
 *
 * Every claim is checked against the product: six material types because
 * there are six, fourteen subjects because SUBJECTS has fourteen, three
 * languages because MESSAGES has three. There are no usage statistics on
 * this page because the product has none to report, and no "no mistakes"
 * promise because nothing in the product can guarantee one.
 */

const HOW_STEPS: { title: MessageKey; desc: MessageKey }[] = [
  { title: "landing.how.s1.title", desc: "landing.how.s1.desc" },
  { title: "landing.how.s2.title", desc: "landing.how.s2.desc" },
  { title: "landing.how.s3.title", desc: "landing.how.s3.desc" },
];

const BENEFITS: { icon: typeof Clock; title: MessageKey; desc: MessageKey }[] = [
  { icon: Clock, title: "landing.benefit.time.title", desc: "landing.benefit.time.desc" },
  { icon: FolderOpen, title: "landing.benefit.library.title", desc: "landing.benefit.library.desc" },
  { icon: Settings2, title: "landing.benefit.adapt.title", desc: "landing.benefit.adapt.desc" },
];

const FACTS: MessageKey[] = ["landing.fact.fast", "landing.fact.clean", "landing.fact.plan"];

/** One heading treatment for the whole page, so section rhythm is a
 *  decision made once rather than re-typed per section. */
function SectionHead({
  eyebrow,
  title,
  subtitle,
}: {
  eyebrow: MessageKey;
  title: MessageKey;
  subtitle?: MessageKey;
}) {
  const t = useT();
  return (
    <div className="max-w-2xl">
      <p className="mb-2 text-micro font-semibold uppercase tracking-wide text-primary-accent">
        {t(eyebrow)}
      </p>
      <h2 className="text-title font-bold text-text-primary sm:text-display">{t(title)}</h2>
      {subtitle && <p className="mt-2.5 text-subheading text-text-secondary">{t(subtitle)}</p>}
    </div>
  );
}

export default function LandingPage({ apkSize }: { apkSize: string | null }) {
  const t = useT();
  const router = useRouter();
  const { user } = useAuth();
  const [topic, setTopic] = useState("");

  function startWithTopic(event: FormEvent) {
    event.preventDefault();
    const value = topic.trim();
    if (!value) return;
    const query = new URLSearchParams({ topic: value });
    router.push(user ? `/dashboard/create?${query}` : `/register?${query}`);
  }

  return (
    <main className="flex min-h-screen flex-col overflow-x-clip bg-background">
      <LandingNav />

      {/* ---- Hero ------------------------------------------------------ */}
      <section className="relative isolate overflow-hidden">
        <div
          className="soft-hero-backdrop pointer-events-none absolute inset-0 -z-10"
          aria-hidden
        />
        <div className="landing-hero-grid mx-auto grid w-full max-w-7xl min-w-0 items-center gap-3 px-4 pb-8 pt-9 sm:px-6 sm:pt-14 lg:grid-cols-[minmax(0,1.2fr)_minmax(18rem,0.8fr)] lg:gap-10 lg:px-8 lg:pb-12">
        <div className="landing-hero-copy min-w-0 text-center lg:text-left">
          <div className="inline-flex items-center gap-1.5 rounded-full border border-primary/15 bg-primary-50 px-3.5 py-1.5 text-micro font-semibold text-primary-accent">
            <Sparkles className="h-3.5 w-3.5" />
            {t("landing.hero.badge")}
          </div>

          <h1 className="mx-auto mt-5 w-full max-w-3xl break-words text-balance text-[clamp(2rem,7vw,4.3rem)] font-bold leading-[1.04] tracking-[-0.045em] text-text-primary lg:mx-0">
            {t("landing.hero.title")}{" "}
            <span className="text-primary-accent">{t("landing.hero.titleAccent")}</span>
          </h1>

          <p className="mx-auto mt-4 w-full max-w-xl break-words text-body text-text-secondary sm:text-subheading lg:mx-0">
            {t("landing.hero.subtitle")}
          </p>

          <form onSubmit={startWithTopic} className="mx-auto mt-7 flex w-full max-w-2xl min-w-0 flex-col gap-2 rounded-card border border-white/80 bg-white/85 p-2 shadow-card-lift backdrop-blur-sm sm:flex-row lg:mx-0">
            <label htmlFor="landing-topic" className="sr-only">{t("landing.hero.topicLabel")}</label>
            <input
              id="landing-topic"
              value={topic}
              onChange={(event) => setTopic(event.target.value)}
              maxLength={200}
              placeholder={t("landing.hero.topicPlaceholder")}
              className="min-w-0 flex-1 rounded-control bg-transparent px-4 py-3 text-body text-text-primary outline-none placeholder:text-text-tertiary focus-visible:ring-2 focus-visible:ring-primary/30"
            />
            <button type="submit" disabled={!topic.trim()} className="flex w-full items-center justify-center gap-2 rounded-control bg-primary px-6 py-3 text-body font-semibold text-white transition-colors duration-150 hover:bg-primary-dark disabled:cursor-not-allowed disabled:bg-surface-muted disabled:text-text-tertiary sm:w-auto">
              {t("landing.hero.topicAction")}
              <ArrowRight className="h-4 w-4" />
            </button>
          </form>
          <a href="#samples" className="mt-4 inline-flex text-meta font-semibold text-primary-accent underline-offset-4 hover:underline">
            {t("landing.hero.ctaSecondary")}
          </a>

          <p className="mt-3 text-meta text-text-tertiary">{t("landing.hero.note")}</p>

          <ul className="mx-auto mt-7 flex max-w-xl flex-wrap items-center justify-center gap-x-5 gap-y-2 lg:mx-0 lg:justify-start">
            {FACTS.map((key) => (
              <li key={key} className="flex items-center gap-1.5 text-meta text-text-secondary">
                <Check className="h-4 w-4 shrink-0 text-primary-accent" strokeWidth={2.4} />
                {t(key)}
              </li>
            ))}
          </ul>
        </div>

        <div className="relative mx-auto flex min-h-52 w-full max-w-sm items-center justify-center lg:min-h-[29rem] lg:max-w-none">
          <span className="soft-mascot-halo absolute h-44 w-44 rounded-full blur-2xl sm:h-64 sm:w-64 lg:h-80 lg:w-80" aria-hidden="true" />

          {/* Floating soft-3D props around the robot, each on its own float
            * rhythm (soft3d-float-prop reuses landing-float-chip) so the
            * composition reads as a small scene rather than one static image.
            * The second prop is sm:+ only - a 360px hero has no room to spare. */}
          <Image
            src="/soft3d/quiz.webp"
            alt=""
            aria-hidden="true"
            width={400}
            height={400}
            className="soft3d-float-prop absolute bottom-[1%] right-[2%] z-0 h-14 w-14 object-contain opacity-90 sm:h-20 sm:w-20 lg:bottom-[8%] lg:right-[0%] lg:h-28 lg:w-28"
            style={{ ["--chip-rot" as string]: "6deg", ["--float-duration" as string]: "5.4s", ["--float-delay" as string]: "0.9s" }}
          />
          <Image
            src="/soft3d/presentation.webp"
            alt=""
            aria-hidden="true"
            width={400}
            height={400}
            className="soft3d-float-prop absolute left-[1%] top-[4%] z-0 hidden h-16 w-16 object-contain opacity-90 sm:block sm:h-20 sm:w-20 lg:h-24 lg:w-24"
            style={{ ["--chip-rot" as string]: "-8deg", ["--float-duration" as string]: "6.2s", ["--float-delay" as string]: "0.3s" }}
          />

          <span className="absolute right-[9%] top-[14%] z-[2] grid h-12 w-12 place-items-center rounded-2xl border border-white/80 bg-white/80 text-primary-accent shadow-card sm:h-14 sm:w-14"><Sparkles className="h-6 w-6" /></span>
          <span className="absolute bottom-[16%] left-[8%] z-[2] grid h-11 w-11 place-items-center rounded-2xl border border-white/80 bg-white/80 text-secondary-accent shadow-card"><span className="text-lg">✦</span></span>
          <Image
            src="/soft3d/teacher-hero.webp"
            alt=""
            aria-hidden="true"
            width={1536}
            height={1024}
            priority
            sizes="(max-width: 639px) 94vw, (max-width: 1023px) 80vw, 38vw"
            className="soft3d-hero-art relative z-[1] h-auto w-full max-w-[38rem] object-contain"
          />
          <div className="soft-floating-card absolute bottom-[4%] right-0 hidden rounded-2xl border px-4 py-3 shadow-card-lift backdrop-blur-sm lg:block lg:right-[4%]">
            <p className="text-micro font-semibold uppercase tracking-wide text-text-tertiary">Dastyor AI</p>
            <p className="mt-0.5 text-meta font-semibold text-text-primary">{t("landing.hero.badge")}</p>
          </div>
        </div>
        </div>

        {/* The real generated pages, directly under the claim they back. */}
        <div className="mx-auto w-full max-w-2xl px-4 pb-12 sm:px-6 sm:pb-16">
          <HeroDocuments />
        </div>
      </section>

      {/* ---- What you gain, and the screen you gain it on ---------------- */}
      <section id="preview" className="border-y border-border-light bg-surface-muted/60">
        <div className="mx-auto w-full max-w-7xl px-4 py-14 sm:px-6 sm:py-18 lg:px-8">
          <div className="grid items-start gap-10 lg:grid-cols-[0.9fr_1.1fr] lg:gap-14">
            <div>
              <SectionHead
                eyebrow="landing.preview.eyebrow"
                title="landing.preview.title"
                subtitle="landing.preview.subtitle"
              />

              {/* The benefits that used to be their own section, now beside
                * the screen that delivers them. */}
              <ul className="mt-7 flex flex-col gap-5">
                {BENEFITS.map(({ icon: Icon, title, desc }) => (
                  <li key={title} className="flex gap-3.5">
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-control bg-primary-50">
                      <Icon className="h-4.5 w-4.5 text-primary-accent" strokeWidth={1.9} />
                    </span>
                    <span className="min-w-0">
                      <span className="block text-body font-semibold text-text-primary">
                        {t(title)}
                      </span>
                      <span className="mt-0.5 block text-meta text-text-secondary">{t(desc)}</span>
                    </span>
                  </li>
                ))}
              </ul>

            </div>

            <div className="lg:sticky lg:top-24">
              <ProductPreview />
              <p className="mt-3 text-meta text-text-tertiary">{t("landing.preview.caption")}</p>
            </div>
          </div>
        </div>
      </section>

      {/* ---- How it works ----------------------------------------------- */}
      <section id="how" className="mx-auto w-full max-w-7xl px-4 py-14 sm:px-6 sm:py-18 lg:px-8">
        <SectionHead eyebrow="landing.nav.how" title="landing.how.title" subtitle="landing.how.subtitle" />
        {/* Numbered because the steps genuinely are a sequence — you cannot
          * pick a topic before you have a subject to pick it in. */}
        <ol className="mt-9 grid gap-7 md:grid-cols-3 md:gap-8">
          {HOW_STEPS.map((step, i) => (
            <li key={step.title} className="flex gap-4">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary text-meta font-bold tabular-nums text-white">
                {i + 1}
              </span>
              <div className="min-w-0 pt-1">
                <h3 className="text-subheading font-semibold text-text-primary">{t(step.title)}</h3>
                <p className="mt-1 text-body text-text-secondary">{t(step.desc)}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      {/* ---- Features, on the dark band, closing on the subject list ----- */}
      <section id="features" className="bg-surface-inverse">
        <div className="mx-auto w-full max-w-7xl px-4 py-14 sm:px-6 sm:py-18 lg:px-8">
          <div className="max-w-2xl">
            <p className="mb-2 text-micro font-semibold uppercase tracking-wide text-primary-light">
              {t("landing.nav.features")}
            </p>
            <h2 className="text-title font-bold text-text-on-inverse sm:text-display">
              {t("landing.features.title")}
            </h2>
            <p className="mt-2.5 text-subheading text-text-on-inverse-muted">
              {t("landing.features.subtitle")}
            </p>
          </div>

          <ul className="mt-9 grid gap-px overflow-hidden rounded-card border border-border-inverse bg-border-inverse sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map(({ id, icon: Icon, bg, color }) => (
              <li key={id} className="flex flex-col bg-surface-inverse p-5">
                <span className={`mb-3.5 flex h-9 w-9 items-center justify-center rounded-control ${bg}`}>
                  <Icon className={`h-4.5 w-4.5 ${color}`} strokeWidth={1.9} />
                </span>
                <h3 className="text-subheading font-semibold text-text-on-inverse">
                  {t(featureTitleKey(id))}
                </h3>
                <p className="mt-1 text-meta leading-relaxed text-text-on-inverse-muted">
                  {t(featureDescKey(id))}
                </p>
              </li>
            ))}
          </ul>

          <div id="subjects" className="mt-9 border-t border-border-inverse pt-8">
            <SubjectStrip inverse />
          </div>
        </div>
      </section>

      {/* ---- Real output -------------------------------------------------- */}
      <section id="samples" className="mx-auto w-full max-w-7xl px-4 py-14 sm:px-6 sm:py-18 lg:px-8">
        <SectionHead
          eyebrow="landing.nav.samples"
          title="landing.samples.title"
          subtitle="landing.samples.subtitle"
        />
        <div className="mt-9">
          <SamplesGallery />
        </div>
      </section>

      {/* ---- FAQ ---------------------------------------------------------- */}
      <section id="faq" className="border-y border-border-light bg-surface-muted/60">
        <div className="mx-auto w-full max-w-7xl px-4 py-14 sm:px-6 sm:py-18 lg:px-8">
          <SectionHead eyebrow="landing.nav.faq" title="landing.faq.title" />
          <div className="mt-8 max-w-3xl">
            <LandingFaq />
          </div>
        </div>
      </section>

      {/* ---- Closing CTA --------------------------------------------------- */}
      <section className="mx-auto w-full max-w-2xl px-4 py-16 text-center sm:py-20">
        <div className="inline-flex items-center gap-1.5 rounded-full border border-primary/15 bg-primary-50 px-3.5 py-1.5 text-micro font-semibold text-primary-accent">
          <Languages className="h-3.5 w-3.5" />
          {t("landing.cta.langs")}
        </div>
        <h2 className="mt-5 text-title font-bold text-text-primary sm:text-display">
          {t("landing.cta.title")}
        </h2>
        <p className="mt-2.5 text-subheading text-text-secondary">{t("landing.cta.subtitle")}</p>
        <Link
          href="/register"
          className="group mt-7 inline-flex items-center gap-2 rounded-control bg-primary px-8 py-3.5 text-body font-semibold text-white transition-colors duration-150 hover:bg-primary-dark"
        >
          {t("landing.hero.ctaPrimary")}
          <ArrowRight className="h-4 w-4 transition-transform duration-150 group-hover:translate-x-0.5" />
        </Link>
      </section>

      {/* ---- Footer --------------------------------------------------------- */}
      <footer className="border-t border-border-light bg-background">
        <div className="mx-auto w-full max-w-7xl px-4 py-11 sm:px-6 lg:px-8">
          <div className="grid gap-9 sm:grid-cols-2 md:grid-cols-[1.4fr_1fr_1fr] lg:gap-14">
            <div>
              <Logo height="1.75rem" />
              <p className="mt-3 max-w-xs text-meta text-text-secondary">
                {t("landing.footer.tagline")}
              </p>
              {/* The app is not on Google Play — a teacher-facing tool for
                * one country does not clear Play's review bar the way a
                * consumer app does — so this direct download is the only
                * install path and belongs in the footer, not buried. */}
              <a
                href="/dastyor.apk"
                download
                className="mt-5 inline-flex items-center gap-3 rounded-card border border-border bg-surface px-4 py-3 transition-colors duration-150 hover:bg-surface-muted"
              >
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-control bg-primary-50">
                  <Smartphone className="h-4.5 w-4.5 text-primary-accent" />
                </span>
                <span className="text-left leading-tight">
                  <span className="block text-micro font-medium text-text-tertiary">
                    {t("landing.footer.android")}
                  </span>
                  <span className="flex items-center gap-1.5 text-meta font-semibold text-text-primary">
                    dastyor.apk
                    {apkSize && (
                      <span className="font-normal text-text-tertiary">
                        · {apkSize} {t("landing.hero.apkMb")}
                      </span>
                    )}
                  </span>
                </span>
              </a>
              <p className="mt-2 text-micro text-text-tertiary">{t("landing.hero.apkNote")}</p>
            </div>

            <nav aria-label={t("landing.footer.product")}>
              <p className="mb-3 text-micro font-semibold uppercase tracking-wide text-text-tertiary">
                {t("landing.footer.product")}
              </p>
              <ul className="flex flex-col gap-2.5">
                {NAV_LINKS.map((l) => (
                  <li key={l.href}>
                    <a
                      href={l.href}
                      className="text-meta text-text-secondary transition-colors duration-150 hover:text-primary-accent"
                    >
                      {t(l.labelKey)}
                    </a>
                  </li>
                ))}
              </ul>
            </nav>

            <nav aria-label={t("landing.footer.legal")}>
              <p className="mb-3 text-micro font-semibold uppercase tracking-wide text-text-tertiary">
                {t("landing.footer.legal")}
              </p>
              {/* Only the two destinations that exist. There is no contact
                * page or support address in this project, so none is
                * invented here. */}
              <ul className="flex flex-col gap-2.5">
                <li>
                  <Link
                    href="/privacy"
                    className="text-meta text-text-secondary transition-colors duration-150 hover:text-primary-accent"
                  >
                    {t("landing.footer.privacy")}
                  </Link>
                </li>
                <li>
                  <Link
                    href="/terms"
                    className="text-meta text-text-secondary transition-colors duration-150 hover:text-primary-accent"
                  >
                    {t("landing.footer.terms")}
                  </Link>
                </li>
                <li>
                  <Link
                    href="/login"
                    className="text-meta text-text-secondary transition-colors duration-150 hover:text-primary-accent"
                  >
                    {t("login.submit")}
                  </Link>
                </li>
              </ul>
            </nav>
          </div>

          <div className="mt-9 flex flex-col items-center justify-between gap-4 border-t border-border-light pt-6 sm:flex-row">
            <p className="text-micro text-text-tertiary">
              © {new Date().getFullYear()} Dastyor. {t("landing.footer.rights")}
            </p>
            <LocaleSwitcher />
          </div>
        </div>
      </footer>
    </main>
  );
}

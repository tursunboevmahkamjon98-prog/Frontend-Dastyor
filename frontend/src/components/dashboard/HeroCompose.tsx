"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { ArrowRight, BookOpen, ClipboardCheck, ClipboardList, FileText, Lightbulb, Presentation, Puzzle, Waypoints } from "lucide-react";
import { CREATE_HREF } from "@/lib/dashboard-nav";
import type { MaterialType } from "@/lib/api";
import type { MessageKey } from "@/lib/messages";
import { useT } from "@/lib/i18n";

type Service = {
  id: string;
  type?: Exclude<MaterialType, "igra">;
  title: MessageKey;
  description: MessageKey;
  icon: typeof BookOpen;
};

const SERVICES: Service[] = [
  { id: "konspekt", type: "konspekt", title: "home.service.konspektTitle", description: "home.service.konspekt", icon: BookOpen },
  { id: "lektsiya", type: "lektsiya", title: "home.service.lektsiyaTitle", description: "home.service.lektsiya", icon: Lightbulb },
  { id: "prezentatsiya", type: "prezentatsiya", title: "home.service.prezentatsiyaTitle", description: "home.service.prezentatsiya", icon: Presentation },
  { id: "test", type: "test", title: "home.service.testTitle", description: "home.service.test", icon: ClipboardCheck },
  { id: "amaliy", type: "amaliy", title: "home.service.amaliyTitle", description: "home.service.amaliy", icon: ClipboardList },
  // A generated konspekt includes lesson_program; its billing type stays konspekt.
  { id: "plan", type: "konspekt", title: "home.service.planTitle", description: "home.service.plan", icon: Waypoints },
  { id: "method", title: "home.service.methodTitle", description: "home.service.method", icon: FileText },
  { id: "crossword", title: "home.service.crosswordTitle", description: "home.service.crossword", icon: Puzzle },
];

const SERVICE_ART: Record<string, string> = {
  konspekt: "/soft3d/book.webp",
  lektsiya: "/soft3d/notebook.webp",
  prezentatsiya: "/soft3d/presentation.webp",
  test: "/soft3d/quiz.webp",
  amaliy: "/soft3d/notebook.webp",
  plan: "/soft3d/book.webp",
  method: "/soft3d/book.webp",
  crossword: "/soft3d/quiz.webp",
};

export default function HeroCompose() {
  const t = useT();
  const router = useRouter();
  const [topic, setTopic] = useState("");
  const trimmed = topic.trim();

  function hrefFor(type: Exclude<MaterialType, "igra">) {
    const query = new URLSearchParams({ type });
    if (trimmed) query.set("topic", trimmed);
    return `${CREATE_HREF}?${query}`;
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (trimmed) router.push(`${CREATE_HREF}?${new URLSearchParams({ topic: trimmed })}`);
  }

  return (
    <section aria-labelledby="home-services-title">
      <div className="soft-compose-panel relative isolate mb-8 overflow-hidden rounded-[1.75rem] border p-5 shadow-card-lift sm:p-8 lg:p-9">
        <div className="relative max-w-3xl">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary-accent">{t("home.aiWorkspace")}</p>
          <h2 id="home-services-title" className="mt-2 text-2xl font-semibold tracking-tight text-text-primary sm:text-3xl">{t("home.composerTitle")}</h2>
          <form onSubmit={submit} className="soft-input-panel mt-6 flex min-h-[4.25rem] min-w-0 items-center gap-3 rounded-2xl border p-2 shadow-card-lift ring-1 ring-black/[0.025] focus-within:ring-2 focus-within:ring-primary/20 sm:max-w-2xl sm:p-2.5">
            <span aria-hidden className="ml-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-primary-50 to-[#fff0e4] text-primary-accent shadow-sm"><BookOpen className="h-5 w-5" /></span>
            <label htmlFor="home-topic" className="sr-only">{t("create.topicTitle")}</label>
            <input id="home-topic" value={topic} onChange={(event) => setTopic(event.target.value)}
              placeholder={t("home.composerPlaceholder")} maxLength={200}
              className="min-w-0 flex-1 bg-transparent py-2 text-base text-text-primary outline-none placeholder:text-text-tertiary sm:text-lg" />
            <button type="submit" disabled={!trimmed} aria-label={t("home.composerAction")}
              className="flex h-11 shrink-0 items-center justify-center gap-2 rounded-xl bg-primary px-4 text-meta font-semibold text-white shadow-sm transition-all hover:bg-primary-dark disabled:cursor-not-allowed disabled:bg-surface-muted disabled:text-text-tertiary sm:px-5">
              <span className="hidden sm:inline">{t("home.composerAction")}</span><ArrowRight className="h-5 w-5" />
            </button>
          </form>
          <p className="mt-2 px-1 text-xs text-text-tertiary">{t("home.composerHint")}</p>
        </div>
      </div>

      {/* Primary vs. placeholder used to be one undifferentiated grid of
        * eight equal cards, told apart only by a corner label easy to miss.
        * The six real, routable types (service.type is set) now get a
        * larger, more deliberate grid; the two not-yet-built ones (method,
        * crossword) move to a visually distinct, compact strip below so
        * "what can I actually make today" reads at a glance. */}
      <div className="mb-4 mt-9 flex items-center justify-between gap-3">
        <h3 className="text-lg font-semibold tracking-tight text-text-primary">{t("home.primaryTypes")}</h3>
        <span className="text-xs text-text-tertiary">{t("home.nextStep")}</span>
      </div>
      <div className="grid gap-3.5 sm:grid-cols-2 xl:grid-cols-3">
        {SERVICES.filter((s) => s.type).map((service) => {
          const Icon = service.icon;
          return (
            <Link
              key={service.id}
              href={hrefFor(service.type!)}
              data-type={service.id}
              className="dashboard-service-card group relative flex min-h-48 flex-col overflow-hidden rounded-[1.6rem] border border-white/90 p-5 shadow-card transition-all hover:-translate-y-1 hover:shadow-card-lift sm:min-h-52 sm:p-6"
            >
              <div className="relative z-10 flex h-full w-[calc(100%-5rem)] flex-col">
                <span className={`flex h-12 w-12 items-center justify-center rounded-2xl border border-white/80 shadow-[0_5px_12px_rgba(50,35,30,0.08)] ${service.id === "prezentatsiya" ? "bg-[var(--color-pres-bg)] text-[var(--color-pres-icon)]" : service.id === "test" || service.id === "amaliy" ? "bg-[var(--color-test-bg)] text-[var(--color-test-icon)]" : service.id === "lektsiya" || service.id === "plan" ? "bg-[var(--color-lecture-bg)] text-[var(--color-lecture-icon)]" : "bg-[var(--color-note-bg)] text-[var(--color-note-icon)]"}`}>
                  <Icon className="h-5.5 w-5.5" strokeWidth={1.8} />
                </span>
                <span className="mt-5 text-lg font-semibold text-text-primary">{t(service.title)}</span>
                <span className="mt-1.5 line-clamp-2 text-sm leading-snug text-text-secondary">{t(service.description)}</span>
                <span className="mt-auto flex items-center gap-1.5 pt-3 text-sm font-semibold text-primary-accent">
                  {t("home.composerAction")}
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                </span>
              </div>
              <Image src={SERVICE_ART[service.id]} alt="" aria-hidden="true" width={280} height={280} sizes="140px" className="dashboard-service-art h-28 w-28 sm:h-32 sm:w-32" />
            </Link>
          );
        })}
      </div>

      <div className="mt-7 flex items-center gap-3 rounded-2xl border border-dashed border-border px-4 py-3.5 sm:px-5">
        <span className="shrink-0 text-xs font-semibold uppercase tracking-[0.12em] text-text-tertiary">{t("home.comingSoon")}</span>
        <div className="flex min-w-0 flex-1 flex-wrap gap-2">
          {SERVICES.filter((s) => !s.type).map((service) => {
            const Icon = service.icon;
            return (
              <span key={service.id} data-type={service.id} className="flex items-center gap-2 rounded-full border border-border-light bg-surface-muted px-3 py-1.5 text-xs font-medium text-text-tertiary">
                <Icon className="h-3.5 w-3.5" strokeWidth={1.8} />
                {t(service.title)}
              </span>
            );
          })}
        </div>
      </div>
    </section>
  );
}

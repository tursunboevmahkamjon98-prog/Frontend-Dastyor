"use client";

import { useEffect, useRef, useState, type DragEvent } from "react";
import Link from "next/link";
import { ArrowRight, BookOpen, Check, FileText, Loader2, UploadCloud } from "lucide-react";
import CreateModeTabs from "@/components/dashboard/CreateModeTabs";
import { ErrorNote, StepBadge } from "@/components/ui";
import { bookApi, type BookSource } from "@/lib/book-api";
import { ApiError, type GenerateAllResult, type MaterialType } from "@/lib/api";
import { CLASSES, LANGUAGES, LEVELS, MATERIAL_TYPE_CONFIG, MATERIAL_TYPE_LABEL_KEY, SUBJECTS } from "@/lib/material-types";
import { useT } from "@/lib/i18n";
import type { MessageKey } from "@/lib/messages";

type CreatableType = Exclude<MaterialType, "igra">;
type Scope = "all" | "chapter" | "pages";
const TYPES: CreatableType[] = ["konspekt", "lektsiya", "prezentatsiya", "test", "amaliy"];
const ERROR_KEYS: Record<string, MessageKey> = {
  empty_file: "book.error.empty_file", file_too_large: "book.error.file_too_large",
  unsupported_file: "book.error.unsupported_file", invalid_pdf: "book.error.invalid_pdf",
  encrypted_pdf: "book.error.encrypted_pdf", page_limit: "book.error.page_limit",
  too_many_scanned_pages: "book.error.too_many_scanned_pages", ocr_unavailable: "book.error.ocr_unavailable",
  ocr_failed: "book.error.ocr_failed", no_text: "book.error.no_text",
  extraction_timeout: "book.error.extraction_timeout", topic_not_found: "book.error.topic_not_found",
  extraction_busy: "book.error.extraction_busy", invalid_scope: "book.error.invalid_scope",
  invalid_pages: "book.error.invalid_pages", invalid_chapter: "book.error.invalid_chapter",
  not_found: "book.error.not_found",
};

export default function BookCreatePage() {
  const t = useT();
  const inputRef = useRef<HTMLInputElement>(null);
  const generationRef = useRef<AbortController | null>(null);
  const [source, setSource] = useState<BookSource | null>(null);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [scope, setScope] = useState<Scope>("all");
  const [chapterIndex, setChapterIndex] = useState(0);
  const [pageStart, setPageStart] = useState(1);
  const [pageEnd, setPageEnd] = useState(1);
  const [topic, setTopic] = useState("");
  const [subject, setSubject] = useState(SUBJECTS[0]);
  const [grade, setGrade] = useState(CLASSES[6]);
  const [language, setLanguage] = useState(LANGUAGES[0]);
  const [selected, setSelected] = useState<CreatableType[]>(["konspekt"]);
  const [creating, setCreating] = useState(false);
  const [result, setResult] = useState<GenerateAllResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => () => generationRef.current?.abort(), []);

  function message(err: unknown) {
    if (err instanceof ApiError && ERROR_KEYS[err.message]) return t(ERROR_KEYS[err.message]);
    if (err instanceof ApiError && err.status === 404 && /^not found$/i.test(err.message.trim())) {
      return t("book.error.api_route_missing");
    }
    return err instanceof ApiError ? err.message : t("common.error");
  }

  async function upload(file: File | undefined) {
    if (!file) return;
    setError(null);
    setResult(null);
    setSource(null);
    setUploading(true);
    try {
      const uploaded = await bookApi.upload(file);
      setSource(uploaded);
      setScope("all");
      setPageStart(1);
      setPageEnd(uploaded.page_count);
      setChapterIndex(0);
    } catch (err) {
      setError(message(err));
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  function drop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    void upload(event.dataTransfer.files[0]);
  }

  function toggleType(type: CreatableType) {
    setSelected((current) => current.includes(type) ? current.filter((entry) => entry !== type) : [...current, type]);
  }

  async function generate() {
    if (!source || !selected.length) return;
    if (scope === "pages" && (pageStart < 1 || pageEnd > source.page_count || pageStart > pageEnd)) {
      setError(t("book.error.invalid_pages"));
      return;
    }
    setError(null);
    setCreating(true);
    const controller = new AbortController();
    generationRef.current = controller;
    try {
      const created = await bookApi.generate({
        source_id: source.id, scope,
        chapter_index: scope === "chapter" ? chapterIndex : undefined,
        page_start: scope === "pages" ? pageStart : undefined,
        page_end: scope === "pages" ? pageEnd : undefined,
        topic: topic.trim(), subject, grade, language, level: LEVELS[1], types: selected,
      }, controller.signal);
      setResult(created);
    } catch (err) {
      if (controller.signal.aborted) return;
      setError(message(err));
    } finally {
      if (generationRef.current === controller) generationRef.current = null;
      setCreating(false);
    }
  }

  const made = result ? selected.filter((type) => result.content[type]) : [];
  const failed = result ? selected.filter((type) => !result.content[type]) : [];

  return <div className="create-page mx-auto max-w-6xl px-4 pb-28 pt-6 sm:px-6 sm:pt-8 lg:px-8 lg:pb-12">
    <header className="mb-6 flex items-end justify-between gap-4"><div><p className="mb-2 text-micro font-semibold uppercase tracking-[0.16em] text-primary-accent">{t("home.aiWorkspace")}</p><h1 className="text-title font-semibold tracking-tight text-text-primary sm:text-display">{t("book.title")}</h1>
      <p className="mt-1 text-meta text-text-secondary sm:text-body">{t("book.intro")}</p></div></header>
    <CreateModeTabs mode="book" />
    {error && <div className="mb-5"><ErrorNote>{error}</ErrorNote></div>}

    {result ? <div className="space-y-5">
      <section className="rounded-2xl border border-border bg-surface p-5 sm:p-7">
        <h2 className="text-xl font-semibold text-text-primary">{made.length === 0 ? t("create.failedToCreate") : failed.length ? t("create.partiallyDone") : t("create.done")}</h2>
        <p className="mt-2 text-sm text-text-secondary">{t("book.source")}: {result.source?.document_title ?? source?.title}</p>
        {result.source && <p className="mt-1 text-sm text-text-secondary">{t("book.usedPages")}: {result.source.used_pages.join(", ")}</p>}
        {result.source && result.source.unreadable_pages.length > 0 && <p className="mt-1 text-sm text-text-secondary">{t("book.unreadable")}: {result.source.unreadable_pages.join(", ")}</p>}
        {result.source?.selection_is_excerpt && <p className="mt-3 text-sm text-text-secondary">{t("book.excerptNote")}</p>}
        <p className="mt-2 text-sm text-text-secondary">{t("book.groundingNote")}</p>
      </section>
      <div className="grid gap-3 sm:grid-cols-2">{made.map((type) => {
        const id = result.ids[type];
        const Icon = MATERIAL_TYPE_CONFIG[type].icon;
        return id && <Link key={type} href={`/dashboard/materials/${type}/${id}`} className="flex items-center gap-3 rounded-2xl border border-border bg-surface p-4 text-sm font-semibold text-text-primary shadow-card hover:border-primary/40">
          <Icon className="h-5 w-5 text-primary-accent" />{t(MATERIAL_TYPE_LABEL_KEY[type])}<ArrowRight className="ml-auto h-4 w-4" />
        </Link>;
      })}</div>
      {failed.length > 0 && <p className="text-sm text-text-secondary">{t("create.partiallyDone")}: {failed.map((type) => t(MATERIAL_TYPE_LABEL_KEY[type])).join(", ")}</p>}
      <button type="button" onClick={() => setResult(null)} className="text-sm font-semibold text-primary-accent">{t("book.replace")}</button>
    </div> : <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_19rem]">
      <div className="min-w-0 space-y-6">
        <section className="rounded-card border border-border-light bg-surface p-5 shadow-card sm:p-6">
          <h2 className="flex items-center gap-2.5 text-lg font-semibold text-text-primary"><StepBadge n={1} />{t("book.uploadTitle")}</h2>
          <input ref={inputRef} type="file" accept="application/pdf,.pdf" className="sr-only" onChange={(event) => void upload(event.target.files?.[0])} />
          <div onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={drop}
            className={`relative mt-4 flex min-h-40 flex-col items-center justify-center overflow-hidden rounded-[1.5rem] border border-dashed px-4 py-5 text-center transition-colors ${dragging ? "border-secondary bg-secondary-50" : "border-primary/30 bg-gradient-to-br from-primary-50 to-secondary-50"}`}>
            <BookOpen
              aria-hidden="true"
              className="pointer-events-none absolute -right-2 -top-2 h-16 w-16 text-primary/15 sm:h-20 sm:w-20"
              style={{ animation: "landing-float-chip 6s ease-in-out infinite" }}
            />
            {uploading ? <Loader2 className="h-8 w-8 animate-spin text-primary-accent" /> : <UploadCloud className="h-8 w-8 text-primary-accent" />}
            <p className="mt-2 text-sm text-text-secondary">{uploading ? t("book.uploading") : t("book.uploadHint")}</p>
            <button type="button" onClick={() => inputRef.current?.click()} disabled={uploading}
              className="mt-3 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary-dark disabled:opacity-50">{source ? t("book.replace") : t("book.choose")}</button>
          </div>
          {source && <div className="mt-4 rounded-xl border border-border bg-surface-muted/50 p-4">
            <div className="flex items-center gap-3"><FileText className="h-6 w-6 text-primary-accent" /><div className="min-w-0"><p className="truncate text-sm font-semibold text-text-primary">{source.title}</p>
              <p className="text-xs text-text-secondary">{source.page_count} {t("book.pages")}{source.ocr_pages ? ` · ${source.ocr_pages} ${t("book.ocrPages")}` : ""}</p></div><Check className="ml-auto h-5 w-5 text-primary-accent" /></div>
            {source.unreadable_pages > 0 && <p className="mt-2 text-xs text-text-secondary">{t("book.unreadable")}: {source.unreadable_pages}</p>}
          </div>}
          <p className="mt-3 text-xs text-text-tertiary">{t("book.privacyNote")}</p>
        </section>

        {source && <>
          <section className="rounded-2xl border border-border bg-surface p-5 sm:p-6">
            <h2 className="flex items-center gap-2.5 text-lg font-semibold text-text-primary"><StepBadge n={2} />{t("book.scopeTitle")}</h2>
            <div className="mt-4 grid gap-2 sm:grid-cols-3">{(["all", "chapter", "pages"] as const).map((value) => <button key={value} type="button"
              onClick={() => setScope(value)} disabled={value === "chapter" && source.chapters.length === 0}
              aria-pressed={scope === value} className={`rounded-xl border px-3 py-3 text-left text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-40 ${scope === value ? "border-primary bg-primary-50 text-primary-accent" : "border-border text-text-secondary hover:border-primary/40"}`}>
              {t(value === "all" ? "book.scopeAll" : value === "chapter" ? "book.scopeChapter" : "book.scopePages")}
            </button>)}</div>
            {source.chapters.length === 0 && <p className="mt-3 text-xs text-text-tertiary">{t("book.noChapters")}</p>}
            {scope === "chapter" && <label className="mt-4 block text-sm text-text-secondary">{t("book.chapter")}
              <select value={chapterIndex} onChange={(event) => setChapterIndex(Number(event.target.value))} className="mt-2 w-full rounded-xl border border-border bg-surface p-3 text-text-primary">
                {source.chapters.map((chapter, index) => <option key={`${chapter.start_page}:${index}`} value={index}>{chapter.title} ({chapter.start_page}–{chapter.end_page})</option>)}
              </select></label>}
            {scope === "pages" && <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <label className="text-sm text-text-secondary">{t("book.pageFrom")}<input type="number" min={1} max={source.page_count} value={pageStart} onChange={(event) => setPageStart(Number(event.target.value))} className="mt-2 w-full rounded-xl border border-border bg-surface p-3 text-text-primary" /></label>
              <label className="text-sm text-text-secondary">{t("book.pageTo")}<input type="number" min={1} max={source.page_count} value={pageEnd} onChange={(event) => setPageEnd(Number(event.target.value))} className="mt-2 w-full rounded-xl border border-border bg-surface p-3 text-text-primary" /></label>
            </div>}
          </section>
          <section className="rounded-2xl border border-border bg-surface p-5 sm:p-6">
            <h2 className="flex items-center gap-2.5 text-lg font-semibold text-text-primary"><StepBadge n={3} />{t("book.settings")}</h2>
            <label className="mt-4 block text-sm font-medium text-text-secondary">{t("book.topic")}
              <input value={topic} onChange={(event) => setTopic(event.target.value)} maxLength={200} placeholder={source.title} className="mt-2 w-full rounded-xl border border-border bg-surface p-3 text-text-primary outline-none focus:border-primary" /></label>
            <p className="mt-1 text-xs text-text-tertiary">{t("book.topicHint")}</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <Picker label={t("create.subjectTitle")} value={subject} options={SUBJECTS} onChange={setSubject} />
              <Picker label={t("create.gradeTitle")} value={grade} options={CLASSES} onChange={setGrade} />
              <Picker label={t("create.languageTitle")} value={language} options={LANGUAGES} onChange={setLanguage} />
            </div>
            <p className="mt-5 text-sm font-semibold text-text-primary">{t("home.pickType")}</p>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">{TYPES.map((type) => {
              const cfg = MATERIAL_TYPE_CONFIG[type];
              const Icon = cfg.icon;
              const active = selected.includes(type);
              return <button key={type} type="button" onClick={() => toggleType(type)} aria-pressed={active}
                className={`flex items-center gap-3 rounded-xl border p-3 text-left text-sm font-semibold transition-colors ${active ? "text-text-primary" : "border-border bg-surface text-text-secondary hover:border-primary/40"}`}
                style={active ? { borderColor: `var(${cfg.accentVar})`, backgroundColor: `color-mix(in srgb, var(${cfg.accentVar}) 12%, var(--color-surface))` } : undefined}>
                <span className={active ? "" : cfg.color}><Icon className="h-5 w-5 shrink-0" style={active ? { color: `var(${cfg.accentVar})` } : undefined} /></span>
                <span className="flex-1">{t(MATERIAL_TYPE_LABEL_KEY[type])}</span>
                {active && <Check className="ml-auto h-4 w-4 shrink-0" style={{ color: `var(${cfg.accentVar})` }} />}
              </button>;
            })}</div>
            <p className="mt-3 text-xs text-text-tertiary">{t("home.service.plan")}</p>
          </section>
        </>}
      </div>

      {source && <aside className="rounded-card border border-border-light bg-surface p-5 shadow-card-lift lg:sticky lg:top-24" aria-live="polite">
        <p className="text-sm text-text-secondary">{t("book.groundingNote")}</p>
        <button type="button" onClick={generate} disabled={creating || !selected.length}
          className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-4 py-3 text-sm font-semibold text-white hover:bg-primary-dark disabled:cursor-not-allowed disabled:bg-surface-muted disabled:text-text-tertiary">
          {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : <BookOpen className="h-4 w-4" />}{creating ? t("book.generating") : t("book.generate")}
        </button>
      </aside>}
    </div>}
  </div>;
}

function Picker({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (value: string) => void }) {
  return <label className="text-sm font-medium text-text-secondary">{label}<select value={value} onChange={(event) => onChange(event.target.value)} className="mt-2 w-full rounded-xl border border-border bg-surface p-3 text-text-primary">
    {options.map((option) => <option key={option} value={option}>{option}</option>)}
  </select></label>;
}

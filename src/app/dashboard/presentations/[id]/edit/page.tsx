"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  ChevronDown,
  ChevronUp,
  Copy,
  Download,
  Loader2,
  Maximize2,
  Plus,
  RefreshCw,
  Trash2,
  X,
} from "lucide-react";
import { materialsApi, downloadMaterial, ApiError, API_ORIGIN } from "@/lib/api";
import { KONSPEKT_TEMPLATES, PRESENTATION_TEMPLATES, getSubjectAccent } from "@/lib/material-types";
import { deckTemplateName, templateById, subjectTemplateFor } from "@/lib/subject-templates";
import SubjectTemplatePreview from "@/components/SubjectTemplatePreview";
import PresentMode from "@/components/PresentMode";
import VisualBlockView, { VisualBlock, SlideHeader } from "@/components/presentation/SlideVisuals";

interface Slide {
  title: string;
  bullet_points?: string[];
  body?: string;
  speaker_notes?: string;
  visual?: VisualBlock;
  image?: { path: string; caption?: string; credit?: string };
  kind?: string;
  image_query?: string;
}








export default function PresentationEditorPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = params.id;

  const [item, setItem] = useState<{ title: string; subject: string; grade: string } | null>(null);
  const [content, setContent] = useState<Record<string, unknown>>({});
  const [selected, setSelected] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved">("idle");
  const [regenerating, setRegenerating] = useState(false);
  const [addingSlide, setAddingSlide] = useState(false);
  const [presenting, setPresenting] = useState(false);
  const [downloading, setDownloading] = useState<string | null>(null);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    materialsApi
      .get("prezentatsiya", id)
      .then((loaded) => {
        setItem({ title: loaded.title, subject: loaded.subject, grade: loaded.grade });
        try {
          setContent(JSON.parse(loaded.slides_json ?? "{}"));
        } catch {
          setContent({});
        }
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Не удалось загрузить презентацию"));
  }, [id]);

  const slides = (content.slides as Slide[] | undefined) ?? [];
  const accent = getSubjectAccent(content.subject as string | undefined);
  
  
  
  
  const deckDesignName = deckTemplateName(content.template as string | undefined);
  const deckDesign = templateById(content.template as string | undefined)
    ?? (PRESENTATION_TEMPLATES.some((t) => t.id === content.template)
        ? undefined                      
        : subjectTemplateFor(content.subject as string | undefined));

  
  
  
  
  
  const legacyTmpl = PRESENTATION_TEMPLATES.find((t) => t.id === content.template);
  const tmpl = legacyTmpl ?? {
    ...PRESENTATION_TEMPLATES[0],
    name: deckDesignName,
    deck: {
      ...PRESENTATION_TEMPLATES[0].deck,
      paper: deckDesign?.bg ?? "#ffffff",
      ink: deckDesign?.ink ?? "#1e2937",
      header:
        deckDesign?.header === "band" ? "band" as const
        : deckDesign?.header === "underline" || deckDesign?.header === "prompt"
          || deckDesign?.header === "measure" ? "underline" as const
        : deckDesign?.header === "smallcaps" ? "plain" as const
        : "rule" as const,
      cards: deckDesign?.card !== "quote",
      badge: true,
      pastel: deckDesign?.card === "pastel",
      serif: Boolean(deckDesign?.serif),
      caps: deckDesign?.header === "smallcaps",
    },
  };
  const presentTmpl = KONSPEKT_TEMPLATES.find((t) => t.id === content.template) ?? KONSPEKT_TEMPLATES[0];

  
  
  
  
  
  
  
  function persist(next: Record<string, unknown>) {
    setContent(next);
    setSaveState("saving");
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(async () => {
      try {
        await materialsApi.update("prezentatsiya", id, { slides_json: JSON.stringify(next) });
        setSaveState("saved");
      } catch {
        setSaveState("idle");
      }
    }, 800);
  }

  function updateSlides(nextSlides: Slide[]) {
    persist({ ...content, slides: nextSlides });
  }

  function updateSlide(index: number, patch: Partial<Slide>) {
    updateSlides(slides.map((s, i) => (i === index ? { ...s, ...patch } : s)));
  }

  function moveSlide(index: number, dir: -1 | 1) {
    const target = index + dir;
    if (target < 0 || target >= slides.length) return;
    const next = [...slides];
    [next[index], next[target]] = [next[target], next[index]];
    updateSlides(next);
    setSelected(target);
  }

  function deleteSlide(index: number) {
    if (slides.length <= 1) return;
    if (!confirm("Удалить этот слайд?")) return;
    const next = slides.filter((_, i) => i !== index);
    updateSlides(next);
    setSelected((s) => Math.min(s, next.length - 1));
  }

  function duplicateSlide(index: number) {
    const clone: Slide = JSON.parse(JSON.stringify(slides[index]));
    const next = [...slides.slice(0, index + 1), clone, ...slides.slice(index + 1)];
    updateSlides(next);
    setSelected(index + 1);
  }

  
  
  
  
  
  
  async function regenerateAt(index: number, replace: boolean) {
    if (!item) return;
    if (replace) setRegenerating(true);
    else setAddingSlide(true);
    try {
      const result = await materialsApi.regeneratePresentationSlide({
        topic: item.title,
        subject: item.subject,
        language: typeof content.language === "string" ? content.language : "Русский",
        level: typeof content.level === "string" ? content.level : "Средний",
        grade: item.grade,
        item_index: index,
        existing_items: slides as unknown as Record<string, unknown>[],
      });
      const nextSlide = result.item as unknown as Slide;
      if (replace) {
        updateSlide(index, nextSlide);
      } else {
        const next = [...slides, nextSlide];
        updateSlides(next);
        setSelected(next.length - 1);
      }
    } catch {
      
    } finally {
      if (replace) setRegenerating(false);
      else setAddingSlide(false);
    }
  }

  async function handleDownload(format: "pptx" | "pdf") {
    setDownloading(format);
    try {
      const language = typeof content.language === "string" ? content.language : "Русский";
      await downloadMaterial(format, { material_type: "prezentatsiya", content, language });
    } catch {
      
    } finally {
      setDownloading(null);
    }
  }

  if (error) {
    return <div className="px-4 pt-10 text-center text-sm text-primary-dark">{error}</div>;
  }
  if (!item) {
    return <div className="px-4 pt-10 text-center text-sm text-text-secondary">Загрузка...</div>;
  }

  const s = slides[selected];

  return (
    <div className="flex h-[calc(100dvh-4rem)] flex-col lg:h-dvh">
      {}
      <div className="flex shrink-0 items-center justify-between border-b border-border-light bg-surface px-4 py-3">
        <div className="flex min-w-0 items-center gap-3">
          <button
            onClick={() => router.push(`/dashboard/materials/prezentatsiya/${id}`)}
            className="flex items-center gap-1.5 text-sm font-medium text-text-secondary shrink-0"
          >
            <ArrowLeft className="h-4 w-4" />
            Назад
          </button>
          <h1 className="truncate text-sm font-semibold text-text-primary">{item.title}</h1>
        </div>
        <div className="flex shrink-0 items-center gap-2 text-xs text-text-tertiary">
          {saveState === "saving" && (
            <span className="flex items-center gap-1">
              <Loader2 className="h-3 w-3 animate-spin" /> Сохранение…
            </span>
          )}
          {saveState === "saved" && <span>Сохранено</span>}
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col lg:grid lg:grid-cols-[220px_1fr_300px]">
        {}
        <div className="flex shrink-0 gap-2 overflow-x-auto border-b border-border-light bg-surface-muted p-3 lg:h-full lg:w-[220px] lg:flex-col lg:overflow-y-auto lg:overflow-x-hidden lg:border-b-0 lg:border-r">
          {slides.map((slide, i) => (
            <div
              key={i}
              onClick={() => setSelected(i)}
              className={`group relative shrink-0 cursor-pointer rounded-lg border p-1.5 lg:shrink transition ${
                i === selected ? "border-primary ring-2 ring-primary/20" : "border-border hover:border-border-strong"
              }`}
              style={{ width: "clamp(104px, 30vw, 150px)" }}
            >
              <div
                className="overflow-hidden rounded"
                style={{ aspectRatio: "16 / 9", backgroundColor: tmpl.deck.paper }}
              >
                <div className="px-1.5 pt-1" style={tmpl.deck.header === "band" ? { backgroundColor: accent, paddingBottom: 3 } : undefined}>
                  <p
                    className="line-clamp-2 text-[7px] font-bold leading-tight"
                    style={{ color: tmpl.deck.header === "band" ? "#fff" : tmpl.deck.ink }}
                  >
                    {i + 1}. {slide.title || "Без названия"}
                  </p>
                </div>
              </div>
              {}
              <div className="absolute -top-1.5 -right-1.5 flex gap-0.5 [@media(hover:hover)]:hidden [@media(hover:hover)]:group-hover:flex">
                <button
                  title="Вверх"
                  onClick={(e) => {
                    e.stopPropagation();
                    moveSlide(i, -1);
                  }}
                  disabled={i === 0}
                  className="flex h-7 w-7 items-center justify-center rounded-full bg-surface text-text-secondary shadow disabled:opacity-30 [@media(hover:hover)]:h-5 [@media(hover:hover)]:w-5"
                >
                  <ChevronUp className="h-3.5 w-3.5 [@media(hover:hover)]:h-3 [@media(hover:hover)]:w-3" />
                </button>
                <button
                  title="Вниз"
                  onClick={(e) => {
                    e.stopPropagation();
                    moveSlide(i, 1);
                  }}
                  disabled={i === slides.length - 1}
                  className="flex h-7 w-7 items-center justify-center rounded-full bg-surface text-text-secondary shadow disabled:opacity-30 [@media(hover:hover)]:h-5 [@media(hover:hover)]:w-5"
                >
                  <ChevronDown className="h-3.5 w-3.5 [@media(hover:hover)]:h-3 [@media(hover:hover)]:w-3" />
                </button>
              </div>
              <div className="mt-1 flex items-center justify-between">
                <span className="text-[10px] text-text-tertiary">{i + 1}</span>
                <div className="flex gap-1">
                  <button
                    title="Дублировать"
                    onClick={(e) => {
                      e.stopPropagation();
                      duplicateSlide(i);
                    }}
                    className="text-text-tertiary hover:text-text-primary"
                  >
                    <Copy className="h-3 w-3" />
                  </button>
                  <button
                    title="Удалить"
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteSlide(i);
                    }}
                    disabled={slides.length <= 1}
                    className="text-text-tertiary hover:text-primary-dark disabled:opacity-30"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </div>
              </div>
            </div>
          ))}
          <button
            onClick={() => regenerateAt(slides.length, false)}
            disabled={addingSlide}
            className="flex shrink-0 items-center justify-center gap-1.5 rounded-lg border border-dashed border-border-strong px-3 py-2 text-xs font-medium text-text-secondary hover:border-primary hover:text-primary disabled:opacity-60 lg:w-full"
            style={{ minWidth: 110 }}
          >
            {addingSlide ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
            Слайд
          </button>
        </div>

        {}
        <div className="min-h-0 flex-1 overflow-y-auto p-4 lg:p-8">
          {s ? (
            <div
              className="relative mx-auto max-w-3xl overflow-hidden rounded-2xl border shadow-sm"
              style={{ borderColor: `${accent}22`, background: `linear-gradient(135deg, ${accent}0d 0%, #ffffff 45%, ${accent}12 100%)` }}
            >
              <div className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full blur-3xl" style={{ backgroundColor: `${accent}1f` }} aria-hidden />
              <div className="relative">
                <SlideHeader index={selected} title={s.title} accent={accent} header={tmpl.deck.header === "band" ? "bar" : tmpl.deck.header === "underline" ? "underline" : tmpl.deck.caps ? "smallcaps" : "numbered"} />
                <div className="space-y-3 p-4 pt-3">
                  {}
                  <input
                    value={s.title}
                    onChange={(e) => updateSlide(selected, { title: e.target.value })}
                    placeholder="Заголовок слайда"
                    className="w-full rounded-lg border border-transparent bg-white/60 px-2 py-1 text-sm font-semibold text-text-primary outline-none focus:border-primary/40 focus:bg-white"
                  />

                  {}
                  <div className="space-y-1.5">
                    {(s.bullet_points ?? []).map((b, j) => (
                      <div key={j} className="flex items-center gap-2">
                        <span className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ backgroundColor: accent }} aria-hidden />
                        <input
                          value={b}
                          onChange={(e) => {
                            const next = [...(s.bullet_points ?? [])];
                            next[j] = e.target.value;
                            updateSlide(selected, { bullet_points: next });
                          }}
                          className="min-w-0 flex-1 rounded-lg border border-transparent bg-white/50 px-2 py-1 text-sm text-text-primary outline-none focus:border-primary/40 focus:bg-white"
                        />
                        <button
                          onClick={() => {
                            const next = (s.bullet_points ?? []).filter((_, k) => k !== j);
                            updateSlide(selected, { bullet_points: next });
                          }}
                          className="shrink-0 text-text-tertiary hover:text-primary-dark"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    ))}
                    <button
                      onClick={() => updateSlide(selected, { bullet_points: [...(s.bullet_points ?? []), ""] })}
                      className="flex items-center gap-1 text-xs font-medium text-text-tertiary hover:text-primary"
                    >
                      <Plus className="h-3 w-3" /> Добавить пункт
                    </button>
                  </div>

                  {s.visual && <VisualBlockView visual={s.visual} accent={accent} />}

                  {s.image && (
                    <div className="relative">
                      <img src={`${API_ORIGIN}${s.image.path}`} alt={s.image.caption ?? ""} className="max-h-56 w-full rounded-lg object-cover" />
                      <button
                        onClick={() => {
                          const { image: _drop, ...rest } = s;
                          void _drop;
                          updateSlides(slides.map((sl, i) => (i === selected ? (rest as Slide) : sl)));
                        }}
                        className="absolute right-2 top-2 flex h-6 w-6 items-center justify-center rounded-full bg-black/50 text-white hover:bg-black/70"
                        title="Удалить изображение"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  )}

                  {}
                  <textarea
                    value={s.body ?? ""}
                    onChange={(e) => updateSlide(selected, { body: e.target.value })}
                    placeholder="Краткое пояснение (необязательно)"
                    rows={2}
                    className="w-full resize-none rounded-lg border border-transparent bg-white/50 px-2 py-1.5 text-xs text-text-secondary outline-none focus:border-primary/40 focus:bg-white"
                  />

                  {}
                  <div>
                    <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-text-tertiary">Заметки для учителя</p>
                    <textarea
                      value={s.speaker_notes ?? ""}
                      onChange={(e) => updateSlide(selected, { speaker_notes: e.target.value })}
                      rows={3}
                      className="w-full resize-none rounded-lg border-l-[3px] bg-white/70 p-2 text-xs italic text-text-secondary outline-none"
                      style={{ borderLeftColor: accent }}
                    />
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-center text-sm text-text-secondary">Нет слайдов</p>
          )}
        </div>

        {}
        <div className="shrink-0 space-y-4 border-t border-border-light bg-surface p-4 lg:h-full lg:w-[300px] lg:overflow-y-auto lg:border-l lg:border-t-0">
          <button
            onClick={() => regenerateAt(selected, true)}
            disabled={regenerating || !s}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary py-2.5 text-sm font-semibold text-white shadow-sm shadow-primary/25 transition hover:bg-primary-dark disabled:opacity-60"
          >
            {regenerating ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            Пересоздать слайд
          </button>

          <button
            onClick={() => setPresenting(true)}
            disabled={slides.length === 0}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-border bg-surface-muted py-2.5 text-sm font-semibold text-text-primary transition hover:bg-surface disabled:opacity-60"
          >
            <Maximize2 className="h-4 w-4" />
            На весь экран
          </button>

          {}
          <div className="rounded-xl border border-border bg-surface p-3">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-tertiary">
              Оформление
            </p>
            {deckDesign && <SubjectTemplatePreview template={deckDesign} className="mb-2" />}
            <p className="text-sm font-medium text-text-primary">{deckDesignName}</p>
            {deckDesign && (
              <p className="mt-0.5 text-xs leading-snug text-text-tertiary">{deckDesign.note}</p>
            )}
          </div>

          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-tertiary">Скачать</p>
            <div className="flex gap-2">
              {(["pptx", "pdf"] as const).map((f) => (
                <button
                  key={f}
                  onClick={() => handleDownload(f)}
                  disabled={downloading !== null}
                  className="flex flex-1 items-center justify-center gap-1.5 rounded-xl border border-border bg-surface px-3 py-2 text-sm font-medium text-text-primary hover:bg-surface-muted disabled:opacity-60"
                >
                  {downloading === f ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                  .{f}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {presenting && (
        <PresentMode
          slides={slides}
          accent={accent}
          template={presentTmpl}
          initialIndex={selected}
          onClose={() => setPresenting(false)}
        />
      )}
    </div>
  );
}

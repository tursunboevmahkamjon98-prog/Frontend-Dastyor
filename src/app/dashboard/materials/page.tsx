"use client";

import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import Link from "next/link";
import { Search, Star, Trash2, FolderOpen, ChevronRight, Undo2, CheckSquare, Square, X, Copy, Loader2, Download } from "lucide-react";
import { materialsApi, downloadMaterial, MaterialOut, MaterialType } from "@/lib/api";
import { MATERIAL_TYPE_CONFIG, LIBRARY_TYPES, MATERIAL_TYPE_LABEL_KEY } from "@/lib/material-types";
import { useT } from "@/lib/i18n";
import type { MessageKey } from "@/lib/messages";

type Item = MaterialOut & { type: MaterialType };
type Tab = "all" | MaterialType;

/* Mirrors [type]/[id]/page.tsx's own maps — the list row only has the
 * summary MaterialOut, not the parsed content, so downloading from here
 * fetches the full item on click rather than guessing from list data. */
const CONTENT_FIELD: Record<MaterialType, "content" | "slides_json" | "questions_json" | "tasks_json" | "game_json"> = {
  konspekt: "content",
  lektsiya: "content",
  prezentatsiya: "slides_json",
  test: "questions_json",
  amaliy: "tasks_json",
  igra: "game_json",
};

/* The viewer page offers a choice of formats; the list row has room for one
 * icon, so this is each type's first (most useful) format from that list.
 * "igra" never reaches this page (LIBRARY_TYPES excludes it) — the entry
 * exists only so indexing by the broader MaterialType type-checks. */
const DOWNLOAD_FORMAT: Record<MaterialType, "docx" | "pptx"> = {
  konspekt: "docx",
  lektsiya: "docx",
  test: "docx",
  prezentatsiya: "pptx",
  amaliy: "docx",
  igra: "docx",
};

const CURRICULUM_STATUS_KEY: Record<string, MessageKey> = {
  draft: "materials.statusDraft",
  generating: "materials.statusGenerating",
  ready: "materials.statusReady",
  partial_failed: "materials.statusPartialFailed",
};

const FILTER_SELECT =
  "rounded-lg border border-border bg-white px-2.5 py-1.5 text-xs font-medium text-text-secondary shadow-[inset_0_1px_2px_rgba(0,0,0,0.03)] outline-none focus:border-primary";

export default function MaterialsPage() {
  const t = useT();
  const [tab, setTab] = useState<Tab>("all");
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  
  
  
  
  const [subjectFilter, setSubjectFilter] = useState("all");
  const [gradeFilter, setGradeFilter] = useState("all");

  
  
  
  
  
  
  const [pendingItems, setPendingItems] = useState<Item[]>([]);
  const pendingRef = useRef<Item[]>([]);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hiddenIds = useMemo(() => new Set(pendingItems.map((i) => `${i.type}:${i.id}`)), [pendingItems]);

  
  
  
  const [selectMode, setSelectMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  function toggleSelected(item: Item) {
    const key = `${item.type}:${item.id}`;
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function exitSelectMode() {
    setSelectMode(false);
    setSelectedIds(new Set());
  }

  
  
  
  useEffect(() => {
    exitSelectMode();
    
  }, [tab]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const types = tab === "all" ? LIBRARY_TYPES : [tab];
      const results = await Promise.all(
        types.map(async (t) => {
          const list = await materialsApi.list(t, { q: query || undefined });
          return list.map((m) => ({ ...m, type: t }));
        })
      );
      const merged = results.flat().sort((a, b) => {
        if (a.is_favorite !== b.is_favorite) return a.is_favorite ? -1 : 1;
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      });
      setItems(merged);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [tab, query]);

  useEffect(() => {
    const t = setTimeout(load, 250); 
    return () => clearTimeout(t);
  }, [load]);

  
  
  
  useEffect(() => {
    if (subjectFilter !== "all" && !items.some((i) => i.subject === subjectFilter)) {
      setSubjectFilter("all");
    }
    if (gradeFilter !== "all" && !items.some((i) => i.grade === gradeFilter)) {
      setGradeFilter("all");
    }
    
  }, [items]);

  async function toggleFavorite(item: Item) {
    setItems((prev) => prev.map((i) => (i.id === item.id ? { ...i, is_favorite: !i.is_favorite } : i)));
    await materialsApi.update(item.type, item.id, { is_favorite: !item.is_favorite }).catch(() => load());
  }

  
  
  
  
  
  
  const [duplicatingKey, setDuplicatingKey] = useState<string | null>(null);
  async function duplicate(item: Item) {
    const key = `${item.type}:${item.id}`;
    setDuplicatingKey(key);
    try {
      const copy = await materialsApi.duplicate(item.type, item.id);
      setItems((prev) => [{ ...copy, type: item.type }, ...prev]);
    } catch {

    } finally {
      setDuplicatingKey(null);
    }
  }

  const [downloadingKey, setDownloadingKey] = useState<string | null>(null);
  async function download(item: Item) {
    const key = `${item.type}:${item.id}`;
    setDownloadingKey(key);
    try {
      const full = await materialsApi.get(item.type, item.id);
      const raw = full[CONTENT_FIELD[item.type]];
      if (!raw) return;
      const content = JSON.parse(raw);
      const language = typeof content.language === "string" ? content.language : "Русский";
      await downloadMaterial(DOWNLOAD_FORMAT[item.type], { material_type: item.type, content, language });
    } catch {

    } finally {
      setDownloadingKey(null);
    }
  }

  function commitDeletes(toDelete: Item[]) {
    return Promise.all(toDelete.map((i) => materialsApi.remove(i.type, i.id).catch(() => {})));
  }

  function scheduleDelete(newOnes: Item[]) {
    const merged = [...pendingRef.current];
    for (const i of newOnes) {
      if (!merged.some((m) => m.id === i.id && m.type === i.type)) merged.push(i);
    }
    pendingRef.current = merged;
    setPendingItems(merged);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      const toDelete = pendingRef.current;
      commitDeletes(toDelete).catch(() => {});
      setItems((prev) => prev.filter((i) => !toDelete.some((d) => d.id === i.id && d.type === i.type)));
      pendingRef.current = [];
      setPendingItems([]);
      timerRef.current = null;
    }, 5000);
  }

  function undoDelete() {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    pendingRef.current = [];
    setPendingItems([]);
  }

  
  
  
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        if (pendingRef.current.length) commitDeletes(pendingRef.current);
      }
    };
  }, []);

  function remove(item: Item) {
    scheduleDelete([item]);
  }

  function bulkDelete() {
    const toDelete = filteredItems.filter((i) => selectedIds.has(`${i.type}:${i.id}`));
    scheduleDelete(toDelete);
    exitSelectMode();
  }

  const subjectOptions = useMemo(
    () => Array.from(new Set(items.map((i) => i.subject))).sort(),
    [items]
  );
  const gradeOptions = useMemo(
    () => Array.from(new Set(items.map((i) => i.grade))).sort(),
    [items]
  );

  const filteredItems = items.filter(
    (i) =>
      !hiddenIds.has(`${i.type}:${i.id}`) &&
      (subjectFilter === "all" || i.subject === subjectFilter) &&
      (gradeFilter === "all" || i.grade === gradeFilter)
  );

  const isEmpty = filteredItems.length === 0;

  return (
    <div className="mx-auto max-w-3xl px-4 pt-8 sm:px-6 lg:max-w-5xl lg:px-8">
      <div className="mb-1 flex items-start justify-between gap-3">
        <h1 className="text-2xl font-bold text-text-primary">{t("materials.title")}</h1>
        {!isEmpty && filteredItems.length > 0 && (
          <button
            onClick={() => (selectMode ? exitSelectMode() : setSelectMode(true))}
            className="shrink-0 rounded-lg px-2.5 py-1 text-sm font-medium text-primary hover:bg-primary-50"
          >
            {selectMode ? t("materials.cancel") : t("materials.select")}
          </button>
        )}
      </div>
      <p className="mb-5 text-sm text-text-secondary">{t("materials.subtitle")}</p>

      <div className="relative mb-4">
        <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-text-tertiary" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t("materials.search")}
          className="w-full rounded-xl border border-border bg-white py-2.5 pl-10 pr-4 text-sm text-text-primary shadow-[inset_0_2px_3px_rgba(0,0,0,0.04)] outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/10"
        />
      </div>

      <div className="mb-3 flex gap-2 overflow-x-auto pb-1">
        <TabChip active={tab === "all"} onClick={() => setTab("all")}>
          {t("materials.all")}
        </TabChip>
        {}
        {LIBRARY_TYPES.map((type) => (
          <TabChip key={type} active={tab === type} onClick={() => setTab(type)}>
            {t(MATERIAL_TYPE_LABEL_KEY[type])}
          </TabChip>
        ))}
      </div>

      {(subjectOptions.length > 1 || gradeOptions.length > 1) && (
        <div className="mb-5 flex gap-2">
          {subjectOptions.length > 1 && (
            <select value={subjectFilter} onChange={(e) => setSubjectFilter(e.target.value)} className={FILTER_SELECT}>
              <option value="all">{t("materials.allSubjects")}</option>
              {subjectOptions.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          )}
          {gradeOptions.length > 1 && (
            <select value={gradeFilter} onChange={(e) => setGradeFilter(e.target.value)} className={FILTER_SELECT}>
              <option value="all">{t("materials.allGrades")}</option>
              {gradeOptions.map((g) => (
                <option key={g} value={g}>
                  {g}
                </option>
              ))}
            </select>
          )}
        </div>
      )}

      {loading ? (
        <p className="py-10 text-center text-sm text-text-secondary">{t("common.loading")}</p>
      ) : isEmpty ? (
        <p className="py-10 text-center text-sm text-text-secondary">
          {query || subjectFilter !== "all" || gradeFilter !== "all" ? t("materials.nothingFound") : t("materials.empty")}
        </p>
      ) : (
        <div className="space-y-2">
          {filteredItems.map((item) => {
            const config = MATERIAL_TYPE_CONFIG[item.type];
            const Icon = config.icon;
            const key = `${item.type}:${item.id}`;
            const selected = selectedIds.has(key);
            const body = (
              <>
                <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${config.bg} shadow-[inset_0_-2px_3px_rgba(0,0,0,0.08),inset_0_1px_1px_rgba(255,255,255,0.8)]`}>
                  <Icon className={`h-5 w-5 ${config.color}`} />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-text-primary">{item.title}</p>
                  <p className="truncate text-xs text-text-secondary">
                    {t(MATERIAL_TYPE_LABEL_KEY[item.type])} • {item.subject} • {item.grade}
                  </p>
                </div>
              </>
            );
            return (
              <div
                key={key}
                className={`flex items-center gap-3 rounded-2xl border p-3.5 transition-all duration-150 ${
                  selectMode && selected
                    ? "border-primary bg-primary-50"
                    : "border-border-light bg-white shadow-[0_2px_0_0_var(--color-border-light)] hover:-translate-y-0.5 hover:border-primary/20 hover:shadow-[0_3px_0_0_var(--color-primary-50),0_10px_20px_-10px_rgba(220,38,38,0.15)]"
                }`}
              >
                {selectMode ? (
                  <button onClick={() => toggleSelected(item)} className="flex flex-1 items-center gap-3 min-w-0 text-left">
                    {selected ? (
                      <CheckSquare className="h-5 w-5 shrink-0 text-primary" />
                    ) : (
                      <Square className="h-5 w-5 shrink-0 text-text-tertiary" />
                    )}
                    {body}
                  </button>
                ) : (
                  <>
                    <Link href={`/dashboard/materials/${item.type}/${item.id}`} className="flex flex-1 items-center gap-3 min-w-0">
                      {body}
                    </Link>
                    <button onClick={() => toggleFavorite(item)} className="shrink-0 p-1.5">
                      <Star
                        className={`h-4 w-4 ${item.is_favorite ? "fill-primary text-primary" : "text-text-tertiary"}`}
                      />
                    </button>
                    {item.type === "prezentatsiya" && (
                      <button
                        onClick={() => duplicate(item)}
                        disabled={duplicatingKey === key}
                        title="Дублировать"
                        className="shrink-0 p-1.5 text-text-tertiary hover:text-primary disabled:opacity-50"
                      >
                        {duplicatingKey === key ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Copy className="h-4 w-4" />
                        )}
                      </button>
                    )}
                    <button onClick={() => remove(item)} className="shrink-0 p-1.5 text-text-tertiary hover:text-primary">
                      <Trash2 className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => download(item)}
                      disabled={downloadingKey === key}
                      title={t("materials.download")}
                      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-b from-primary-light to-primary text-white shadow-[0_2px_0_0_var(--color-primary-dark)] transition-all duration-150 hover:-translate-y-0.5 hover:shadow-[0_3px_0_0_var(--color-primary-dark)] active:translate-y-px active:shadow-[0_1px_0_0_var(--color-primary-dark)] disabled:pointer-events-none disabled:opacity-60"
                    >
                      {downloadingKey === key ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Download className="h-4 w-4" />
                      )}
                    </button>
                  </>
                )}
              </div>
            );
          })}
        </div>
      )}

      {selectMode && selectedIds.size > 0 && (
        <div className="fixed inset-x-0 bottom-24 z-30 flex justify-center px-4">
          <div className="flex items-center gap-3 rounded-xl bg-text-primary px-4 py-3 text-sm text-white shadow-lg">
            <span>{t("materials.selected")}: {selectedIds.size}</span>
            <button onClick={bulkDelete} className="flex shrink-0 items-center gap-1 font-semibold text-primary-light hover:underline">
              <Trash2 className="h-3.5 w-3.5" />
              {t("materials.delete")}
            </button>
            <button onClick={exitSelectMode} className="shrink-0 text-white/70 hover:text-white">
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {pendingItems.length > 0 && (
        <div className="fixed inset-x-0 bottom-24 z-30 flex justify-center px-4">
          <div className="flex items-center gap-3 rounded-xl bg-text-primary px-4 py-3 text-sm text-white shadow-lg">
            <span className="max-w-[55vw] truncate sm:max-w-xs">
              {pendingItems.length === 1 ? `«${pendingItems[0].title}» ${t("materials.deleted")}` : `${t("materials.deletedCount")}: ${pendingItems.length}`}
            </span>
            <button onClick={undoDelete} className="flex shrink-0 items-center gap-1 font-semibold text-primary-light hover:underline">
              <Undo2 className="h-3.5 w-3.5" />
              {t("materials.undo")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function TabChip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`shrink-0 rounded-full px-4 py-1.5 text-sm font-medium transition-all duration-150 ${
        active
          ? "bg-gradient-to-b from-primary-light to-primary text-white shadow-[0_3px_0_0_var(--color-primary-dark)]"
          : "border border-border-light bg-white text-text-secondary hover:border-primary/25 hover:text-text-primary"
      }`}
    >
      {children}
    </button>
  );
}

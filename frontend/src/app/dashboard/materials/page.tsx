"use client";

import { Suspense, useEffect, useState, useCallback, useMemo, useRef } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Grid2X2, List, Plus, Search, Trash2, Undo2, X } from "lucide-react";
import { materialsApi, MaterialOut, MaterialType } from "@/lib/api";
import { LIBRARY_TYPES, MATERIAL_TYPE_LABEL_KEY } from "@/lib/material-types";
import { useT } from "@/lib/i18n";
import { CREATE_HREF } from "@/lib/dashboard-nav";
import MaterialLibraryView from "@/components/dashboard/MaterialLibraryView";

type Item = MaterialOut & { type: MaterialType };
type Tab = "all" | MaterialType;

const FILTER_SELECT =
  "h-11 rounded-xl border border-border bg-surface px-3 text-sm font-medium text-text-secondary outline-none focus:border-primary";

export default function MaterialsPage() {
  return <Suspense fallback={null}><MaterialsRoute /></Suspense>;
}

function MaterialsRoute() {
  const params = useSearchParams();
  const requested = params.get("type");
  const initialTab: Tab = (requested && (LIBRARY_TYPES as string[]).includes(requested)) || requested === "igra"
    ? requested as MaterialType : "all";
  return <MaterialsView key={initialTab} initialTab={initialTab} />;
}

function MaterialsView({ initialTab }: { initialTab: Tab }) {
  const t = useT();
  const [tab, setTab] = useState<Tab>(initialTab);
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [view, setView] = useState<"grid" | "list">("grid");
  
  
  
  
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

  
  
  
  function changeTab(next: Tab) {
    exitSelectMode();
    setSubjectFilter("all");
    setGradeFilter("all");
    setTab(next);
  }

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const types: MaterialType[] = tab === "all" ? [...LIBRARY_TYPES, "igra"] : [tab];
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
      setLoadError(false);
    } catch {
      setItems([]);
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  }, [tab, query]);

  useEffect(() => {
    const t = setTimeout(load, 250); 
    return () => clearTimeout(t);
  }, [load]);

  
  
  
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
  const activeSubjectFilter = subjectOptions.includes(subjectFilter) ? subjectFilter : "all";
  const activeGradeFilter = gradeOptions.includes(gradeFilter) ? gradeFilter : "all";

  const filteredItems = items.filter(
    (i) =>
      !hiddenIds.has(`${i.type}:${i.id}`) &&
      (activeSubjectFilter === "all" || i.subject === activeSubjectFilter) &&
      (activeGradeFilter === "all" || i.grade === activeGradeFilter)
  );

  const isEmpty = filteredItems.length === 0;
  const filtering = Boolean(query) || activeSubjectFilter !== "all" || activeGradeFilter !== "all";

  return (
    <div className="mx-auto w-full max-w-[1600px] px-4 pb-16 pt-6 sm:px-7 lg:px-10 lg:pt-9">
      <div className="mb-7">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary-accent">Dastyor / {t("materials.title")}</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-text-primary sm:text-4xl">{t("materials.title")}</h1>
        <p className="mt-1 text-sm text-text-secondary sm:text-base">{t("materials.subtitle")}</p>
      </div>

      <div className="mb-6 flex flex-col gap-3 rounded-[1.25rem] border border-border-light bg-surface/90 p-3 shadow-card sm:p-4 xl:flex-row xl:items-center">
        <div className="flex flex-1 flex-wrap items-center gap-2">
          <div className="flex shrink-0 rounded-xl bg-surface-muted p-1" role="group" aria-label={t("materials.title")}>
            <button type="button" onClick={() => setView("grid")} aria-label={t("materials.grid")} aria-pressed={view === "grid"}
              className={`flex h-9 w-9 items-center justify-center rounded-lg ${view === "grid" ? "bg-surface text-primary-accent shadow-sm" : "text-text-tertiary hover:text-text-primary"}`}><Grid2X2 className="h-4.5 w-4.5" /></button>
            <button type="button" onClick={() => setView("list")} aria-label={t("materials.list")} aria-pressed={view === "list"}
              className={`flex h-9 w-9 items-center justify-center rounded-lg ${view === "list" ? "bg-surface text-primary-accent shadow-sm" : "text-text-tertiary hover:text-text-primary"}`}><List className="h-4.5 w-4.5" /></button>
          </div>
          <label className="relative min-w-[150px] flex-1 sm:max-w-xs">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-tertiary" />
            <span className="sr-only">{t("materials.search")}</span>
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t("materials.search")}
              className="h-11 w-full rounded-xl border border-border bg-surface py-2 pl-9 pr-3 text-sm text-text-primary outline-none focus:border-primary" />
          </label>
          <select value={tab} onChange={(e) => changeTab(e.target.value as Tab)} aria-label={t("home.pickType")} className={`${FILTER_SELECT} min-w-32 flex-1 sm:max-w-48`}>
            <option value="all">{t("materials.all")}</option>
            {([...LIBRARY_TYPES, "igra"] as MaterialType[]).map((type) => <option key={type} value={type}>{t(MATERIAL_TYPE_LABEL_KEY[type])}</option>)}
          </select>
        </div>
        <div className="flex items-center gap-2">
          {!isEmpty && <button type="button" onClick={() => (selectMode ? exitSelectMode() : setSelectMode(true))}
            className="h-11 rounded-xl border border-border px-3 text-sm font-medium text-text-secondary hover:bg-surface-muted">{selectMode ? t("materials.cancel") : t("materials.select")}</button>}
          <Link href={CREATE_HREF} className="inline-flex h-11 flex-1 items-center justify-center gap-2 rounded-xl bg-primary px-4 text-sm font-semibold text-white shadow-sm hover:bg-primary-dark xl:flex-none">
            <Plus className="h-4 w-4" />{t("materials.new")}
          </Link>
        </div>
      </div>

      {(subjectOptions.length > 1 || gradeOptions.length > 1) && <div className="mb-6 flex flex-wrap gap-2">
        {subjectOptions.length > 1 && <select value={activeSubjectFilter} onChange={(e) => setSubjectFilter(e.target.value)} aria-label={t("materials.allSubjects")} className={FILTER_SELECT}>
          <option value="all">{t("materials.allSubjects")}</option>
          {subjectOptions.map((subject) => <option key={subject} value={subject}>{subject}</option>)}
        </select>}
        {gradeOptions.length > 1 && <select value={activeGradeFilter} onChange={(e) => setGradeFilter(e.target.value)} aria-label={t("materials.allGrades")} className={FILTER_SELECT}>
          <option value="all">{t("materials.allGrades")}</option>
          {gradeOptions.map((grade) => <option key={grade} value={grade}>{grade}</option>)}
        </select>}
      </div>}

      <MaterialLibraryView
        items={filteredItems} loading={loading} error={loadError} filtering={filtering}
        view={view} tab={tab} selectMode={selectMode} selectedIds={selectedIds}
        duplicatingKey={duplicatingKey} onRetry={load} onToggleSelected={toggleSelected}
        onFavorite={toggleFavorite} onDuplicate={duplicate} onRemove={remove}
      />
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

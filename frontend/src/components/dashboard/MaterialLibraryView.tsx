"use client";

import Link from "next/link";
import Image from "next/image";
import { ArrowUpRight, CheckSquare, Copy, FilePlus2, Loader2, Square, Star, Trash2 } from "lucide-react";
import Mascot from "@/components/Mascot";
import { CREATE_HREF } from "@/lib/dashboard-nav";
import { MATERIAL_TYPE_CONFIG, MATERIAL_TYPE_LABEL_KEY } from "@/lib/material-types";
import type { MaterialOut, MaterialType } from "@/lib/api";
import { useT } from "@/lib/i18n";

type Item = MaterialOut & { type: MaterialType };

const MATERIAL_ART: Record<string, string> = {
  konspekt: "/soft3d/book.webp",
  lektsiya: "/soft3d/notebook.webp",
  test: "/soft3d/quiz.webp",
  prezentatsiya: "/soft3d/presentation.webp",
  amaliy: "/soft3d/notebook.webp",
  igra: "/soft3d/quiz.webp",
};

export default function MaterialLibraryView({ items, loading, error, filtering, view, tab, selectMode, selectedIds, duplicatingKey, onRetry, onToggleSelected, onFavorite, onDuplicate, onRemove }: {
  items: Item[];
  loading: boolean;
  error: boolean;
  filtering: boolean;
  view: "grid" | "list";
  tab: "all" | MaterialType;
  selectMode: boolean;
  selectedIds: Set<string>;
  duplicatingKey: string | null;
  onRetry: () => void;
  onToggleSelected: (item: Item) => void;
  onFavorite: (item: Item) => void;
  onDuplicate: (item: Item) => void;
  onRemove: (item: Item) => void;
}) {
  const t = useT();
  if (loading) return <p className="py-12 text-center text-sm text-text-secondary">{t("common.loading")}</p>;
  if (error) return <div className="rounded-2xl border border-border bg-surface p-8 text-center">
    <p className="text-sm text-text-secondary">{t("materials.loadFailed")}</p>
    <button type="button" onClick={onRetry} className="mt-3 text-sm font-semibold text-primary-accent">{t("home.retry")}</button>
  </div>;

  return <>
    {items.length === 0 && <div className="mb-5 flex flex-col items-center rounded-2xl border border-dashed border-border bg-surface px-5 py-9 text-center">
      {!filtering && <Mascot mood="idle" size={64} />}
      <p className="mt-2 text-sm text-text-secondary">{filtering ? t("materials.nothingFound") : t("materials.empty")}</p>
    </div>}
    <div className={view === "grid" ? "grid gap-4 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4" : "space-y-2"}>
      {items.map((item) => {
        const config = MATERIAL_TYPE_CONFIG[item.type];
        const Icon = config.icon;
        const key = `${item.type}:${item.id}`;
        const selected = selectedIds.has(key);
        const href = `/dashboard/materials/${item.type}/${item.id}`;
        const metadata = <span className="block truncate text-xs text-text-secondary">{t(MATERIAL_TYPE_LABEL_KEY[item.type])} · {item.subject} · {item.grade}</span>;
        const actions = <div className="flex shrink-0 items-center gap-0.5">
          <button type="button" onClick={() => onFavorite(item)} aria-label={t("materials.favorite")} title={t("materials.favorite")}
            className="rounded-lg p-2 text-text-tertiary hover:bg-primary-50 hover:text-primary-accent">
            <Star className={`h-4 w-4 ${item.is_favorite ? "fill-primary text-primary" : ""}`} />
          </button>
          {item.type === "prezentatsiya" && <button type="button" onClick={() => onDuplicate(item)} disabled={duplicatingKey === key}
            aria-label={t("materials.duplicate")} title={t("materials.duplicate")}
            className="rounded-lg p-2 text-text-tertiary hover:bg-primary-50 hover:text-primary-accent disabled:opacity-50">
            {duplicatingKey === key ? <Loader2 className="h-4 w-4 animate-spin" /> : <Copy className="h-4 w-4" />}
          </button>}
          <button type="button" onClick={() => onRemove(item)} aria-label={t("materials.delete")} title={t("materials.delete")}
            className="rounded-lg p-2 text-text-tertiary hover:bg-primary-50 hover:text-primary-accent"><Trash2 className="h-4 w-4" /></button>
        </div>;

        if (view === "list") return <div key={key} className={`flex min-w-0 items-center gap-3 rounded-xl border p-3 transition-colors ${selected ? "border-primary bg-primary-50" : "border-border bg-surface hover:border-primary/30"}`}>
          {selectMode ? <button type="button" onClick={() => onToggleSelected(item)} aria-label={item.title} aria-pressed={selected} className="flex min-w-0 flex-1 items-center gap-3 text-left">
            {selected ? <CheckSquare className="h-5 w-5 shrink-0 text-primary" /> : <Square className="h-5 w-5 shrink-0 text-text-tertiary" />}
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary-50"><Icon className="h-5 w-5 text-primary-accent" /></span>
            <span className="min-w-0"><span className="block truncate text-sm font-semibold text-text-primary">{item.title}</span>{metadata}</span>
          </button> : <>
            <Link href={href} aria-label={`${t("materials.open")}: ${item.title}`} className="flex min-w-0 flex-1 items-center gap-3">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary-50"><Icon className="h-5 w-5 text-primary-accent" /></span>
              <span className="min-w-0"><span className="block truncate text-sm font-semibold text-text-primary">{item.title}</span>{metadata}</span>
            </Link>{actions}
          </>}
        </div>;

        return <article key={key} className={`group min-w-0 overflow-hidden rounded-2xl border bg-surface transition-all hover:-translate-y-0.5 hover:shadow-card-lift ${selected ? "border-primary ring-2 ring-primary/15" : "border-border hover:border-primary/30"}`}>
          {selectMode ? <button type="button" onClick={() => onToggleSelected(item)} aria-label={item.title} aria-pressed={selected} className="w-full text-left">
            <DocumentPreview type={item.type} icon={Icon} selected={selected} />
            <div className="px-4 pb-4"><p className="truncate text-sm font-semibold text-text-primary">{item.title}</p><p className="mt-1">{metadata}</p></div>
          </button> : <>
            <Link href={href} aria-label={`${t("materials.open")}: ${item.title}`} className="block">
              <DocumentPreview type={item.type} icon={Icon} />
              <div className="px-4 pt-1"><p className="truncate text-sm font-semibold text-text-primary group-hover:text-primary-accent">{item.title}</p><p className="mt-1">{metadata}</p></div>
            </Link>
            <div className="flex items-center justify-between border-t border-border-light px-3 py-1.5">
              <span className="px-1 text-xs text-text-tertiary">{new Date(item.created_at).toLocaleDateString()}</span>{actions}
            </div>
          </>}
        </article>;
      })}
      {view === "grid" && !filtering && tab !== "igra" && !selectMode && <Link href={CREATE_HREF} className="group flex min-h-64 flex-col items-center justify-center rounded-2xl border border-dashed border-primary/30 bg-primary-50/35 p-6 text-center text-primary-accent transition-colors hover:border-primary hover:bg-primary-50">
        <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-white shadow-sm"><FilePlus2 className="h-6 w-6" /></span>
        <span className="mt-4 text-sm font-semibold">{t("materials.new")}</span>
        <ArrowUpRight className="mt-2 h-4 w-4 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
      </Link>}
    </div>
  </>;
}

/* Used to be one grey document mock for every type - every card in a grid
 * read as the same card. Now it carries the type's own category colour and
 * the real soft3d object for that type, so a library of mixed materials
 * reads as mixed at a glance instead of a wall of identical tiles. */
function DocumentPreview({ type, icon: Icon, selected = false }: { type: MaterialType; icon: typeof FilePlus2; selected?: boolean }) {
  const config = MATERIAL_TYPE_CONFIG[type];
  return <div className={`relative flex h-36 items-center justify-center overflow-hidden ${config.bg}/55`}>
    <div className={`relative h-28 w-20 rounded-lg border border-white/70 bg-surface p-3 shadow-sm ${config.color}`}>
      <Icon className="h-6 w-6" strokeWidth={1.7} />
      <span className="mt-3 block h-1.5 w-full rounded-full bg-border" /><span className="mt-1.5 block h-1.5 w-4/5 rounded-full bg-border" /><span className="mt-1.5 block h-1.5 w-3/5 rounded-full bg-border" />
    </div>
    <Image src={MATERIAL_ART[type]} alt="" aria-hidden="true" width={160} height={160} sizes="80px" className="absolute -bottom-3 -right-3 h-20 w-20 object-contain opacity-80 drop-shadow-[0_8px_10px_rgba(64,44,43,0.14)]" />
    {selected && <CheckSquare className="absolute right-3 top-3 z-[1] h-5 w-5 text-primary" />}
  </div>;
}

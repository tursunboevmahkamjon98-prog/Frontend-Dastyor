"use client";

import { useEffect, useState, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { Search, Trash2, Loader2, ExternalLink } from "lucide-react";
import Link from "next/link";
import { adminApi, AdminMaterialOut, ApiError, MaterialType } from "@/lib/api";
import { MATERIAL_TYPE_CONFIG, MATERIAL_TYPES } from "@/lib/material-types";

const PAGE_SIZE = 30;

/** The nav item pointing here (admin/layout.tsx's "Материалы") has
 * existed since before this page did — adminApi.listMaterials/
 * removeMaterial and the backend endpoints behind them (see
 * routers/admin.py) were already there too, just never wired to
 * anything, so the tab silently 404'd. This is that missing page. */
export default function AdminMaterialsPage() {
  // ?user=<id> narrows the list to one teacher — set by the "materials"
  // button on an admin/users row, so an admin can go from "who is this
  // account" straight to "what have they actually made" instead of
  // hunting for their name in the all-teachers list.
  const params = useSearchParams();
  const userId = params.get("user") || "";
  const [query, setQuery] = useState("");
  const [type, setType] = useState<MaterialType | "">("");
  const [items, setItems] = useState<AdminMaterialOut[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (nextOffset: number) => {
    setLoading(true);
    try {
      const page = await adminApi.listMaterials({
        q: query || undefined,
        user_id: userId || undefined,
        type: type || undefined,
        limit: PAGE_SIZE,
        offset: nextOffset,
      });
      setItems(page.items);
      setTotal(page.total);
      setOffset(nextOffset);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось загрузить");
    } finally {
      setLoading(false);
    }
  }, [query, type, userId]);

  // Debounced like admin/users — a search/type change goes back to page 1
  // rather than keeping whatever offset was scrolled to for the OLD filter.
  useEffect(() => {
    const t = setTimeout(() => load(0), 250);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query, type, userId]);

  async function remove(item: AdminMaterialOut) {
    // Same reasoning as admin/users' remove(): irreversible, no undo
    // story here, worth a native confirm() despite the rest of the app
    // having moved to the undo-toast pattern for a teacher's OWN deletes.
    if (!confirm(`Удалить «${item.title}» (${MATERIAL_TYPE_CONFIG[item.type]?.label ?? item.type}, владелец: ${item.owner_name})? Это необратимо.`)) return;
    setBusyId(item.id);
    setError(null);
    try {
      await adminApi.removeMaterial(item.type, item.id);
      setItems((prev) => prev.filter((x) => x.id !== item.id));
      setTotal((prev) => prev - 1);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось удалить");
    } finally {
      setBusyId(null);
    }
  }

  const canPrev = offset > 0;
  const canNext = offset + PAGE_SIZE < total;

  return (
    <div>
      <h1 className="mb-1 text-2xl font-bold text-text-primary">Материалы</h1>
      {userId ? (
        <p className="mb-5 text-sm text-text-secondary">
          Материалы одного учителя
          {items[0]?.owner_name ? ` — ${items[0].owner_name}` : ""} ({total} шт.).{" "}
          <Link href="/admin/materials" className="font-medium text-primary hover:underline">
            Показать всех
          </Link>
        </p>
      ) : (
        <p className="mb-5 text-sm text-text-secondary">
          Все сгенерированные материалы, всех учителей — {total} шт.
        </p>
      )}

      <div className="mb-4 flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-text-tertiary" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Поиск по названию, предмету..."
            className="w-full rounded-xl border border-border bg-surface py-2.5 pl-10 pr-4 text-sm text-text-primary outline-none focus:border-primary"
          />
        </div>
        <select
          value={type}
          onChange={(e) => setType(e.target.value as MaterialType | "")}
          className="rounded-xl border border-border bg-surface px-3 py-2.5 text-sm text-text-primary outline-none focus:border-primary"
        >
          <option value="">Все типы</option>
          {MATERIAL_TYPES.map((t) => (
            <option key={t} value={t}>{MATERIAL_TYPE_CONFIG[t].label}</option>
          ))}
        </select>
      </div>

      {error && <p className="mb-4 rounded-xl bg-primary-50 px-4 py-2.5 text-sm text-primary-dark">{error}</p>}

      {loading ? (
        <p className="py-10 text-center text-sm text-text-secondary">Загрузка...</p>
      ) : items.length === 0 ? (
        <p className="py-10 text-center text-sm text-text-secondary">Ничего не найдено</p>
      ) : (
        <div className="overflow-hidden rounded-2xl border border-border-light bg-surface">
          <div className="divide-y divide-border-light">
            {items.map((item) => {
              const cfg = MATERIAL_TYPE_CONFIG[item.type];
              const Icon = cfg?.icon;
              return (
                <div key={`${item.type}-${item.id}`} className="flex items-center gap-3 p-4">
                  <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${cfg?.bg ?? "bg-surface-muted"}`}>
                    {Icon && <Icon className={`h-4.5 w-4.5 ${cfg?.color ?? "text-text-secondary"}`} />}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium text-text-primary">{item.title || "Без названия"}</p>
                    <p className="truncate text-xs text-text-secondary">
                      {cfg?.label ?? item.type} • {item.subject} • {item.grade}
                    </p>
                    <p className="mt-0.5 truncate text-xs text-text-tertiary">
                      {item.owner_name} {item.owner_phone ? `(${item.owner_phone})` : ""} •{" "}
                      {new Date(item.created_at).toLocaleDateString("ru-RU")}
                    </p>
                  </div>

                  {/* "igra" has no standalone viewer page (see
                      MATERIAL_TYPE_LABEL_KEY's own docs on why it's
                      excluded from LIBRARY_TYPES) — no link for it. */}
                  {item.type !== "igra" && (
                    <Link
                      href={`/dashboard/materials/${item.type}/${item.id}`}
                      target="_blank"
                      title="Открыть материал"
                      className="flex shrink-0 items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-xs font-medium text-text-secondary hover:bg-surface-muted"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                    </Link>
                  )}

                  <button
                    onClick={() => remove(item)}
                    disabled={busyId === item.id}
                    title="Удалить материал"
                    className="shrink-0 rounded-lg p-1.5 text-text-tertiary hover:text-primary disabled:opacity-40"
                  >
                    {busyId === item.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {!loading && total > PAGE_SIZE && (
        <div className="mt-4 flex items-center justify-between text-sm">
          <button
            onClick={() => load(offset - PAGE_SIZE)}
            disabled={!canPrev}
            className="rounded-lg border border-border px-3 py-1.5 font-medium text-text-secondary disabled:opacity-40"
          >
            Назад
          </button>
          <span className="text-text-tertiary">
            {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} из {total}
          </span>
          <button
            onClick={() => load(offset + PAGE_SIZE)}
            disabled={!canNext}
            className="rounded-lg border border-border px-3 py-1.5 font-medium text-text-secondary disabled:opacity-40"
          >
            Далее
          </button>
        </div>
      )}
    </div>
  );
}

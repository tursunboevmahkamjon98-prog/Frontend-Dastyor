"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Search, X } from "lucide-react";
import { materialsApi, type SearchResultItem } from "@/lib/api";
import { MATERIAL_TYPE_CONFIG, MATERIAL_TYPE_LABEL_KEY } from "@/lib/material-types";
import { useT } from "@/lib/i18n";

/* Search across the teacher's own materials, from anywhere in the
 * dashboard. It calls the same /materials/search the home page already
 * used to fill its "recent" list, so this adds a way in, not an endpoint.
 *
 * Every request is cancelled when the query moves on: without that, a slow
 * response for "фо" can land after a fast one for "фотосинтез" and
 * overwrite it with results for a prefix the teacher has stopped typing.
 */

const DEBOUNCE_MS = 220;
const MAX_RESULTS = 6;

export default function GlobalSearch({ className = "" }: { className?: string }) {
  const t = useT();
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResultItem[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  /* Nothing here writes state synchronously: clearing on an empty box is
   * done by the handler that empties it, and `busy` is raised once the
   * debounce actually fires. A setState in the effect body would re-render
   * on every keystroke before the request is even scheduled. */
  useEffect(() => {
    const q = query.trim();
    if (!q) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      setBusy(true);
      materialsApi
        .search(q)
        .then((items) => {
          if (controller.signal.aborted) return;
          setResults(items.slice(0, MAX_RESULTS));
        })
        .catch(() => {
          if (!controller.signal.aborted) setResults([]);
        })
        .finally(() => {
          if (!controller.signal.aborted) setBusy(false);
        });
    }, DEBOUNCE_MS);
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [query]);

  /* Close on an outside click or Escape. Both, because the popover can be
   * dismissed by moving the mouse away or by never leaving the keyboard. */
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  function clear() {
    setResults(null);
    setBusy(false);
  }

  function go(item: SearchResultItem) {
    setOpen(false);
    setQuery("");
    clear();
    router.push(`/dashboard/materials/${item.type}/${item.id}`);
  }

  const showPopover = open && query.trim().length > 0;

  return (
    <div ref={boxRef} className={`relative ${className}`}>
      <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-tertiary" />
      <input
        /* Deliberately not type="search": WebKit draws its own clear
         * button inside that control, which lands on top of the one here
         * and shows the teacher two X icons side by side. */
        type="text"
        inputMode="search"
        value={query}
        onChange={(e) => {
          const next = e.target.value;
          setQuery(next);
          setOpen(true);
          if (!next.trim()) clear();
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && results?.length) go(results[0]);
        }}
        placeholder={t("nav.searchPlaceholder")}
        aria-label={t("nav.searchPlaceholder")}
        className="w-full rounded-control border border-border bg-surface-muted py-2 pl-9 pr-9 text-meta text-text-primary outline-none transition-colors duration-150 placeholder:text-text-tertiary focus:border-primary focus:bg-surface focus:ring-2 focus:ring-primary/20"
      />
      {query && (
        <button
          type="button"
          onClick={() => {
            setQuery("");
            setOpen(false);
            clear();
          }}
          aria-label={t("nav.closeMenu")}
          className="absolute right-2 top-1/2 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-full text-text-tertiary transition-colors duration-150 hover:bg-surface-muted hover:text-text-primary"
        >
          {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <X className="h-3.5 w-3.5" />}
        </button>
      )}

      {showPopover && (
        <div className="absolute left-0 right-0 top-full z-40 mt-2 overflow-hidden rounded-card border border-border-light bg-surface shadow-float">
          {results === null ? (
            <p className="px-4 py-3 text-meta text-text-tertiary">{t("common.loading")}</p>
          ) : results.length === 0 ? (
            <p className="px-4 py-3 text-meta text-text-tertiary">{t("nav.searchEmpty")}</p>
          ) : (
            <ul className="divide-y divide-border-light">
              {results.map((item) => {
                const Icon = MATERIAL_TYPE_CONFIG[item.type].icon;
                return (
                  <li key={`${item.type}-${item.id}`}>
                    <button
                      type="button"
                      onClick={() => go(item)}
                      className="flex w-full items-center gap-3 px-3 py-2.5 text-left transition-colors duration-150 hover:bg-surface-muted"
                    >
                      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-control bg-primary-50 text-primary-accent">
                        <Icon className="h-3.5 w-3.5" strokeWidth={2} />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-meta font-medium text-text-primary">{item.title}</span>
                        <span className="block truncate text-micro text-text-tertiary">
                          {t(MATERIAL_TYPE_LABEL_KEY[item.type])} · {item.subject}
                        </span>
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

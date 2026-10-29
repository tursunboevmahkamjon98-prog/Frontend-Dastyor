"use client";

import Link from "next/link";
import dynamic from "next/dynamic";
import { Sparkles } from "lucide-react";
import { useT } from "@/lib/i18n";
import LocaleSwitcher from "./LocaleSwitcher";

/* Same 3D card stack as the landing hero (components/landing/MaterialCards3D),
 * not a per-page illustration — one shared 3D motif across the site reads as
 * a deliberate brand language instead of a one-off decoration. Client-only:
 * WebGL has no server-side representation. */
const MaterialCards3D = dynamic(() => import("@/components/landing/MaterialCards3D"), {
  ssr: false,
  loading: () => <div className="h-full w-full animate-pulse rounded-full bg-primary/5" />,
});

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  const t = useT();
  return (
    <main className="flex min-h-screen bg-background">
      {}
      <div className="relative hidden w-[46%] shrink-0 overflow-hidden bg-surface-muted lg:flex lg:flex-col lg:justify-between lg:p-12">
        <div
          className="pointer-events-none absolute -left-24 -top-24 h-96 w-96 rounded-full bg-primary/10 blur-3xl"
          style={{ animation: "landing-blob-drift 18s ease-in-out infinite" }}
          aria-hidden
        />
        <div
          className="pointer-events-none absolute -bottom-32 -right-16 h-96 w-96 rounded-full bg-primary/10 blur-3xl"
          style={{ animation: "landing-blob-drift 22s ease-in-out infinite", animationDelay: "-8s" }}
          aria-hidden
        />

        <Link href="/" className="relative z-10 flex items-center gap-2.5">
          {}
          <img src="/brand/dastyor-mark.webp" alt="Dastyor" className="h-9 w-auto" />
          <span className="text-lg font-bold text-text-primary">Dastyor</span>
        </Link>

        <div className="relative z-10 flex flex-1 items-center justify-center py-8">
          <div className="relative w-full max-w-md">
            <div
              className="absolute inset-x-6 bottom-2 top-6 -z-10 rounded-[3rem] bg-gradient-to-b from-primary/15 via-primary/10 to-transparent shadow-[inset_0_8px_24px_rgba(220,38,38,0.08)]"
              aria-hidden
            />
            <div className="h-72 w-full">
              <MaterialCards3D className="h-full w-full" />
            </div>
            <div
              className="absolute -left-6 top-6 flex items-center gap-1.5 rounded-full border border-border-light bg-white px-3 py-1.5 text-xs font-semibold text-primary shadow-[0_3px_0_0_var(--color-border-light),0_10px_20px_-6px_rgba(220,38,38,0.25)]"
              style={{ ["--chip-rot" as string]: "-3deg", animation: "landing-float-chip 5s ease-in-out infinite" }}
            >
              <Sparkles className="h-3.5 w-3.5" />
              {t("auth.chipAssistant")}
            </div>
            <div
              className="absolute -right-4 bottom-8 rounded-2xl border border-border-light bg-white px-3.5 py-2 text-xs font-semibold text-text-primary shadow-[0_3px_0_0_var(--color-border-light),0_10px_20px_-6px_rgba(0,0,0,0.12)]"
              style={{ ["--chip-rot" as string]: "2deg", animation: "landing-float-chip 5.5s ease-in-out infinite", animationDelay: "-2s" }}
            >
              {t("auth.chipTypes")}
            </div>
          </div>
        </div>

        <div className="relative z-10">
          <div className="mb-3 inline-flex items-center gap-1.5 rounded-full bg-primary-50 px-3.5 py-1.5 text-xs font-semibold text-primary-dark">
            <Sparkles className="h-3.5 w-3.5" />
            {t("auth.badge")}
          </div>
          <h2 className="mb-1 max-w-sm text-2xl font-extrabold leading-tight text-text-primary">
            {t("auth.headline")}
          </h2>
          <p className="max-w-sm text-sm text-text-secondary">
            {t("auth.tagline")}
          </p>
        </div>
      </div>

      {}
      <div className="relative flex flex-1 flex-col items-center justify-center px-4 py-10 sm:px-6">
        <LocaleSwitcher className="absolute right-4 top-4 sm:right-6 sm:top-6" />
        {/* The left panel (and its 3D card stack) only renders at lg+ —
            below that breakpoint this is the only 3D a visitor ever sees,
            so it isn't optional decoration here, it's the whole point. */}
        <div className="mb-1 h-28 w-28 lg:hidden">
          <MaterialCards3D className="h-full w-full" />
        </div>
        <div className="w-full max-w-sm" style={{ animation: "landing-reveal 0.5s ease-out both" }}>
          {children}
        </div>
      </div>
    </main>
  );
}

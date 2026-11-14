"use client";

import Link from "next/link";
import AuthTabletPreview from "./AuthTabletPreview";
import { Sparkles } from "lucide-react";
import { useT } from "@/lib/i18n";
import LocaleSwitcher from "./LocaleSwitcher";

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
          <img src="/brand/rahnamo-mark-tight.png" alt="" className="h-10 w-auto" />
          <span className="text-lg font-bold text-text-primary">Rahnamo</span>
        </Link>

        <div className="relative z-10 flex flex-1 items-center justify-center py-8">
          <div className="relative w-full max-w-md">
            <div
              className="absolute inset-x-6 bottom-2 top-6 -z-10 rounded-[3rem] bg-gradient-to-b from-primary/15 via-primary/10 to-transparent shadow-[inset_0_8px_24px_rgba(220,38,38,0.08)]"
              aria-hidden
            />
            <AuthTabletPreview />
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
        <div className="mb-5 mt-8 w-full max-w-[240px] lg:hidden"><AuthTabletPreview /></div>
        <div className="w-full max-w-sm" style={{ animation: "landing-reveal 0.5s ease-out both" }}>
          {children}
        </div>
      </div>
    </main>
  );
}

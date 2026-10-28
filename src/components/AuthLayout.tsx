"use client";

import Link from "next/link";
import { Sparkles } from "lucide-react";
import { useT } from "@/lib/i18n";
import LocaleSwitcher from "./LocaleSwitcher";


export default function AuthLayout({
  children,
  illustration = "/auth-illustration.svg",
}: {
  children: React.ReactNode;
  illustration?: string;
}) {
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
          <img src="/logo.png" alt="Dastyor" className="h-9 w-9" />
          <span className="text-lg font-bold text-text-primary">Dastyor</span>
        </Link>

        <div className="relative z-10 flex flex-1 items-center justify-center py-8">
          <div className="relative" style={{ animation: "landing-float 7s ease-in-out infinite" }}>
            {}
            <img src={illustration} alt="" className="w-full max-w-md drop-shadow-xl" />
            <div
              className="absolute -left-6 top-6 flex items-center gap-1.5 rounded-full bg-surface/95 px-3 py-1.5 text-xs font-semibold text-primary shadow-md shadow-black/[0.06] backdrop-blur"
              style={{ ["--chip-rot" as string]: "-3deg", animation: "landing-float-chip 5s ease-in-out infinite" }}
            >
              <Sparkles className="h-3.5 w-3.5" />
              {t("auth.chipAssistant")}
            </div>
            <div
              className="absolute -right-4 bottom-8 rounded-2xl bg-surface/95 px-3.5 py-2 text-xs font-semibold text-text-primary shadow-md shadow-black/[0.06] backdrop-blur"
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
      <div className="relative flex flex-1 items-center justify-center px-4 py-10 sm:px-6">
        <LocaleSwitcher className="absolute right-4 top-4 sm:right-6 sm:top-6" />
        <div className="w-full max-w-sm" style={{ animation: "landing-reveal 0.5s ease-out both" }}>
          {children}
        </div>
      </div>
    </main>
  );
}

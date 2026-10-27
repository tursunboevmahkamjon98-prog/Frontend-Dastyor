"use client";

import Link from "next/link";
import { BookOpen, ClipboardCheck, FileText, Presentation, Sparkles } from "lucide-react";
import Logo from "./Logo";
import LocaleSwitcher from "./LocaleSwitcher";
import ThemeToggle from "./ThemeToggle";
import { useT } from "@/lib/i18n";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  const t = useT();

  return (
    <main className="auth-shell min-h-screen bg-background">
      <header className="mx-auto flex w-full max-w-7xl items-center justify-between gap-3 px-4 py-4 sm:px-6 lg:px-8">
        <Link href="/" aria-label="Dastyor">
          <Logo height="2rem" />
        </Link>
        <div className="flex items-center gap-1.5">
          <LocaleSwitcher />
          <ThemeToggle />
        </div>
      </header>

      <div className="mx-auto grid w-full max-w-7xl items-center gap-8 px-4 pb-8 pt-3 sm:px-6 lg:min-h-[calc(100vh-5rem)] lg:grid-cols-[1.05fr_0.95fr] lg:gap-12 lg:px-8 lg:pb-12">
        <aside className="auth-art auth-art-red relative hidden min-h-[39rem] overflow-hidden rounded-[2rem] p-9 text-white shadow-[0_28px_70px_rgba(170,20,36,0.22)] lg:flex lg:flex-col lg:justify-between xl:p-12">
          <span className="pointer-events-none absolute -right-20 -top-20 h-80 w-80 rounded-full border-[1.5rem] border-white/10" aria-hidden="true" />
          <span className="pointer-events-none absolute -bottom-32 -left-20 h-96 w-96 rounded-full bg-white/10 blur-2xl" aria-hidden="true" />

          <div className="relative z-10 max-w-lg">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/25 bg-white/15 px-3.5 py-2 text-meta font-semibold text-white shadow-sm backdrop-blur-sm">
              <Sparkles size={15} aria-hidden="true" />
              {t("home.aiWorkspace")}
            </div>
            <h1 className="mt-6 text-[2.7rem] font-semibold leading-[1.08] tracking-[-0.035em] text-white xl:text-[3.35rem]">
              {t("home.prompt")}
            </h1>
          </div>

          <div className="auth-art-stage relative z-10 mx-auto my-8 flex h-[19rem] w-full max-w-[27rem] items-center justify-center" aria-hidden="true">
            <div className="absolute left-[12%] top-[20%] h-52 w-64 rotate-[-12deg] rounded-[1.6rem] border border-white/70 bg-[#ffe9dd] shadow-[0_24px_45px_rgba(100,10,20,0.22)]" />
            <div className="absolute right-[7%] top-[15%] h-52 w-64 rotate-[10deg] rounded-[1.6rem] border border-white/80 bg-[#fff6eb] shadow-[0_24px_45px_rgba(100,10,20,0.2)]" />

            <div className="relative z-10 w-[17rem] -rotate-[2deg] rounded-[1.6rem] border border-white/90 bg-white p-5 text-text-primary shadow-[0_30px_60px_rgba(95,10,20,0.32)]">
              <div className="flex items-center gap-3">
                <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#fff0ec] text-primary shadow-[inset_0_2px_4px_rgba(255,255,255,0.9)]">
                  <BookOpen size={22} />
                </span>
                <span className="space-y-1.5">
                  <span className="block h-2.5 w-28 rounded-full bg-[#ddd8d6]" />
                  <span className="block h-2 w-20 rounded-full bg-[#eee9e7]" />
                </span>
              </div>
              <div className="mt-5 space-y-2.5">
                <span className="block h-2 w-full rounded-full bg-[#f0ecea]" />
                <span className="block h-2 w-[88%] rounded-full bg-[#f0ecea]" />
                <span className="block h-2 w-[72%] rounded-full bg-[#f0ecea]" />
              </div>
              <div className="mt-5 grid grid-cols-3 gap-2">
                {[FileText, ClipboardCheck, Presentation].map((Icon, i) => (
                  <span key={i} className={`flex h-14 items-center justify-center rounded-2xl ${i === 0 ? "bg-[#f1edfd] text-[#7155d9]" : i === 1 ? "bg-[#e9f7f0] text-[#187a54]" : "bg-[#e3f2ff] text-[#1f6fb0]"}`}>
                    <Icon size={21} />
                  </span>
                ))}
              </div>
            </div>

            <span className="absolute bottom-5 right-[8%] flex h-[4.5rem] w-[4.5rem] rotate-[9deg] items-center justify-center rounded-[1.35rem] border border-white/80 bg-white text-primary shadow-[0_16px_30px_rgba(95,10,20,0.25)]">
              <Sparkles size={27} />
            </span>
            <span className="absolute left-[5%] top-[43%] h-5 w-5 rounded-full border-4 border-white/60 bg-[#ffd1a8] shadow-lg" />
          </div>

          <div className="relative z-10 flex items-center justify-between border-t border-white/25 pt-5 text-meta font-medium text-white/85">
            <span>Dastyor</span>
            <span className="rounded-full bg-white/15 px-3 py-1.5">AI</span>
          </div>
        </aside>

        <section className="mx-auto w-full max-w-[29rem] py-3 sm:py-6 lg:py-10">
          {children}
        </section>
      </div>
    </main>
  );
}

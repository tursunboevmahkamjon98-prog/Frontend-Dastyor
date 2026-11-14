"use client";
import { BookOpen, Check, ChevronDown, FileText, LayoutDashboard, Plus, Presentation, Sparkles } from "lucide-react";
import { useT } from "@/lib/i18n";
import type { MessageKey } from "@/lib/messages";
export default function AuthTabletPreview() {
  const t = useT();
  const materialTypes = [
    { icon: FileText, key: "type.konspekt" },
    { icon: BookOpen, key: "type.test" },
    { icon: Presentation, key: "type.prezentatsiya" },
  ] as const satisfies ReadonlyArray<{ icon: typeof FileText; key: MessageKey }>;
  return <div aria-hidden="true" className="pointer-events-none relative mx-auto w-full max-w-[440px] select-none py-6">
    <div className="absolute inset-x-8 bottom-0 h-14 rounded-[50%] bg-rose-950/20 blur-2xl" />
    <div className="relative rotate-[-3deg] rounded-[2rem] border border-slate-500 bg-gradient-to-br from-slate-600 via-slate-900 to-black p-2.5 shadow-[6px_10px_0_#1e293b,12px_28px_45px_-12px_rgba(80,20,30,0.4)]">
      <div className="absolute left-1/2 top-1 h-1 w-1 rounded-full bg-slate-400" />
      <div className="overflow-hidden rounded-[1.4rem] bg-[#faf8f7] text-slate-800">
        <div className="flex items-center justify-between border-b border-slate-100 bg-white px-5 py-3"><span className="flex items-center gap-2 text-sm font-extrabold"><img src="/brand/rahnamo-mark-tight.png" alt="" className="h-7 w-7 rounded-lg object-contain" />Rahnamo</span><Sparkles size={15} className="text-red-500"/></div>
        <div className="flex min-h-[300px]">
          <div className="flex w-10 shrink-0 flex-col items-center gap-5 border-r border-slate-100 bg-white pt-5 text-slate-300"><LayoutDashboard size={15}/><span className="rounded-lg bg-red-50 p-2 text-red-600"><Plus size={16}/></span><BookOpen size={15}/><FileText size={15}/></div>
          <div className="min-w-0 flex-1 p-4"><div className="mb-1 text-[9px] font-bold tracking-[0.18em] text-red-500">RAHNAMO AI</div><div className="mb-4 text-base font-bold">{t("create.title")}</div>
            <div className="rounded-xl border border-slate-200/80 bg-white p-3 shadow-sm"><div className="mb-2 text-[10px] font-semibold">{t("create.topicTitle")}</div><div className="mb-3 rounded-lg border border-red-200 bg-red-50/30 px-2.5 py-2 text-[9px] leading-relaxed text-slate-500">{t("create.topicPlaceholder")}</div><div className="mb-2 flex items-center justify-between gap-2 rounded-lg border border-slate-100 p-2 text-[9px] text-slate-500">{t("create.subjectTitle")}<ChevronDown size={12}/></div>
              <div className="grid grid-cols-3 gap-1.5">{materialTypes.map(({icon: Icon, key}, i) => <div key={key} className={`min-w-0 rounded-lg border px-1 py-2 text-center ${i === 0 ? "border-red-200 bg-red-50 text-red-600" : "border-slate-100 text-slate-400"}`}><Icon size={15} className="mx-auto mb-1"/><span className="block break-words text-[8px] leading-tight">{t(key)}</span></div>)}</div>
              <div className="mt-3 flex items-center justify-center gap-1.5 rounded-lg bg-gradient-to-b from-red-500 to-red-600 px-2 py-2.5 text-[10px] font-semibold text-white shadow-[0_3px_0_#991b1b]"><Sparkles size={12}/>{t("create.sourceAi")}</div>
            </div><div className="mt-3 flex items-center gap-2 rounded-lg border border-emerald-100 bg-white p-2"><Check size={13} className="text-emerald-500"/><div className="flex-1 space-y-1"><div className="h-1 w-3/4 rounded-full bg-slate-200"/><div className="h-1 w-1/2 rounded-full bg-slate-100"/></div><FileText size={13} className="text-red-400"/></div>
          </div>
        </div>
      </div><div className="mx-auto mt-1.5 h-1 w-16 rounded-full bg-slate-600"/>
    </div>
  </div>;
}

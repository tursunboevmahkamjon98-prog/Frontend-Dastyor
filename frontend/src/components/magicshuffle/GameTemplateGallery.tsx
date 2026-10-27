"use client";

import { ArrowLeft, Check, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { BOX_THEME } from "./MagicBox";
import { magicSfx } from "./sounds";


interface GameTemplate {
  id: string;
  emoji: string;
  title: string;
  description: string;
  available: boolean;
  
  preview: React.ReactNode;
}


function MagicBoxPreview() {
  return (
    <>
      {}
      <img
        src="/game-backgrounds/classroom.png"
        alt=""
        className="absolute inset-0 h-full w-full object-cover transition-transform duration-500 group-hover:scale-110"
      />
      <div className="absolute inset-0 bg-gradient-to-b from-[#2e1065]/45 via-[#4c1d95]/35 to-[#1b0f3a]/80" />

      {}
      <span className="absolute left-4 top-4 text-lg font-black text-amber-200/80" style={{ animation: "mbox-float 3s ease-in-out infinite" }}>
        ?
      </span>
      <span
        className="absolute right-6 top-6 text-sm font-black text-fuchsia-200/70"
        style={{ animation: "mbox-float 3.4s ease-in-out 0.6s infinite" }}
      >
        ?
      </span>
      <span className="absolute right-12 top-3 text-amber-200/80" style={{ animation: "wheel-bulb-twinkle 2s ease-in-out infinite" }}>
        ✦
      </span>

      {}
      <img
        src="/game-backgrounds/jester.png"
        alt=""
        className="absolute bottom-8 left-1/2 h-28 w-auto -translate-x-1/2 drop-shadow-2xl transition-transform duration-500 group-hover:-translate-y-1"
        style={{ animation: "mascot-bob 2.8s ease-in-out infinite" }}
      />

      {}
      <div className="absolute bottom-3 left-1/2 flex -translate-x-1/2 items-end gap-3.5">
        {[0, 1, 2].map((i) => (
          <span key={i} className="relative" style={{ animation: `mbox-float 3s ease-in-out ${i * 0.3}s infinite` }}>
            <span
              className="absolute inset-0 rounded-lg blur-md"
              style={{ background: BOX_THEME.glow, opacity: 0.65 }}
              aria-hidden
            />
            <span
              className="relative flex h-9 w-9 items-center justify-center rounded-lg text-sm font-black text-white shadow-lg"
              style={{ background: BOX_THEME.body, border: `1.5px solid ${BOX_THEME.bodyShade}` }}
            >
              ?
            </span>
          </span>
        ))}
      </div>
    </>
  );
}


function SecretLabPreview() {
  return (
    <>
      <div
        className="absolute inset-0 transition-transform duration-500 group-hover:scale-105"
        style={{
          background:
            "radial-gradient(120% 80% at 50% 0%, #1e3a5f 0%, #12203c 42%, #0a1226 72%, #070c1a 100%)",
        }}
      />
      {}
      <div
        className="absolute left-1/2 top-0 h-28 w-28 -translate-x-1/2"
        style={{
          background: "linear-gradient(to bottom, rgba(186,230,253,0.5), rgba(186,230,253,0))",
          clipPath: "polygon(42% 0, 58% 0, 100% 100%, 0% 100%)",
          animation: "lab-lamp-flare 3s ease-in-out infinite",
        }}
      />
      {}
      {[15, 34, 58, 78, 90].map((left, i) => (
        <span
          key={left}
          className="absolute bottom-10 h-1 w-1 rounded-full bg-cyan-200"
          style={{ left: `${left}%`, ["--mx" as string]: `${i % 2 ? 14 : -12}px`, animation: `lab-mote ${7 + i}s linear ${i * 0.8}s infinite` }}
          aria-hidden
        />
      ))}
      {}
      <div className="absolute inset-x-0 bottom-0 h-10 bg-gradient-to-b from-slate-400 to-[#0c1526]" />
      {}
      <div className="absolute bottom-8 left-1/2 flex -translate-x-1/2 items-end gap-3">
        {["#38bdf8", "#a855f7", "#34d399", "#fb923c"].map((c, i) => (
          <span key={c} className="relative" style={{ animation: `lab-bottle-idle 3.4s ease-in-out ${i * 0.2}s infinite` }}>
            <span className="absolute -inset-1.5 rounded-xl blur-md" style={{ background: c, opacity: 0.5 }} aria-hidden />
            <span className="relative block h-9 w-6 overflow-hidden rounded-b-lg rounded-t-sm border border-white/40 bg-white/15">
              <span className="absolute inset-x-0 bottom-0 h-[60%]" style={{ background: c }} />
            </span>
          </span>
        ))}
      </div>
      {}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 translate-y-[-46px]">
        <span className="absolute -inset-3 rounded-full bg-cyan-300/40 blur-xl" aria-hidden />
        <span
          className="relative block h-10 w-12 border border-white/40 bg-white/15"
          style={{ clipPath: "polygon(38% 0, 62% 0, 100% 100%, 0% 100%)", borderRadius: "0 0 10px 10px" }}
        >
          <span className="absolute inset-x-0 bottom-0 h-[55%] bg-cyan-400/90" />
        </span>
      </div>
      <span className="absolute right-4 top-4 text-lg" style={{ animation: "mbox-float 3s ease-in-out infinite" }}>
        ⚗️
      </span>
      <span className="absolute left-4 top-6 text-base" style={{ animation: "mbox-float 3.6s ease-in-out 0.5s infinite" }}>
        🔬
      </span>
    </>
  );
}

const TEMPLATES: GameTemplate[] = [
  {
    id: "magicbox",
    emoji: "🎁",
    title: "Қуттиҳои сеҳрнок",
    description:
      "Саволро дар қуттиҳо ҷойгир кунед, қуттиҳоро омехта кунед ва қуттии дурустро интихоб кунед.",
    available: true,
    preview: <MagicBoxPreview />,
  },
  {
    id: "seclab",
    emoji: "🧪",
    title: "Лабораторияи махфӣ",
    description:
      "Ба лабораторияи махфӣ ворид шавед, ба саволҳо ҷавоб диҳед ва таҷрибаи бузургро анҷом диҳед!",
    available: true,
    preview: <SecretLabPreview />,
  },
];


export default function GameTemplateGallery({ onPick }: { onPick: (templateId: string) => void }) {
  const router = useRouter();

  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-6">
      <button
        type="button"
        onClick={() => router.push("/dashboard/create")}
        className="mb-5 flex items-center gap-2 text-sm font-semibold text-text-secondary transition hover:text-text-primary"
      >
        <ArrowLeft className="h-4 w-4" />
        Бозгашт
      </button>

      <div className="text-center">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-igra-bg px-3 py-1 text-[11px] font-black uppercase tracking-wide text-igra-icon">
          <Sparkles className="h-3.5 w-3.5" />
          Бозиҳо
        </span>
        <h1 className="mt-2 text-2xl font-extrabold text-text-primary sm:text-3xl">Шаблонҳои бозӣ</h1>
        <p className="mx-auto mt-1.5 max-w-md text-sm text-text-secondary">
          Аввал шаблони бозиро интихоб кунед, баъд танзимоти онро муайян мекунем.
        </p>
      </div>

      <div className="mt-7 grid gap-5 sm:grid-cols-2">
        {TEMPLATES.map((tpl) => (
          <button
            key={tpl.id}
            type="button"
            disabled={!tpl.available}
            onClick={() => {
              magicSfx.click();
              onPick(tpl.id);
            }}
            className="group overflow-hidden rounded-3xl border border-border bg-surface text-left shadow-lg transition hover:-translate-y-1.5 hover:border-igra-icon/40 hover:shadow-2xl active:translate-y-0 disabled:pointer-events-none disabled:opacity-60"
          >
            <div className="relative h-48 w-full overflow-hidden bg-[#1b0f3a]">{tpl.preview}</div>

            <div className="p-4">
              <h2 className="flex items-center gap-2 text-lg font-extrabold text-text-primary">
                <span className="text-xl">{tpl.emoji}</span>
                {tpl.title}
              </h2>
              <p className="mt-1.5 text-xs leading-relaxed text-text-secondary">{tpl.description}</p>
              <span className="mt-3.5 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-br from-amber-400 to-orange-500 py-2.5 text-sm font-black text-white shadow-md transition group-hover:from-amber-300 group-hover:to-orange-400">
                <Check className="h-4 w-4" />
                Интихоб кардан
              </span>
            </div>
          </button>
        ))}

        {}
        <div className="flex min-h-[220px] flex-col items-center justify-center rounded-3xl border-2 border-dashed border-border bg-surface-muted p-6 text-center">
          <span className="text-3xl opacity-40">✨</span>
          <p className="mt-2 text-sm font-bold text-text-secondary">Шаблонҳои нав</p>
          <p className="mt-1 text-xs text-text-tertiary">Ба зудӣ бозиҳои нав илова мешаванд</p>
        </div>
      </div>
    </div>
  );
}

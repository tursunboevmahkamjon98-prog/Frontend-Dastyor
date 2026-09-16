"use client";

import { useEffect, useRef } from "react";
import { ArrowRight, Lightbulb } from "lucide-react";
import { LabQuestion, OPTION_LETTERS } from "./types";


export default function ExplanationCard({
  question,
  picked,
  onContinue,
}: {
  question: LabQuestion;
  picked: number | null;
  onContinue: () => void;
}) {
  
  
  const btnRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    btnRef.current?.focus();
  }, []);

  const correctText = question.options[question.correctIndex];
  const pickedText = picked !== null ? question.options[picked] : null;

  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center overflow-y-auto bg-[#070c1a]/75 px-4 py-6 backdrop-blur-md">
      <div
        className="relative w-full max-w-md overflow-hidden rounded-[28px] border border-white/20 bg-gradient-to-b from-[#16233f]/95 to-[#0c1526]/95 p-5 shadow-[0_24px_60px_rgba(0,0,0,0.6)]"
        style={{ animation: "lab-panel-in 0.5s cubic-bezier(0.22,1,0.36,1)" }}
      >
        {}
        <span className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-rose-400 via-amber-300 to-emerald-400" aria-hidden />

        <p className="text-center text-3xl">❌</p>
        <p className="mt-1.5 text-center text-xl font-black text-rose-300">Ҷавоби нодуруст!</p>

        <div className="mt-4 space-y-2.5">
          {pickedText && (
            <div className="rounded-2xl border border-rose-400/30 bg-rose-500/10 px-3.5 py-2.5 text-left">
              <p className="text-[10px] font-black uppercase tracking-widest text-rose-300/80">Ҷавоби шумо</p>
              <p className="mt-0.5 text-sm font-bold text-rose-50">
                <span className="mr-1.5 opacity-70">{picked !== null ? OPTION_LETTERS[picked] : ""}</span>
                {pickedText}
              </p>
            </div>
          )}

          <div className="rounded-2xl border border-emerald-400/30 bg-emerald-500/10 px-3.5 py-2.5 text-left">
            <p className="text-[10px] font-black uppercase tracking-widest text-emerald-300/80">Ҷавоби дуруст</p>
            <p className="mt-0.5 text-sm font-bold text-emerald-50">
              <span className="mr-1.5 opacity-70">{OPTION_LETTERS[question.correctIndex]}</span>
              {correctText}
            </p>
          </div>

          {}
          {question.explanation && (
            <div className="rounded-2xl border border-amber-300/30 bg-amber-400/10 px-3.5 py-3 text-left">
              <p className="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-widest text-amber-200/90">
                <Lightbulb className="h-3.5 w-3.5" />
                Чаро?
              </p>
              <p className="mt-1 text-sm font-medium leading-relaxed text-amber-50/95">{question.explanation}</p>
            </div>
          )}
        </div>

        <button
          ref={btnRef}
          type="button"
          onClick={onContinue}
          className="mt-5 flex w-full items-center justify-center gap-2 rounded-2xl bg-gradient-to-br from-cyan-400 to-blue-600 py-3.5 text-sm font-black text-white shadow-[0_6px_0_rgba(30,64,175,0.9)] transition hover:-translate-y-0.5 active:translate-y-0.5 active:shadow-[0_2px_0_rgba(30,64,175,0.9)]"
        >
          Идома додан
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

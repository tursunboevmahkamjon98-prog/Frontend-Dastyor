"use client";

import { ShuffleQuestion } from "./types";


const LETTER_COLORS = ["bg-[#7c3aed]", "bg-[#16a34a]", "bg-[#2563eb]", "bg-[#ea580c]"];


export default function QuestionPanel({
  question,
  picked,
  onAnswer,
}: {
  question: ShuffleQuestion;
  picked: number | null;
  onAnswer: (index: number) => void;
}) {
  const revealed = picked !== null;

  
  
  
  return (
    <div
      className="w-full max-w-lg rounded-3xl border border-white/20 bg-white/95 p-4 shadow-2xl backdrop-blur-sm sm:p-5"
      style={{ animation: "game-round-in 0.35s ease-out" }}
    >
      <div className="grid gap-2.5 sm:grid-cols-2">
        {question.answers.map((ans, i) => {
          const isCorrect = i === question.correctAnswer;
          const isPicked = picked === i;
          return (
            <button
              key={i}
              type="button"
              disabled={revealed}
              onClick={() => onAnswer(i)}
              className={`flex min-h-[52px] w-full items-center gap-3 rounded-2xl border-2 px-3.5 py-3 text-left text-sm font-bold transition active:scale-[0.97] disabled:cursor-default sm:text-base ${
                revealed && isCorrect
                  ? "border-emerald-500 bg-emerald-50 text-emerald-800"
                  : revealed && isPicked
                    ? "border-red-500 bg-red-50 text-red-800"
                    : revealed
                      ? "border-violet-100 bg-violet-50/40 text-[#3b0764] opacity-60"
                      : "border-violet-200 bg-violet-50/70 text-[#3b0764] hover:-translate-y-0.5 hover:border-violet-400 hover:shadow-md"
              }`}
            >
              <span
                className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-xl text-sm font-black text-white shadow-sm ${LETTER_COLORS[i % LETTER_COLORS.length]}`}
              >
                {String.fromCharCode(65 + i)}
              </span>
              <span className="flex-1">{ans}</span>
              {}
              {revealed && isCorrect && <span className="text-lg font-black text-emerald-600">✓</span>}
              {revealed && isPicked && !isCorrect && <span className="text-lg font-black text-red-600">✕</span>}
            </button>
          );
        })}
      </div>
    </div>
  );
}

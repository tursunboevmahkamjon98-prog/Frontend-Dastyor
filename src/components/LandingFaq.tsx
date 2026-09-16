"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";





const ITEMS: { q: string; a: string }[] = [
  {
    q: "Как это работает?",
    a: "Вы выбираете предмет, класс и тему урока — ИИ за несколько секунд создаёт готовый документ: конспект, тест, презентацию, лекцию или практическое задание. Можно отметить сразу несколько — все придут по одной теме. Результат скачивается в Word, PDF или PowerPoint.",
  },
  {
    q: "На каких языках создаются материалы?",
    a: "На таджикском, русском и английском — язык материала выбирается отдельно от языка интерфейса, под тот класс, для которого вы готовите урок.",
  },
  {
    q: "Можно ли редактировать то, что создал ИИ?",
    a: "Да. Презентация выгружается как обычный .pptx с редактируемым текстом, таблицами и диаграммами — не картинками, конспект и тест — как .docx/.pdf. Всё открывается и правится в Word/PowerPoint как любой другой файл.",
  },
  {
    q: "Материалы соответствуют школьной программе?",
    a: "Да — предметы, классы и структура документов ориентированы на программу школ Таджикистана; при этом тему урока вы всегда задаёте сами, так что материал точно попадает в то, что вы проходите.",
  },
];

export default function LandingFaq() {
  const [open, setOpen] = useState<number | null>(0);

  return (
    <div className="mx-auto max-w-3xl divide-y divide-border-light rounded-3xl border border-border-light bg-surface">
      {ITEMS.map((item, i) => {
        const isOpen = open === i;
        return (
          <div key={item.q}>
            <button
              type="button"
              onClick={() => setOpen(isOpen ? null : i)}
              className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left sm:px-6"
              aria-expanded={isOpen}
            >
              <span className="text-sm font-semibold text-text-primary sm:text-base">{item.q}</span>
              <ChevronDown
                className={`h-4.5 w-4.5 shrink-0 text-text-tertiary transition-transform duration-300 ${isOpen ? "rotate-180 text-primary" : ""}`}
              />
            </button>
            <div
              className="grid overflow-hidden px-5 text-sm leading-relaxed text-text-secondary transition-all duration-300 ease-out sm:px-6"
              style={{
                gridTemplateRows: isOpen ? "1fr" : "0fr",
                paddingBottom: isOpen ? "1.1rem" : 0,
                opacity: isOpen ? 1 : 0,
              }}
            >
              <div className="min-h-0">{item.a}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

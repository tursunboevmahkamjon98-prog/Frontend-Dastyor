"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, BookOpen, Check, FileText, Loader2, Paperclip, Sparkles, Upload } from "lucide-react";
import { bookApi, type BookLibraryItem } from "@/lib/book-api";

type AssistantAnswer = {
  goal?: string;
  level?: string;
};

export type SourceChoice = "library" | "uploaded" | "pasted" | "none";

interface CreationAssistantProps {
  topic: string;
  subject: string;
  language: string;
  step: 1 | 2 | 3;
  answers: AssistantAnswer;
  sourceFileName: string | null;
  pastedText: string;
  sourceTruncated: boolean;
  sourceUploading: boolean;
  selectedLibraryBook: BookLibraryItem | null;
  librarySelecting: boolean;
  error: string | null;
  onAnswer: (key: "goal" | "level", value: string) => void;
  onUploadSource: (file: File) => void;
  onSelectLibraryBook: (book: BookLibraryItem) => void;
  onPastedTextChange: (value: string) => void;
  onUsePastedSource: () => void;
  onFinish: (source: SourceChoice) => void;
  onBack: () => void;
}

type AssistantCopy = {
  eyebrow: string;
  title: string;
  intro: string;
  goalQuestion: string;
  goalOptions: { value: string; label: string }[];
  levelQuestion: string;
  levelOptions: { value: string; label: string }[];
  sourceQuestion: string;
  sourceYes: string;
  sourceNo: string;
  uploadTitle: string;
  uploadHint: string;
  uploaded: string;
  truncated: string;
  createFromSource: string;
  pasteTitle: string;
  pastePlaceholder: string;
  usePasted: string;
  createWithoutSource: string;
  back: string;
  fileTypes: string;
  libraryTitle: string;
  libraryHint: string;
  libraryEmpty: string;
  libraryChoose: string;
  librarySelected: string;
};

const COPY: Record<"tg" | "ru" | "en", AssistantCopy> = {
  tg: {
    eyebrow: "Ёвари AI",
    title: "Пеш аз сохтани мавод чанд чизро муайян мекунем",
    intro: "Ҷавобҳои шумо ба AI кӯмак мекунанд, ки маводро барои синф ва мақсади дарс дуруст созад.",
    goalQuestion: "Мақсади асосии ин дарс чист?",
    goalOptions: [
      { value: "explain", label: "Мавзӯи навро фаҳмондан" },
      { value: "practice", label: "Машқ ва мустаҳкамкунӣ" },
      { value: "assessment", label: "Омодагӣ ба санҷиш" },
    ],
    levelQuestion: "Хонандагон мавзӯъро то чӣ андоза медонанд?",
    levelOptions: [
      { value: "beginner", label: "Аз ибтидо меомӯзанд" },
      { value: "some", label: "Каме медонанд" },
      { value: "familiar", label: "Асосҳоро медонанд" },
    ],
    sourceQuestion: "Китоб ё манбаи тайёр доред?",
    sourceYes: "Ҳа, файл дорам",
    sourceNo: "Не, аз дониши умумӣ истифода бар",
    uploadTitle: "Китоб ё маводи дарсиро бор кунед",
    uploadHint: "PDF, DOCX, MD ё TXT • танҳо қисмҳои дахлдор истифода мешаванд",
    uploaded: "Манбаъ бор шуд",
    truncated: "Матни хеле калон буд — қисми мувофиқ интихоб мешавад.",
    createFromSource: "Аз рӯи ин манбаъ сохтан",
    pasteTitle: "Матни китоб ё дарсро часпонед",
    pastePlaceholder: "Матни конспект, китоб ё варақаи дарсиро дар ин ҷо гузоред…",
    usePasted: "Ин матнро истифода бар",
    createWithoutSource: "Бе манбаъ идома додан",
    back: "Бозгашт",
    fileTypes: ".pdf, .docx, .md ё .txt",
    libraryTitle: "Аз китобхонаи фан китоб интихоб кунед",
    libraryHint: "Китобҳои фанни интихобшуда нишон дода мешаванд. AI танҳо маълумоти мувофиқро истифода мебарад.",
    libraryEmpty: "Барои ин фан китоб ёфт нашуд.",
    libraryChoose: "Китобро интихоб кунед",
    librarySelected: "Китоб интихоб шуд",
  },
  ru: {
    eyebrow: "Помощник AI",
    title: "Уточним несколько вещей перед созданием",
    intro: "Ваши ответы помогут AI подобрать материал под класс и цель урока.",
    goalQuestion: "Какова главная цель урока?",
    goalOptions: [
      { value: "explain", label: "Объяснить новую тему" },
      { value: "practice", label: "Практика и закрепление" },
      { value: "assessment", label: "Подготовка к проверке" },
    ],
    levelQuestion: "Насколько ученики знакомы с темой?",
    levelOptions: [
      { value: "beginner", label: "Изучают с нуля" },
      { value: "some", label: "Знают немного" },
      { value: "familiar", label: "Знают основы" },
    ],
    sourceQuestion: "У вас есть книга или готовый источник?",
    sourceYes: "Да, у меня есть файл",
    sourceNo: "Нет, используй общие знания",
    uploadTitle: "Загрузите книгу или учебный материал",
    uploadHint: "PDF, DOCX, MD или TXT • будет использована только нужная часть",
    uploaded: "Источник загружен",
    truncated: "Текст большой — будет выбрана только подходящая часть.",
    createFromSource: "Создать по этому источнику",
    pasteTitle: "Вставьте текст книги или урока",
    pastePlaceholder: "Вставьте сюда конспект, текст книги или учебный материал…",
    usePasted: "Использовать этот текст",
    createWithoutSource: "Продолжить без источника",
    back: "Назад",
    fileTypes: ".pdf, .docx, .md или .txt",
    libraryTitle: "Выберите книгу из библиотеки предмета",
    libraryHint: "Показываем книги выбранного предмета. AI использует только подходящие фрагменты.",
    libraryEmpty: "Для этого предмета книги не найдены.",
    libraryChoose: "Выбрать книгу",
    librarySelected: "Книга выбрана",
  },
  en: {
    eyebrow: "AI assistant",
    title: "Let’s clarify a few things first",
    intro: "Your answers help AI tailor the material to the class and lesson goal.",
    goalQuestion: "What is the main goal of this lesson?",
    goalOptions: [
      { value: "explain", label: "Explain a new topic" },
      { value: "practice", label: "Practice and reinforce" },
      { value: "assessment", label: "Prepare for an assessment" },
    ],
    levelQuestion: "How familiar are the students with the topic?",
    levelOptions: [
      { value: "beginner", label: "Learning from scratch" },
      { value: "some", label: "Know a little" },
      { value: "familiar", label: "Know the basics" },
    ],
    sourceQuestion: "Do you have a book or ready source?",
    sourceYes: "Yes, I have a file",
    sourceNo: "No, use general knowledge",
    uploadTitle: "Upload a book or lesson source",
    uploadHint: "PDF, DOCX, MD or TXT • only relevant parts will be used",
    uploaded: "Source uploaded",
    truncated: "The text was large — only the relevant part will be selected.",
    createFromSource: "Create from this source",
    pasteTitle: "Paste a book or lesson excerpt",
    pastePlaceholder: "Paste lesson notes, a book excerpt or worksheet here…",
    usePasted: "Use this text",
    createWithoutSource: "Continue without a source",
    back: "Back",
    fileTypes: ".pdf, .docx, .md or .txt",
    libraryTitle: "Choose a book from the subject library",
    libraryHint: "Books for the selected subject appear here. AI uses only relevant excerpts.",
    libraryEmpty: "No books were found for this subject.",
    libraryChoose: "Choose a book",
    librarySelected: "Book selected",
  },
};

function copyFor(language: string): AssistantCopy {
  if (language === "Таджикский") return COPY.tg;
  if (language === "Английский") return COPY.en;
  return COPY.ru;
}

export default function CreationAssistant({
  topic,
  subject,
  language,
  step,
  answers,
  sourceFileName,
  pastedText,
  sourceTruncated,
  sourceUploading,
  selectedLibraryBook,
  librarySelecting,
  error,
  onAnswer,
  onUploadSource,
  onSelectLibraryBook,
  onPastedTextChange,
  onUsePastedSource,
  onFinish,
  onBack,
}: CreationAssistantProps) {
  const copy = copyFor(language);
  const [sourceChoice, setSourceChoice] = useState<SourceChoice | null>(null);
  const [libraryBooks, setLibraryBooks] = useState<BookLibraryItem[]>([]);
  const [libraryLoading, setLibraryLoading] = useState(false);

  useEffect(() => {
    if (step !== 3 || sourceChoice !== "library") return;
    const controller = new AbortController();
    void bookApi.library(subject, undefined, controller.signal)
      .then(setLibraryBooks)
      .catch(() => setLibraryBooks([]))
      .finally(() => setLibraryLoading(false));
    return () => controller.abort();
  }, [subject, sourceChoice, step]);

  return (
    <div className="mx-auto max-w-2xl px-4 pb-16 pt-8 sm:px-6">
      <div className="mb-5 flex items-center justify-between">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-2 rounded-xl border border-border bg-white px-3.5 py-2 text-sm font-semibold text-text-secondary shadow-[0_2px_0_0_var(--color-border-light)] transition hover:-translate-y-0.5 hover:text-text-primary"
        >
          <ArrowLeft className="h-4 w-4" />
          {copy.back}
        </button>
        <span className="text-xs font-semibold text-text-tertiary">{step}/3</span>
      </div>

      <div className="overflow-hidden rounded-3xl border border-border-light bg-white shadow-[0_16px_45px_-28px_rgba(15,23,42,0.35)]">
        <div className="border-b border-border-light bg-gradient-to-br from-primary-50/80 via-white to-white p-5 sm:p-7">
          <div className="flex items-start gap-3.5">
            <span className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-primary-50 text-primary shadow-[inset_0_-2px_3px_rgba(220,38,38,0.08)]">
              <Sparkles className="h-5 w-5" />
            </span>
            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">{copy.eyebrow}</p>
              <h1 className="mt-1 text-xl font-bold leading-7 text-text-primary sm:text-2xl">{copy.title}</h1>
              <p className="mt-2 text-sm leading-6 text-text-secondary">{copy.intro}</p>
            </div>
          </div>
          <div className="mt-5 flex items-center gap-1.5" aria-label={`${step}/3`}>
            {[1, 2, 3].map((number) => (
              <span
                key={number}
                className={`h-1.5 flex-1 rounded-full ${number <= step ? "bg-primary" : "bg-border-light"}`}
              />
            ))}
          </div>
        </div>

        <div className="p-5 sm:p-7">
          {error && (
            <div className="mb-4 rounded-xl bg-primary-50 px-4 py-3 text-sm text-primary-dark" role="alert">
              {error}
            </div>
          )}
          <div className="mb-5 flex items-end justify-end">
            <div className="max-w-[85%] rounded-2xl rounded-br-md bg-surface-muted px-4 py-3 text-sm font-medium text-text-primary">
              {topic}
            </div>
          </div>

          {step === 1 && (
            <OptionStep question={copy.goalQuestion} options={copy.goalOptions} selected={answers.goal} onSelect={(value) => onAnswer("goal", value)} />
          )}

          {step === 2 && (
            <OptionStep question={copy.levelQuestion} options={copy.levelOptions} selected={answers.level} onSelect={(value) => onAnswer("level", value)} />
          )}

          {step === 3 && (
            <div>
              <div className="mb-4 flex items-start gap-3">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-primary-50 text-primary">
                  <BookOpen className="h-4 w-4" />
                </span>
                <p className="pt-1 text-base font-semibold leading-6 text-text-primary">{copy.sourceQuestion}</p>
              </div>

              {!sourceChoice && (
                <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                  <button
                    type="button"
                    onClick={() => {
                      setLibraryLoading(true);
                      setSourceChoice("library");
                    }}
                    className="flex items-center gap-3 rounded-xl border border-border bg-white px-4 py-3 text-left text-sm font-semibold text-text-primary transition hover:-translate-y-0.5 hover:border-primary/40 hover:bg-primary-50"
                  >
                    <BookOpen className="h-4 w-4 text-primary" />
                    {copy.libraryChoose}
                  </button>
                  <button
                    type="button"
                    onClick={() => setSourceChoice("uploaded")}
                    className="flex items-center gap-3 rounded-xl border border-border bg-white px-4 py-3 text-left text-sm font-semibold text-text-primary transition hover:-translate-y-0.5 hover:border-primary/40 hover:bg-primary-50"
                  >
                    <Paperclip className="h-4 w-4 text-primary" />
                    {copy.sourceYes}
                  </button>
                  <button
                    type="button"
                    onClick={() => setSourceChoice("pasted")}
                    className="flex items-center gap-3 rounded-xl border border-border bg-white px-4 py-3 text-left text-sm font-semibold text-text-primary transition hover:-translate-y-0.5 hover:border-primary/40 hover:bg-primary-50"
                  >
                    <FileText className="h-4 w-4 text-primary" />
                    {copy.pasteTitle}
                  </button>
                  <button
                    type="button"
                    onClick={() => onFinish("none")}
                    className="flex items-center gap-3 rounded-xl border border-border bg-white px-4 py-3 text-left text-sm font-semibold text-text-primary transition hover:-translate-y-0.5 hover:border-primary/40 hover:bg-primary-50"
                  >
                    <Sparkles className="h-4 w-4 text-primary" />
                    {copy.sourceNo}
                  </button>
                </div>
              )}

              {sourceChoice === "library" && (
                <div className="rounded-2xl border border-dashed border-primary/35 bg-primary-50/40 p-4">
                  <div className="mb-3">
                    <p className="text-sm font-semibold text-text-primary">{copy.libraryTitle}</p>
                    <p className="mt-1 text-xs leading-5 text-text-secondary">{copy.libraryHint}</p>
                  </div>
                  {libraryLoading && (
                    <div className="flex items-center gap-2 rounded-xl bg-white px-3 py-3 text-sm text-text-secondary">
                      <Loader2 className="h-4 w-4 animate-spin text-primary" />
                      {copy.libraryChoose}…
                    </div>
                  )}
                  {!libraryLoading && libraryBooks.length === 0 && (
                    <p className="rounded-xl bg-white px-3 py-3 text-sm text-text-secondary">{copy.libraryEmpty}</p>
                  )}
                  {libraryBooks.length > 0 && (
                    <div className="space-y-2 pr-1">
                      {libraryBooks.map((book) => {
                        const active = selectedLibraryBook?.id === book.id;
                        return (
                          <button
                            key={book.id}
                            type="button"
                            onClick={() => onSelectLibraryBook(book)}
                            disabled={librarySelecting}
                            className={`flex w-full items-center gap-3 rounded-xl border p-3 text-left transition disabled:pointer-events-none disabled:opacity-60 ${active ? "border-primary bg-white" : "border-border-light bg-white hover:border-primary/40"}`}
                          >
                            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-note-bg text-note-icon">
                              <BookOpen className="h-4 w-4" />
                            </span>
                            <span className="min-w-0 flex-1">
                              <span className="block whitespace-normal break-words text-sm font-semibold leading-5 text-text-primary">{book.title}</span>
                              <span className="mt-0.5 block text-xs text-text-tertiary">{book.extension.toUpperCase()}{book.grade_hint ? ` · ${book.grade_hint}` : ""}</span>
                            </span>
                            {active ? <Check className="h-4 w-4 shrink-0 text-primary" /> : <ArrowLeft className="h-4 w-4 shrink-0 rotate-180 text-text-tertiary" />}
                          </button>
                        );
                      })}
                    </div>
                  )}
                  {selectedLibraryBook && (
                    <div className="mt-3 flex items-center gap-2 rounded-xl bg-white px-3 py-2.5 text-sm text-text-primary">
                      {librarySelecting ? <Loader2 className="h-4 w-4 animate-spin text-primary" /> : <Check className="h-4 w-4 text-emerald-600" />}
                      <span className="min-w-0 flex-1 truncate">{selectedLibraryBook.title}</span>
                      <span className="text-xs text-text-tertiary">{copy.librarySelected}</span>
                    </div>
                  )}
                  <div className="mt-4 flex flex-col gap-2 sm:flex-row">
                    <button
                      type="button"
                      onClick={() => onFinish("library")}
                      disabled={!selectedLibraryBook || librarySelecting}
                      className="flex-1 rounded-xl bg-gradient-to-b from-primary-light to-primary px-4 py-3 text-sm font-semibold text-white shadow-[0_3px_0_0_var(--color-primary-dark)] transition hover:-translate-y-0.5 disabled:pointer-events-none disabled:opacity-50"
                    >
                      {copy.createFromSource}
                    </button>
                    <button
                      type="button"
                      onClick={() => onFinish("none")}
                      disabled={librarySelecting}
                      className="rounded-xl border border-border bg-white px-4 py-3 text-sm font-semibold text-text-secondary transition hover:border-primary/40 hover:text-text-primary disabled:pointer-events-none disabled:opacity-50"
                    >
                      {copy.createWithoutSource}
                    </button>
                  </div>
                </div>
              )}

              {sourceChoice === "uploaded" && (
                <div className="rounded-2xl border border-dashed border-primary/35 bg-primary-50/40 p-4">
                  <label className="flex cursor-pointer items-center gap-3 rounded-xl border border-border-light bg-white p-3 transition hover:border-primary/40">
                    <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-pres-bg text-pres-icon">
                      {sourceUploading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Upload className="h-5 w-5" />}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-semibold text-text-primary">{copy.uploadTitle}</span>
                      <span className="mt-0.5 block text-xs text-text-tertiary">{copy.uploadHint} ({copy.fileTypes})</span>
                    </span>
                    <input
                      type="file"
                      className="sr-only"
                      accept=".pdf,.docx,.md,.markdown,.txt"
                      disabled={sourceUploading}
                      onChange={(event) => {
                        const file = event.target.files?.[0];
                        if (file) onUploadSource(file);
                        event.currentTarget.value = "";
                      }}
                    />
                  </label>

                  {sourceFileName && (
                    <div className="mt-3 flex items-start gap-2 rounded-xl bg-white px-3 py-2.5 text-sm text-text-primary">
                      <FileText className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate font-medium">{sourceFileName}</span>
                        {sourceTruncated && <span className="mt-0.5 block text-xs text-text-tertiary">{copy.truncated}</span>}
                      </span>
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                    </div>
                  )}

                  <div className="mt-4 flex flex-col gap-2 sm:flex-row">
                    <button
                      type="button"
                      onClick={() => onFinish("uploaded")}
                      disabled={!sourceFileName || sourceUploading}
                      className="flex-1 rounded-xl bg-gradient-to-b from-primary-light to-primary px-4 py-3 text-sm font-semibold text-white shadow-[0_3px_0_0_var(--color-primary-dark)] transition hover:-translate-y-0.5 disabled:pointer-events-none disabled:opacity-50"
                    >
                      {copy.createFromSource}
                    </button>
                    <button
                      type="button"
                      onClick={() => onFinish("none")}
                      disabled={sourceUploading}
                      className="rounded-xl border border-border bg-white px-4 py-3 text-sm font-semibold text-text-secondary transition hover:border-primary/40 hover:text-text-primary disabled:pointer-events-none disabled:opacity-50"
                    >
                      {copy.createWithoutSource}
                    </button>
                  </div>
                </div>
              )}

              {sourceChoice === "pasted" && (
                <div className="rounded-2xl border border-dashed border-primary/35 bg-primary-50/40 p-4">
                  <label className="block text-sm font-semibold text-text-primary">
                    {copy.pasteTitle}
                    <textarea
                      className="mt-3 w-full rounded-xl border border-border-light bg-white px-3.5 py-3 text-sm font-normal text-text-primary outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/10"
                      rows={8}
                      value={pastedText}
                      onChange={(event) => onPastedTextChange(event.target.value)}
                      placeholder={copy.pastePlaceholder}
                    />
                  </label>
                  <div className="mt-3 flex flex-col gap-2 sm:flex-row">
                    <button
                      type="button"
                      onClick={onUsePastedSource}
                      disabled={!pastedText.trim()}
                      className="flex-1 rounded-xl bg-gradient-to-b from-primary-light to-primary px-4 py-3 text-sm font-semibold text-white shadow-[0_3px_0_0_var(--color-primary-dark)] transition hover:-translate-y-0.5 disabled:pointer-events-none disabled:opacity-50"
                    >
                      {copy.usePasted}
                    </button>
                    <button
                      type="button"
                      onClick={() => onFinish("none")}
                      className="rounded-xl border border-border bg-white px-4 py-3 text-sm font-semibold text-text-secondary transition hover:border-primary/40 hover:text-text-primary"
                    >
                      {copy.createWithoutSource}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function OptionStep({
  question,
  options,
  selected,
  onSelect,
}: {
  question: string;
  options: { value: string; label: string }[];
  selected?: string;
  onSelect: (value: string) => void;
}) {
  return (
    <div>
      <div className="mb-4 flex items-start gap-3">
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-primary-50 text-primary">
          <Sparkles className="h-4 w-4" />
        </span>
        <p className="pt-1 text-base font-semibold leading-6 text-text-primary">{question}</p>
      </div>
      <div className="grid gap-2">
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => onSelect(option.value)}
            className={`flex items-center gap-3 rounded-xl border px-4 py-3 text-left text-sm font-semibold transition hover:-translate-y-0.5 hover:border-primary/40 hover:bg-primary-50 ${
              selected === option.value ? "border-primary bg-primary-50 text-primary" : "border-border bg-white text-text-primary"
            }`}
          >
            <span className={`grid h-5 w-5 place-items-center rounded-full border ${selected === option.value ? "border-primary bg-primary text-white" : "border-border"}`}>
              {selected === option.value && <Check className="h-3 w-3" />}
            </span>
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}

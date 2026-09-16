import Link from "next/link";
import {
  BookOpen, Presentation, ClipboardCheck, Lightbulb, ClipboardList,
  Sparkles, Check, Zap, ShieldCheck, Clock, ArrowRight,
  FileDown, Languages, Wand2, Layers, Wallet, Pencil, Download,
} from "lucide-react";
import SubjectsCarousel from "@/components/SubjectsCarousel";
import Reveal from "@/components/Reveal";
import LandingFaq from "@/components/LandingFaq";
import SamplesGallery from "@/components/SamplesGallery";
import { SUBJECTS, LANGUAGES } from "@/lib/material-types";







const FEATURES = [
  {
    icon: BookOpen,
    title: "Конспект",
    desc: "Полный, структурированный конспект урока по любой теме — с примерами и заданиями для проверки.",
    bg: "bg-note-bg",
    color: "text-note-icon",
  },
  {
    icon: Lightbulb,
    title: "Лекция",
    desc: "Развёрнутый текст лекции по теме — с объяснениями, примерами и выводами.",
    bg: "bg-lecture-bg",
    color: "text-lecture-icon",
  },
  {
    icon: ClipboardCheck,
    title: "Тест",
    desc: "Автоматический тест с разными типами вопросов — с ответами и объяснениями к каждому.",
    bg: "bg-test-bg",
    color: "text-test-icon",
  },
  {
    icon: Presentation,
    title: "Презентация",
    desc: "Готовая колода слайдов — редактируемый .pptx с таблицами, диаграммами и рисунками, не картинки.",
    bg: "bg-pres-bg",
    color: "text-pres-icon",
  },
  {
    icon: ClipboardList,
    title: "Амалӣ супоришҳо",
    desc: "Индивидуальные и групповые практические задания по теме урока.",
    bg: "bg-amaliy-bg",
    color: "text-amaliy-icon",
  },
];

const FACTS = [
  { icon: Zap, label: "Секунды, не часы" },
  { icon: ShieldCheck, label: "Без ошибок и лишних слов" },
  { icon: Clock, label: "План до 62 дней подряд" },
];





const STATS = [
  { value: "5", label: "видов материалов" },
  { value: String(SUBJECTS.length), label: "предметов" },
  { value: String(LANGUAGES.length), label: "языка" },
  
  { value: "4", label: "формата для скачивания" },
];

const STEPS = [
  {
    n: "01",
    icon: Wand2,
    title: "Выберите предмет, класс и тему",
    desc: "Так же, как вы бы объяснили коллеге, что нужно на завтра — без специальных «промптов» и настроек.",
  },
  {
    n: "02",
    icon: Sparkles,
    title: "ИИ готовит документ за секунды",
    desc: "Конспект, тест, лекция, презентация или практическое задание — по выбранной теме, на нужном языке.",
  },
  {
    n: "03",
    icon: FileDown,
    title: "Скачайте и используйте на уроке",
    desc: "Word, PDF или PowerPoint — открывается и правится как любой обычный файл, ничего заблокированного.",
  },
];



const ALL_AT_ONCE_POINTS = [
  "Одна тема — пять документов за одну генерацию",
  "Каждый материал открывается и правится отдельно",
  "Всё скачивается одним архивом",
];


const TRUST = [
  {
    icon: Wallet,
    title: "Без подписки",
    desc: "Ничего не списывается ежемесячно. Вы платите только за материалы, которые действительно создали.",
  },
  {
    icon: Pencil,
    title: "Файлы можно править",
    desc: "Презентация выгружается как настоящий .pptx с редактируемым текстом и таблицами — не картинками.",
  },
  {
    icon: FileDown,
    title: "Обычные форматы",
    desc: "Word, PowerPoint, PDF и текст. Открывается на любом школьном компьютере, ничего устанавливать не нужно.",
  },
  {
    icon: Languages,
    title: "Три языка",
    desc: "Таджикский, русский и английский. Язык материала выбирается отдельно от языка интерфейса.",
  },
];

const NAV_LINKS = [
  { href: "#features", label: "Возможности" },
  { href: "#how", label: "Как это работает" },
  { href: "#samples", label: "Примеры" },
  { href: "#subjects", label: "Предметы" },
  { href: "#faq", label: "Вопросы" },
];

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col overflow-x-clip bg-background">
      {}
      <header className="sticky top-0 z-30 border-b border-border-light/70 bg-background/80 backdrop-blur-md">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
          <div className="flex items-center gap-2.5">
            {}
            <img src="/logo.png" alt="Dastyor" className="h-9 w-9" />
            <span className="text-lg font-bold text-text-primary">Dastyor</span>
          </div>
          <nav className="hidden items-center gap-1 md:flex">
            {NAV_LINKS.map((l) => (
              <a
                key={l.href}
                href={l.href}
                className="rounded-lg px-3 py-2 text-sm font-medium text-text-secondary transition hover:bg-surface-muted hover:text-text-primary"
              >
                {l.label}
              </a>
            ))}
          </nav>
          <div className="flex items-center gap-2 sm:gap-3">
            <Link href="/login" className="rounded-xl px-3 py-2 text-sm font-semibold text-text-primary hover:bg-surface-muted sm:px-4">
              Войти
            </Link>
            <Link href="/register" className="rounded-xl bg-primary px-3 py-2 text-sm font-semibold text-white shadow-sm shadow-primary/25 transition hover:-translate-y-0.5 hover:bg-primary-dark sm:px-4">
              Начать
            </Link>
          </div>
        </div>
      </header>

      {}
      <section className="relative">
        <div
          className="pointer-events-none absolute left-1/2 top-0 -z-10 h-[620px] w-[920px] -translate-x-1/2 rounded-full bg-primary/[0.10] blur-3xl"
          style={{ animation: "landing-blob-drift 16s ease-in-out infinite" }}
          aria-hidden
        />
        <div
          className="pointer-events-none absolute -right-24 top-24 -z-10 h-72 w-72 rounded-full bg-pres-icon/[0.08] blur-3xl"
          style={{ animation: "landing-blob-drift 20s ease-in-out infinite", animationDelay: "-4s" }}
          aria-hidden
        />
        <div
          className="pointer-events-none absolute -left-24 top-60 -z-10 h-72 w-72 rounded-full bg-note-icon/[0.08] blur-3xl"
          style={{ animation: "landing-blob-drift 18s ease-in-out infinite", animationDelay: "-9s" }}
          aria-hidden
        />

        <div className="mx-auto grid w-full max-w-6xl grid-cols-1 items-center gap-10 px-4 pt-14 pb-16 sm:pt-20 sm:pb-24 lg:grid-cols-[1.05fr_0.95fr] lg:gap-6">
          <div className="flex flex-col items-center text-center lg:items-start lg:text-left">
            <div className="mb-5 inline-flex items-center gap-1.5 rounded-full border border-primary/15 bg-primary-50 px-3.5 py-1.5 text-xs font-semibold text-primary-dark">
              <Sparkles className="h-3.5 w-3.5" />
              Учебные материалы с помощью ИИ
            </div>
            <h1 className="max-w-xl text-4xl font-extrabold tracking-tight text-text-primary sm:text-6xl">
              От темы урока до готового документа —{" "}
              <span className="relative inline-block whitespace-nowrap">
                <span className="relative bg-gradient-to-r from-primary via-primary-light to-primary bg-clip-text text-transparent">
                  за секунды
                </span>
                {}
                <svg
                  viewBox="0 0 220 14"
                  className="pointer-events-none absolute -bottom-2 left-0 h-3 w-full text-primary/70 sm:-bottom-3"
                  fill="none"
                  aria-hidden
                >
                  <path
                    d="M2 9.5C40 2.5 90 1 130 6C160 9.5 190 4 218 7.5"
                    stroke="currentColor"
                    strokeWidth="3"
                    strokeLinecap="round"
                    style={{ strokeDasharray: 220, animation: "landing-draw 1s ease-out 1.1s both" }}
                  />
                </svg>
              </span>
            </h1>
            <p className="mt-5 max-w-xl text-base text-text-secondary sm:text-lg">
              Конспект, тест, презентация, лекция, практическое задание — или целый
              месячный учебный план, без ошибок и лишних слов.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link
                href="/register"
                className="group flex items-center justify-center gap-2 rounded-xl bg-primary px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-primary/25 transition hover:-translate-y-0.5 hover:bg-primary-dark"
              >
                Начать бесплатно
                <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
              </Link>
              <Link
                href="/login"
                className="rounded-xl border border-border bg-surface px-6 py-3 text-sm font-semibold text-text-primary transition hover:-translate-y-0.5 hover:bg-surface-muted"
              >
                У меня есть аккаунт
              </Link>
            </div>
            {/* Direct APK download - the app isn't on Google Play (a
                teacher-facing tool for one country doesn't clear Play's
                review bar the same way a consumer app does), so this link
                is the only install path. Points at the backend's own
                /uploads mount (see backend/app/main.py's StaticFiles
                mount) rather than a package registry - the APK is dropped
                there by hand on the server, same as any other upload. */}
            <a
              href="/uploads/app/dastyor.apk"
              download
              className="mt-3 inline-flex items-center justify-center gap-2 text-sm font-medium text-text-secondary underline decoration-border underline-offset-4 transition hover:text-primary"
            >
              <Download className="h-4 w-4" />
              Скачать приложение для Android (.apk)
            </a>
            <div className="mt-10 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 lg:justify-start">
              {FACTS.map(({ icon: Icon, label }) => (
                <span key={label} className="flex items-center gap-1.5 text-sm text-text-tertiary">
                  <Icon className="h-4 w-4 text-primary" />
                  {label}
                </span>
              ))}
            </div>
          </div>

          {}
          <div className="relative hidden lg:block">
            {}
            <div
              className="pointer-events-none absolute right-10 top-6 h-56 w-56 rounded-full bg-primary/[0.14] blur-3xl"
              style={{ animation: "landing-blob-drift 14s ease-in-out infinite" }}
              aria-hidden
            />
            <div
              className="pointer-events-none absolute bottom-0 left-6 h-48 w-48 rounded-full bg-note-icon/[0.10] blur-3xl"
              style={{ animation: "landing-blob-drift 17s ease-in-out infinite", animationDelay: "-6s" }}
              aria-hidden
            />
            <div className="relative" style={{ animation: "landing-float 6s ease-in-out infinite" }}>
              {}
              <img
                src="/images/hero-teacher.svg"
                alt=""
                className="relative mx-auto h-auto w-full max-w-md drop-shadow-xl"
              />

              <div
                className="absolute left-2 top-4 flex items-center gap-1.5 rounded-full bg-surface/90 px-3 py-1.5 text-xs font-semibold text-primary shadow-md shadow-black/[0.06] backdrop-blur"
                style={{ ["--chip-rot" as string]: "-3deg", animation: "landing-float-chip 5s ease-in-out infinite" }}
              >
                <Sparkles className="h-3.5 w-3.5" />
                ИИ-ассистент
              </div>
              <div
                className="absolute bottom-10 right-2 rounded-2xl bg-surface/90 px-4 py-2.5 text-xs font-semibold text-text-primary shadow-md shadow-black/[0.06] backdrop-blur"
                style={{ ["--chip-rot" as string]: "2deg", animation: "landing-float-chip 5.5s ease-in-out infinite", animationDelay: "-2s" }}
              >
                5 видов материалов
              </div>
              <div
                className="absolute right-0 top-1/3 flex items-center gap-1.5 rounded-2xl bg-surface/90 px-3 py-2 text-xs font-semibold text-success shadow-md shadow-black/[0.06] backdrop-blur"
                style={{ ["--chip-rot" as string]: "3deg", animation: "landing-float-chip 4.5s ease-in-out infinite", animationDelay: "-1s" }}
              >
                <Check className="h-3.5 w-3.5" />
                Готово за секунды
              </div>
            </div>
          </div>
        </div>
      </section>

      {}
      <section className="mx-auto w-full max-w-5xl px-4 pb-16 sm:px-6 sm:pb-24">
        <Reveal className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {STATS.map((s) => (
            <div key={s.label} className="rounded-2xl border border-border-light bg-surface px-4 py-6 text-center shadow-sm shadow-black/[0.02]">
              <p className="text-3xl font-extrabold text-primary sm:text-4xl">{s.value}</p>
              <p className="mt-1 text-xs font-medium text-text-secondary sm:text-sm">{s.label}</p>
            </div>
          ))}
        </Reveal>
      </section>

      {}
      <section id="features" className="mx-auto w-full max-w-6xl px-4 pb-16 sm:px-6 sm:pb-24">
        <Reveal className="mx-auto mb-12 max-w-xl text-center">
          <h2 className="text-2xl font-bold text-text-primary sm:text-3xl">Всё, что нужно для урока</h2>
          <p className="mt-3 text-text-secondary">Пять видов материалов — по одной и той же теме, за одну генерацию.</p>
        </Reveal>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, desc, bg, color }, i) => (
            <Reveal key={title} delay={(i % 3) * 100} className="group rounded-2xl border border-border-light bg-surface p-5 transition hover:-translate-y-1 hover:border-primary/25 hover:shadow-lg hover:shadow-black/[0.05]">
              <div className={`mb-4 flex h-11 w-11 items-center justify-center rounded-xl ${bg} transition group-hover:scale-110`}>
                <Icon className={`h-5 w-5 ${color}`} />
              </div>
              <h3 className="mb-1.5 font-semibold text-text-primary">{title}</h3>
              <p className="text-sm leading-relaxed text-text-secondary">{desc}</p>
            </Reveal>
          ))}
        </div>
      </section>

      {}
      <section id="how" className="mx-auto w-full max-w-6xl px-4 pb-16 sm:px-6 sm:pb-24">
        <Reveal className="mx-auto mb-12 max-w-xl text-center">
          <h2 className="text-2xl font-bold text-text-primary sm:text-3xl">Как это работает</h2>
          <p className="mt-3 text-text-secondary">Три шага — от пустого экрана до готового урока.</p>
        </Reveal>
        <div className="relative grid grid-cols-1 gap-6 md:grid-cols-3">
          <div className="pointer-events-none absolute top-9 left-[16.5%] right-[16.5%] hidden h-px bg-border md:block" aria-hidden />
          {STEPS.map((step, i) => (
            <Reveal key={step.n} delay={i * 120} className="relative rounded-2xl border border-border-light bg-surface p-6 shadow-sm shadow-black/[0.02]">
              <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-primary text-white shadow-md shadow-primary/25">
                <step.icon className="h-5 w-5" />
              </div>
              <span className="absolute right-6 top-6 text-3xl font-extrabold text-border">{step.n}</span>
              <h3 className="mb-2 font-semibold text-text-primary">{step.title}</h3>
              <p className="text-sm leading-relaxed text-text-secondary">{step.desc}</p>
            </Reveal>
          ))}
        </div>
      </section>

      {}
      <section className="mx-auto w-full max-w-6xl px-4 pb-16 sm:px-6 sm:pb-24">
        <Reveal className="overflow-hidden rounded-3xl border border-border-light bg-surface shadow-sm shadow-black/[0.02]">
          <div className="grid gap-8 p-7 sm:p-10 lg:grid-cols-2 lg:items-center">
            <div>
              <div className="mb-4 inline-flex items-center gap-1.5 rounded-full border border-primary/15 bg-primary-50 px-3.5 py-1.5 text-xs font-semibold text-primary-dark">
                <Layers className="h-3.5 w-3.5" />
                Всё сразу
              </div>
              <h2 className="mb-3 text-2xl font-bold text-text-primary sm:text-3xl">
                Один раз ввели тему — получили весь урок
              </h2>
              <p className="mb-6 text-text-secondary">
                Не нужно создавать конспект, потом отдельно тест, потом презентацию.
                Отметьте нужные материалы — и все они придут по одной и той же теме,
                согласованные между собой.
              </p>
              <ul className="space-y-3">
                {ALL_AT_ONCE_POINTS.map((point) => (
                  <li key={point} className="flex items-start gap-2.5 text-sm text-text-secondary">
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                    {point}
                  </li>
                ))}
              </ul>
            </div>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-2">
              {FEATURES.map(({ icon: Icon, title, bg, color }) => (
                <div
                  key={title}
                  className="flex items-center gap-2.5 rounded-xl border border-border-light bg-background px-3 py-3"
                >
                  <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${bg}`}>
                    <Icon className={`h-4.5 w-4.5 ${color}`} />
                  </span>
                  <span className="text-xs font-semibold leading-tight text-text-primary">{title}</span>
                </div>
              ))}
              <div className="flex items-center justify-center rounded-xl border border-dashed border-primary/30 bg-primary-50/50 px-3 py-3 text-center text-xs font-semibold text-primary-dark">
                Одна тема
              </div>
            </div>
          </div>
        </Reveal>
      </section>

      <div id="subjects">
        <SubjectsCarousel />
      </div>

      {}
      {}
      <section id="samples" className="mx-auto w-full max-w-6xl px-4 pb-16 sm:px-6 sm:pb-24">
        <Reveal className="mx-auto mb-10 max-w-xl text-center">
          <h2 className="text-2xl font-bold text-text-primary sm:text-3xl">Как выглядит результат</h2>
          <p className="mt-3 text-text-secondary">
            Настоящие страницы, созданные Dastyor — не макеты.
          </p>
        </Reveal>
        <Reveal>
          <SamplesGallery />
        </Reveal>
        <Reveal className="mt-8 text-center">
          <Link
            href="/register"
            className="group inline-flex items-center gap-2 rounded-xl bg-primary px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-primary/25 transition hover:-translate-y-0.5 hover:bg-primary-dark"
          >
            Создать такой же
            <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
          </Link>
        </Reveal>
      </section>

      {}
      <section className="mx-auto w-full max-w-6xl px-4 pb-16 sm:px-6 sm:pb-24">
        <Reveal className="mx-auto mb-12 max-w-xl text-center">
          <h2 className="text-2xl font-bold text-text-primary sm:text-3xl">Почему этому можно доверять</h2>
          <p className="mt-3 text-text-secondary">Никаких подписок и закрытых форматов — вы всегда владеете результатом.</p>
        </Reveal>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {TRUST.map(({ icon: Icon, title, desc }, i) => (
            <Reveal
              key={title}
              delay={i * 90}
              className="rounded-2xl border border-border-light bg-surface p-5 shadow-sm shadow-black/[0.02]"
            >
              <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-primary-50">
                <Icon className="h-5 w-5 text-primary" />
              </div>
              <h3 className="mb-1.5 font-semibold text-text-primary">{title}</h3>
              <p className="text-sm leading-relaxed text-text-secondary">{desc}</p>
            </Reveal>
          ))}
        </div>
      </section>

      {}
      <section id="faq" className="mx-auto w-full max-w-4xl px-4 pb-20 sm:px-6 sm:pb-28">
        <Reveal className="mx-auto mb-10 max-w-xl text-center">
          <h2 className="text-2xl font-bold text-text-primary sm:text-3xl">Частые вопросы</h2>
        </Reveal>
        <Reveal>
          <LandingFaq />
        </Reveal>
      </section>

      {}
      <section className="mx-auto w-full max-w-2xl px-4 pb-20 text-center sm:pb-28">
        <Reveal>
          <div className="mb-5 inline-flex items-center gap-1.5 rounded-full border border-primary/15 bg-primary-50 px-3.5 py-1.5 text-xs font-semibold text-primary-dark">
            <Languages className="h-3.5 w-3.5" />
            Таджикский · Русский · Английский
          </div>
          <h2 className="mb-3 text-2xl font-bold text-text-primary sm:text-3xl">Начните прямо сейчас</h2>
          <p className="mb-7 text-text-secondary">Регистрация бесплатна и занимает меньше минуты.</p>
          <Link
            href="/register"
            className="group inline-flex items-center gap-2 rounded-xl bg-primary px-8 py-3.5 text-sm font-semibold text-white shadow-lg shadow-primary/25 transition hover:-translate-y-0.5 hover:bg-primary-dark"
          >
            Зарегистрироваться бесплатно
            <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
          </Link>
        </Reveal>
      </section>

      <footer className="border-t border-border-light py-8">
        <div className="mx-auto flex w-full max-w-6xl flex-col items-center gap-4 px-4 text-center sm:flex-row sm:justify-between sm:text-left">
          <div className="flex items-center gap-2">
            {}
            <img src="/logo.png" alt="Dastyor" className="h-7 w-7" />
            <span className="text-sm font-semibold text-text-primary">Dastyor</span>
          </div>
          <nav className="flex flex-wrap items-center justify-center gap-x-5 gap-y-1">
            {NAV_LINKS.map((l) => (
              <a key={l.href} href={l.href} className="text-xs font-medium text-text-secondary hover:text-primary">
                {l.label}
              </a>
            ))}
          </nav>
          <p className="text-xs text-text-tertiary">© {new Date().getFullYear()} Dastyor. Все права защищены.</p>
        </div>
      </footer>
    </main>
  );
}

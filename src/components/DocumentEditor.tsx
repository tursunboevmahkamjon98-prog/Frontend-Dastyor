"use client";

import { useEditor, EditorContent, type JSONContent, type Editor } from "@tiptap/react";
import { Node } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import Underline from "@tiptap/extension-underline";
import TextAlign from "@tiptap/extension-text-align";
import Link from "@tiptap/extension-link";
import TextStyle from "@tiptap/extension-text-style";
import Color from "@tiptap/extension-color";
import Highlight from "@tiptap/extension-highlight";
import { renderToString } from "katex";
import { useEffect, useRef, useState } from "react";
import {
  Bold, Italic, Underline as UnderlineIcon, Strikethrough, List, ListOrdered, Undo2, Redo2,
  AlignLeft, AlignCenter, AlignRight, Link2 as LinkIcon, Loader2,
  Palette, Highlighter, IndentIncrease, IndentDecrease, ChevronDown,
  Bookmark, Printer, Copy,
} from "lucide-react";
import { useT } from "@/lib/i18n";
import VisualBlockRenderer, { type VisualBlock } from "./konspekt/VisualBlockRenderer";
import MathText from "./konspekt/MathText";

type Lang = "ru" | "tg" | "en";

/* Fields that are plain prose/lists in the konspekt+lektsiya content schema
 * (see backend/app/ai_service.py's RETURN JSON) and therefore safe to show
 * as one continuous, freely-editable rich-text document. Everything else
 * (lesson_stages, quick_check, formulas, concept_cards with tables,
 * code_blocks, visual_blocks, worked_examples) is genuinely structured data
 * — editing it as free text and parsing it back would risk silently
 * corrupting it — so those render as read-only cards below the editor
 * instead, same as before, just not inside a PDF iframe. Saving NEVER
 * rebuilds the whole content object: it only overwrites the specific keys
 * below, so every field this component doesn't know about passes through
 * completely untouched. */
const LIST_FIELDS = ["objectives", "competencies", "key_concepts", "tools", "group_work", "important_notes", "homework"] as const;
const PROSE_FIELDS = ["main_content", "consolidation", "summary"] as const;
type ListField = (typeof LIST_FIELDS)[number];
type ProseField = (typeof PROSE_FIELDS)[number];

const LABELS: Record<ListField | ProseField, Record<Lang, string>> = {
  objectives: { ru: "Цели урока", tg: "Мақсадҳои дарс", en: "Lesson objectives" },
  competencies: { ru: "Компетенции", tg: "Салоҳиятҳо", en: "Competencies" },
  key_concepts: { ru: "Ключевые понятия", tg: "Мафҳумҳои асосӣ", en: "Key concepts" },
  tools: { ru: "Материалы", tg: "Мавод", en: "Materials" },
  group_work: { ru: "Групповая работа", tg: "Кори гурӯҳӣ", en: "Group work" },
  important_notes: { ru: "Важные замечания", tg: "Қайдҳои муҳим", en: "Important notes" },
  homework: { ru: "Домашнее задание", tg: "Вазифаи хонагӣ", en: "Homework" },
  main_content: { ru: "Основное содержание", tg: "Мазмуни асосӣ", en: "Main content" },
  consolidation: { ru: "Закрепление", tg: "Мустаҳкамкунӣ", en: "Consolidation" },
  summary: { ru: "Итог", tg: "Хулоса", en: "Summary" },
};

const STRUCTURED_LABELS: Record<string, Record<Lang, string>> = {
  lesson_stages: { ru: "Этапы урока", tg: "Марҳилаҳои дарс", en: "Lesson stages" },
  quick_check: { ru: "Быстрая проверка", tg: "Санҷиши тез", en: "Quick check" },
  formulas: { ru: "Формулы", tg: "Формулаҳо", en: "Formulas" },
  concept_cards: { ru: "Понятия", tg: "Мафҳумҳо", en: "Concepts" },
  code_blocks: { ru: "Код", tg: "Код", en: "Code" },
  worked_examples: { ru: "Решённые примеры", tg: "Мисолҳои ҳалшуда", en: "Worked examples" },
  real_life_examples: { ru: "Примеры из жизни", tg: "Мисолҳои ҳаётӣ", en: "Real-life examples" },
};

const FIELD_ORDER: (ListField | ProseField)[] = [
  "objectives", "competencies", "key_concepts", "main_content", "tools",
  "group_work", "consolidation", "summary", "important_notes", "homework",
];

const LESSON_STAGE_HEADERS: Record<Lang, [string, string, string]> = {
  ru: ["Этап", "Время", "Деятельность учителя и учеников"],
  tg: ["Марҳила", "Вақт", "Фаъолияти омӯзгор ва хонандагон"],
  en: ["Stage", "Time", "Teacher and learner activity"],
};

function langKey(language?: string): Lang {
  if (language === "Таджикский") return "tg";
  if (language === "Английский") return "en";
  return "ru";
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function escapeAttribute(s: string): string {
  return escapeHtml(s).replace(/"/g, "&quot;");
}

function mathMarkup(text: string): string {
  const source = String(text ?? "");
  const mathPattern = /\$\$([\s\S]*?)\$\$|\$([^$\n]+?)\$|\\\(([\s\S]*?)\\\)/g;
  let html = "";
  let lastIndex = 0;

  for (const match of source.matchAll(mathPattern)) {
    const full = match[0];
    const index = match.index ?? 0;
    const expression = (match[1] ?? match[2] ?? match[3] ?? "").trim();
    html += escapeHtml(source.slice(lastIndex, index));
    if (!expression) {
      html += escapeHtml(full);
    } else {
      html += `<span data-inline-math="${escapeAttribute(expression)}"></span>`;
    }
    lastIndex = index + full.length;
  }

  return html + escapeHtml(source.slice(lastIndex));
}

const InlineMath = Node.create({
  name: "inlineMath",
  group: "inline",
  inline: true,
  atom: true,
  selectable: false,
  addAttributes() {
    return { source: { default: "" } };
  },
  parseHTML() {
    return [{ tag: "span[data-inline-math]" }];
  },
  renderHTML({ node }) {
    const source = String(node.attrs.source ?? "");
    return ["span", { class: "inline-math", "data-inline-math": source }, source];
  },
  addNodeView() {
    return ({ node }) => {
      const source = String(node.attrs.source ?? "");
      const dom = document.createElement("span");
      dom.className = "inline-math";
      dom.setAttribute("data-inline-math", source);
      try {
        dom.innerHTML = renderToString(source, {
          displayMode: false,
          throwOnError: false,
          output: "htmlAndMathml",
        });
      } catch {
        dom.textContent = source;
      }
      return { dom };
    };
  },
});

function looksLikeCodeLine(line: string): boolean {
  const value = line.trim();
  if (!value) return false;
  // \S+\( (no space before the paren) catches real calls like "print(" or
  // "foo(" without also matching an ordinary parenthetical aside in prose
  // ("Энергия (аз грекӣ...)" has a space before "(" and must stay prose).
  return /^(?:def\b|class\b|import\b|from\b|return\b|if\b|elif\b|else\s*:|for\b|while\b|try\s*:|except\b|with\b|print\s*\(|#|\S+\s*(?:=|\+=|-=|\*=|\/=)|\S+\()/i.test(value);
}

function renderTextWithCode(text: string): string {
  const lines = text.trim().split(/\r?\n/);
  const chunks: string[] = [];
  let proseLines: string[] = [];
  let codeLines: string[] = [];

  const flushProse = () => {
    const value = proseLines.join(" ").trim();
    if (value) chunks.push(`<p>${mathMarkup(value)}</p>`);
    proseLines = [];
  };
  const flushCode = () => {
    const value = codeLines.join("\n").trim();
    if (value) chunks.push(`<pre><code>${escapeHtml(value)}</code></pre>`);
    codeLines = [];
  };

  for (const line of lines) {
    const split = splitExampleText(line);
    if (split.code) {
      if (split.text) proseLines.push(split.text);
      flushProse();
      codeLines.push(split.code);
      continue;
    }

    if (looksLikeCodeLine(line) || (codeLines.length > 0 && /^\s+/.test(line))) {
      flushProse();
      codeLines.push(line);
    } else {
      flushCode();
      proseLines.push(line);
    }
  }

  flushCode();
  flushProse();
  return chunks.join("");
}

function isListField(key: string): key is ListField {
  return (LIST_FIELDS as readonly string[]).includes(key);
}

function buildInitialHtml(content: Record<string, unknown>, lk: Lang): string {
  let html = "";
  for (const key of FIELD_ORDER) {
    const val = content[key];
    if (isListField(key)) {
      const items = Array.isArray(val) ? val.filter((v): v is string => typeof v === "string" && v.trim().length > 0) : [];
      if (!items.length) continue;
      html += `<h2>${escapeHtml(LABELS[key][lk])}</h2><ul>${items.map((i) => `<li>${mathMarkup(i)}</li>`).join("")}</ul>`;
    } else {
      const text = typeof val === "string" ? val.trim() : "";
      if (!text) continue;
      html += `<h2>${escapeHtml(LABELS[key][lk])}</h2>`;
      html += text.split(/\n{2,}/).map(renderTextWithCode).join("");
    }
  }
  return html || "<p></p>";
}

function nodeText(node: JSONContent): string {
  if (node.type === "text") return node.text ?? "";
  if (node.type === "inlineMath") return `$${String(node.attrs?.source ?? "")}$`;
  if (!node.content) return "";
  return node.content.map(nodeText).join("");
}

function splitExampleText(value: string): { text: string; code: string | null } {
  const marker = value.match(/\s+[—-]\s+(?=(?:def\b|import\b|from\b|return\b|print\s*\(|#|[A-Za-z_]\w*\s*=))/i);
  if (!marker || marker.index == null) return { text: value.trim(), code: null };
  return {
    text: value.slice(0, marker.index).trim(),
    code: value.slice(marker.index + marker[0].length).trim() || null,
  };
}

type ExamplePart = { kind: "text" | "code"; value: string };

function splitExampleValue(value: string): ExamplePart[] {
  const trimmed = value.trim();
  if (!trimmed) return [];

  const split = splitExampleText(trimmed);
  if (split.code) {
    return [
      ...(split.text ? [{ kind: "text" as const, value: split.text }] : []),
      { kind: "code", value: split.code },
    ];
  }

  const lines = trimmed.split(/\r?\n/).filter((line) => line.trim().length > 0);
  if (lines.length > 0 && lines.every(looksLikeCodeLine)) {
    return [{ kind: "code", value: trimmed }];
  }

  return [{ kind: "text", value: trimmed }];
}

function parseDocToFields(doc: JSONContent, lk: Lang): Partial<Record<ListField | ProseField, string | string[]>> {
  const reverseLabel: Record<string, ListField | ProseField> = {};
  for (const key of [...LIST_FIELDS, ...PROSE_FIELDS]) reverseLabel[LABELS[key][lk]] = key;

  const result: Partial<Record<ListField | ProseField, string | string[]>> = {};
  let currentField: ListField | ProseField | null = null;
  let prose: string[] = [];
  let list: string[] = [];

  function flush() {
    if (!currentField) return;
    result[currentField] = isListField(currentField) ? list : prose.join("\n\n");
    prose = [];
    list = [];
  }

  for (const node of doc.content ?? []) {
    if (node.type === "heading") {
      // Only a heading whose text matches a known section label starts a
      // new field. A heading the user typed themselves (any other text, or
      // any other level) does NOT reset currentField — otherwise it would
      // silently orphan every paragraph after it, since text under an
      // unrecognised heading would never get attached to any saved field.
      const matched = reverseLabel[nodeText(node).trim()];
      if (matched) {
        flush();
        currentField = matched;
      } else if (currentField && !isListField(currentField)) {
        const text = nodeText(node).trim();
        if (text) prose.push(text);
      }
    } else if (node.type === "paragraph") {
      const text = nodeText(node).trim();
      if (currentField && !isListField(currentField) && text) prose.push(text);
    } else if (node.type === "bulletList" || node.type === "orderedList") {
      for (const li of node.content ?? []) {
        const text = nodeText(li).trim();
        if (currentField && isListField(currentField) && text) list.push(text);
      }
    } else if (node.type === "codeBlock") {
      const text = nodeText(node).trim();
      if (currentField && !isListField(currentField) && text) prose.push(text);
    }
  }
  flush();
  return result;
}

const TOOLBAR_BTN =
  "flex h-7 w-7 items-center justify-center rounded transition disabled:opacity-30";

/* onMouseDown + preventDefault, not just onClick, is the standard fix for
 * the classic contentEditable-toolbar bug: a plain button click first
 * fires mousedown, which blurs the editor and collapses its selection
 * BEFORE the click handler runs — so by the time toggleBold()/etc. fires,
 * there's nothing valid to apply it to and the command silently no-ops.
 * Blocking mousedown's default keeps the editor focused and its selection
 * intact the whole time. */
function ToolbarButton({
  onClick, active, label, children,
}: {
  onClick: () => void;
  active?: boolean;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onMouseDown={(e) => e.preventDefault()}
      onClick={onClick}
      aria-label={label}
      className={`${TOOLBAR_BTN} ${active ? "bg-primary-50 text-primary" : "text-text-secondary hover:bg-surface-muted"}`}
    >
      {children}
    </button>
  );
}

const HEADING_OPTIONS: { label: string; level: 1 | 2 | 3 | null }[] = [
  { label: "Normal", level: null },
  { label: "H1", level: 1 },
  { label: "H2", level: 2 },
  { label: "H3", level: 3 },
];

/* A labeled "Heading 1 ⌄"-style dropdown instead of three bare icon
 * buttons — same three toggleHeading/setParagraph commands underneath,
 * just grouped into one ribbon control like a real document editor's
 * block-type picker. */
function HeadingDropdown({ editor }: { editor: Editor | null }) {
  const [open, setOpen] = useState(false);
  const current =
    HEADING_OPTIONS.find((o) => o.level && editor?.isActive("heading", { level: o.level }))?.label ?? "Normal";

  return (
    <div className="relative">
      <button
        type="button"
        onMouseDown={(e) => e.preventDefault()}
        onClick={() => setOpen((v) => !v)}
        className="flex h-7 items-center gap-1 rounded px-2 text-xs font-medium text-text-secondary transition hover:bg-surface-muted"
      >
        {current}
        <ChevronDown className="h-3 w-3" />
      </button>
      {open && (
        <div className="absolute left-0 top-full z-20 mt-1 w-24 rounded-lg border border-border-light bg-surface py-1 shadow-lg">
          {HEADING_OPTIONS.map((o) => (
            <button
              key={o.label}
              type="button"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => {
                if (o.level === null) editor?.chain().focus().setParagraph().run();
                else editor?.chain().focus().toggleHeading({ level: o.level }).run();
                setOpen(false);
              }}
              className={`block w-full px-3 py-1.5 text-left text-xs transition hover:bg-surface-muted ${
                current === o.label ? "text-primary" : "text-text-primary"
              }`}
            >
              {o.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function DocumentEditor({
  content,
  editable,
  onSave,
  isFavorite,
  onToggleFavorite,
  onDuplicate,
  showHeader = true,
}: {
  content: Record<string, unknown>;
  editable: boolean;
  onSave: (patch: Record<string, unknown>) => Promise<void>;
  isFavorite?: boolean;
  onToggleFavorite?: () => void;
  onDuplicate?: () => void;
  showHeader?: boolean;
}) {
  const t = useT();
  const lk = langKey(typeof content.language === "string" ? content.language : undefined);
  const [title, setTitle] = useState(typeof content.title === "string" ? content.title : "");
  const [subtitle, setSubtitle] = useState(typeof content.subtitle === "string" ? content.subtitle : "");
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved">("idle");
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const skipNextLoad = useRef(false);

  const editor = useEditor({
    extensions: [
      StarterKit,
      InlineMath,
      Underline,
      TextAlign.configure({ types: ["heading", "paragraph"] }),
      Link.configure({ openOnClick: false }),
      TextStyle,
      Color,
      Highlight.configure({ multicolor: false }),
    ],
    content: buildInitialHtml(content, lk),
    editable,
    immediatelyRender: false,
    editorProps: {
      attributes: {
        class: "prose-doc focus:outline-none",
      },
    },
    onUpdate: () => scheduleSave(),
  });

  function scheduleSave() {
    if (!editable) return;
    setSaveState("saving");
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(doSave, 1200);
  }

  async function doSave() {
    if (!editor) return;
    const parsed = parseDocToFields(editor.getJSON(), lk);
    const patch: Record<string, unknown> = { title, subtitle, ...parsed };
    // Any known field with no heading left in the doc means the user
    // deleted that whole section on purpose — clear it rather than leaving
    // a stale value the editor no longer shows.
    for (const key of [...LIST_FIELDS, ...PROSE_FIELDS]) {
      if (!(key in parsed)) patch[key] = isListField(key) ? [] : "";
    }
    skipNextLoad.current = true;
    await onSave(patch);
    setSaveState("saved");
  }

  // Reload the editor's document only when switching to genuinely different
  // content (a different material, or an undo/chat-edit from elsewhere) —
  // not after our own save round-trips back through props.
  useEffect(() => {
    if (skipNextLoad.current) {
      skipNextLoad.current = false;
      return;
    }
    if (!editor) return;
    // The editor is an external TipTap instance; these values mirror its
    // loaded document when the material changes.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTitle(typeof content.title === "string" ? content.title : "");
    setSubtitle(typeof content.subtitle === "string" ? content.subtitle : "");
    editor.commands.setContent(buildInitialHtml(content, lk));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(content), editor]);

  useEffect(() => () => {
    if (saveTimer.current) clearTimeout(saveTimer.current);
  }, []);

  const visualBlocks = Array.isArray(content.visual_blocks) ? (content.visual_blocks as VisualBlock[]) : [];
  const lessonStages = Array.isArray(content.lesson_stages) ? (content.lesson_stages as { minutes?: number; stage?: string; activity?: string }[]) : [];
  const quickCheck = Array.isArray(content.quick_check) ? (content.quick_check as { question?: string; answer?: string }[]) : [];
  const formulas = Array.isArray(content.formulas) ? (content.formulas as { formula?: string; explanation?: string }[]) : [];
  const conceptCards = Array.isArray(content.concept_cards) ? (content.concept_cards as { title?: string; tag?: string; table?: string[][]; note?: string }[]) : [];
  const codeBlocks = Array.isArray(content.code_blocks) ? (content.code_blocks as { language?: string; code?: string; explanation?: string }[]) : [];
  const workedExamples = Array.isArray(content.worked_examples) ? (content.worked_examples as Record<string, unknown>[]) : [];

  return (
    <div className="workspace-paper overflow-hidden rounded-[4px]">
      {editable && showHeader && (
        <div className="workspace-toolbar sticky top-0 z-20 flex items-center justify-between gap-3 px-4 py-2.5">
          <p className="min-w-0 truncate text-sm font-semibold text-text-secondary">{title || "—"}</p>
          <div className="flex shrink-0 items-center gap-0.5">
            {onToggleFavorite && (
              <ToolbarButton label="Bookmark" active={isFavorite} onClick={onToggleFavorite}>
                <Bookmark className="h-3.5 w-3.5" />
              </ToolbarButton>
            )}
            <ToolbarButton label="Print" onClick={() => window.print()}>
              <Printer className="h-3.5 w-3.5" />
            </ToolbarButton>
            {onDuplicate && (
              <ToolbarButton label="Duplicate" onClick={onDuplicate}>
                <Copy className="h-3.5 w-3.5" />
              </ToolbarButton>
            )}
          </div>
        </div>
      )}

      {editable && (
        <div className={`workspace-toolbar sticky ${showHeader ? "top-[2.65rem]" : "top-0"} z-10 flex flex-wrap items-center gap-1 border-b px-4 py-2`}>
          <ToolbarButton label="Undo" onClick={() => editor?.chain().focus().undo().run()}>
            <Undo2 className="h-3.5 w-3.5" />
          </ToolbarButton>
          <ToolbarButton label="Redo" onClick={() => editor?.chain().focus().redo().run()}>
            <Redo2 className="h-3.5 w-3.5" />
          </ToolbarButton>
          <span className="mx-1 h-4 w-px bg-border-light" />
          <HeadingDropdown editor={editor} />
          <span className="mx-1 h-4 w-px bg-border-light" />
          <ToolbarButton label="Bold" active={editor?.isActive("bold")} onClick={() => editor?.chain().focus().toggleBold().run()}>
            <Bold className="h-3.5 w-3.5" />
          </ToolbarButton>
          <ToolbarButton label="Italic" active={editor?.isActive("italic")} onClick={() => editor?.chain().focus().toggleItalic().run()}>
            <Italic className="h-3.5 w-3.5" />
          </ToolbarButton>
          <ToolbarButton label="Underline" active={editor?.isActive("underline")} onClick={() => editor?.chain().focus().toggleUnderline().run()}>
            <UnderlineIcon className="h-3.5 w-3.5" />
          </ToolbarButton>
          <ToolbarButton label="Strikethrough" active={editor?.isActive("strike")} onClick={() => editor?.chain().focus().toggleStrike().run()}>
            <Strikethrough className="h-3.5 w-3.5" />
          </ToolbarButton>
          <span className="mx-1 h-4 w-px bg-border-light" />
          <ToolbarButton label="Bullet list" active={editor?.isActive("bulletList")} onClick={() => editor?.chain().focus().toggleBulletList().run()}>
            <List className="h-3.5 w-3.5" />
          </ToolbarButton>
          <ToolbarButton label="Ordered list" active={editor?.isActive("orderedList")} onClick={() => editor?.chain().focus().toggleOrderedList().run()}>
            <ListOrdered className="h-3.5 w-3.5" />
          </ToolbarButton>
          <ToolbarButton label="Decrease indent" onClick={() => editor?.chain().focus().liftListItem("listItem").run()}>
            <IndentDecrease className="h-3.5 w-3.5" />
          </ToolbarButton>
          <ToolbarButton label="Increase indent" onClick={() => editor?.chain().focus().sinkListItem("listItem").run()}>
            <IndentIncrease className="h-3.5 w-3.5" />
          </ToolbarButton>
          <span className="mx-1 h-4 w-px bg-border-light" />
          <label className={`${TOOLBAR_BTN} relative cursor-pointer text-text-secondary hover:bg-surface-muted`} aria-label="Text color">
            <Palette className="h-3.5 w-3.5" />
            <input
              type="color"
              className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
              onMouseDown={(e) => e.stopPropagation()}
              onChange={(e) => editor?.chain().focus().setColor(e.target.value).run()}
            />
          </label>
          <ToolbarButton label="Highlight" active={editor?.isActive("highlight")} onClick={() => editor?.chain().focus().toggleHighlight().run()}>
            <Highlighter className="h-3.5 w-3.5" />
          </ToolbarButton>
          <span className="mx-1 h-4 w-px bg-border-light" />
          <ToolbarButton label="Align left" active={editor?.isActive({ textAlign: "left" })} onClick={() => editor?.chain().focus().setTextAlign("left").run()}>
            <AlignLeft className="h-3.5 w-3.5" />
          </ToolbarButton>
          <ToolbarButton label="Align center" active={editor?.isActive({ textAlign: "center" })} onClick={() => editor?.chain().focus().setTextAlign("center").run()}>
            <AlignCenter className="h-3.5 w-3.5" />
          </ToolbarButton>
          <ToolbarButton label="Align right" active={editor?.isActive({ textAlign: "right" })} onClick={() => editor?.chain().focus().setTextAlign("right").run()}>
            <AlignRight className="h-3.5 w-3.5" />
          </ToolbarButton>
          <ToolbarButton
            label="Link"
            active={editor?.isActive("link")}
            onClick={() => {
              if (!editor) return;
              if (editor.isActive("link")) {
                editor.chain().focus().unsetLink().run();
                return;
              }
              const url = window.prompt("URL");
              if (url) editor.chain().focus().setLink({ href: url }).run();
            }}
          >
            <LinkIcon className="h-3.5 w-3.5" />
          </ToolbarButton>

          <span className="ml-auto flex items-center gap-1.5 text-xs text-text-tertiary">
            {saveState === "saving" && (<><Loader2 className="h-3 w-3 animate-spin" />{t("material.saving")}</>)}
            {saveState === "saved" && t("material.saved")}
          </span>
        </div>
      )}

      {editable && (
        <div
          className={`document-ruler sticky ${showHeader ? "top-[5.15rem]" : "top-[2.6rem]"} z-[5] hidden h-5 select-none items-end gap-0 overflow-hidden border-b border-border-light bg-slate-50 px-4 text-[8px] leading-none text-text-tertiary sm:flex`}
          aria-hidden
        >
          {Array.from({ length: 24 }).map((_, i) => (
            <span key={i} className="flex-1 border-l border-border-light/70 pb-0.5 pl-0.5">
              {i + 1}
            </span>
          ))}
        </div>
      )}

      <div className="px-1 py-6 sm:px-2 sm:py-8">
        <input
          value={title}
          onChange={(e) => { setTitle(e.target.value); scheduleSave(); }}
          readOnly={!editable}
          className="mb-1 w-full border-none bg-transparent text-2xl font-bold text-text-primary outline-none"
        />
        {(subtitle || editable) && (
          <input
            value={subtitle}
            onChange={(e) => { setSubtitle(e.target.value); scheduleSave(); }}
            readOnly={!editable}
            placeholder={editable ? "—" : undefined}
            className="mb-4 w-full border-none bg-transparent text-sm text-text-secondary outline-none placeholder:text-text-tertiary"
          />
        )}
        {typeof content.duration === "string" && content.duration && (
          <p className="mb-6 text-xs text-text-tertiary">{content.duration}</p>
        )}

        <div className="document-editor-body">
          <EditorContent editor={editor} />
        </div>

        {(visualBlocks.length > 0 || lessonStages.length > 0 || quickCheck.length > 0 || formulas.length > 0 || conceptCards.length > 0 || codeBlocks.length > 0 || workedExamples.length > 0) && (
          <div className="document-structured-content mt-8 space-y-7">
            {lessonStages.length > 0 && (
              <section>
                <h2 className="mb-2 text-sm font-bold text-text-primary">{STRUCTURED_LABELS.lesson_stages[lk]}</h2>
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse text-sm">
                    <thead>
                      <tr>
                        {LESSON_STAGE_HEADERS[lk].map((header) => <th key={header}>{header}</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      {lessonStages.map((s, i) => (
                        <tr key={i}>
                          <td className="font-semibold"><MathText text={s.stage ?? ""} /></td>
                          <td className="whitespace-nowrap">{s.minutes != null ? `${s.minutes} мин` : ""}</td>
                          <td><MathText text={s.activity ?? ""} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            )}

            {formulas.length > 0 && (
              <section>
                <h2 className="mb-2 text-sm font-bold text-text-primary">{STRUCTURED_LABELS.formulas[lk]}</h2>
                <div className="space-y-1.5">
                  {formulas.map((f, i) => (
                    <p key={i} className="text-sm leading-relaxed">
                      <span className="rounded bg-surface-muted px-1.5 py-0.5 font-mono text-primary"><MathText text={f.formula ?? ""} /></span>
                      <span className="ml-2 text-text-secondary"><MathText text={f.explanation ?? ""} /></span>
                    </p>
                  ))}
                </div>
              </section>
            )}

            {conceptCards.length > 0 && (
              <section className="space-y-4">
                <h2 className="text-sm font-bold text-text-primary">{STRUCTURED_LABELS.concept_cards[lk]}</h2>
                {conceptCards.map((c, i) => (
                  <div key={i}>
                    <p className="mb-1 text-sm font-semibold text-text-primary"><MathText text={c.title ?? ""} /> {c.tag ? <span className="rounded bg-surface-muted px-1.5 py-0.5 font-mono text-primary">{c.tag}</span> : null}</p>
                    {Array.isArray(c.table) && c.table.length > 0 && (
                      <table className="my-2 w-full border-collapse text-xs">
                        <tbody>
                          {c.table.map((row, ri) => (
                            <tr key={ri}>
                              {row.map((cell, ci) => (
                                <td key={ci} className={`border-b border-border-light py-1 pr-3 ${ri === 0 ? "font-semibold text-text-primary" : "text-text-secondary"}`}><MathText text={cell ?? ""} /></td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                    {c.note && <p className="text-xs text-text-tertiary"><MathText text={c.note} /></p>}
                  </div>
                ))}
              </section>
            )}

            {codeBlocks.length > 0 && (
              <section className="space-y-4">
                <h2 className="text-sm font-bold text-text-primary">{STRUCTURED_LABELS.code_blocks[lk]}</h2>
                {codeBlocks.map((b, i) => (
                  <div key={i}>
                    <pre className="code-block overflow-x-auto rounded-lg bg-surface-muted p-3 text-xs text-text-primary"><code>{b.code}</code></pre>
                    {b.explanation && <p className="mt-1.5 text-xs text-text-secondary"><MathText text={b.explanation} /></p>}
                  </div>
                ))}
              </section>
            )}

            {quickCheck.length > 0 && (
              <section className="space-y-3">
                <h2 className="text-sm font-bold text-text-primary">{STRUCTURED_LABELS.quick_check[lk]}</h2>
                {quickCheck.map((q, i) => (
                  <p key={i} className="text-sm leading-relaxed">
                    <span className="font-medium text-text-primary"><MathText text={q.question ?? ""} /></span>
                    <span className="block text-text-secondary"><MathText text={q.answer ?? ""} /></span>
                  </p>
                ))}
              </section>
            )}

            {workedExamples.length > 0 && (
              <section className="space-y-2">
                <h2 className="text-sm font-bold text-text-primary">{STRUCTURED_LABELS.worked_examples[lk]}</h2>
                {workedExamples.map((w, i) => {
                  const values = ["problem", "solution", "answer", "explanation"]
                    .map((key) => w[key])
                    .filter((value): value is string => typeof value === "string" && value.trim().length > 0);
                  const parts: ExamplePart[] = values.flatMap(splitExampleValue);
                  const explicitCode = typeof w.code === "string" && w.code.trim() ? w.code.trim() : null;
                  if (explicitCode) parts.push({ kind: "code", value: explicitCode });
                  return (
                    <div key={i} className="space-y-2 border-b border-border-light pb-3 last:border-b-0">
                      {parts.map((part, partIndex) => part.kind === "code" ? (
                        <pre key={partIndex} className="overflow-x-auto whitespace-pre-wrap rounded-lg bg-slate-100 p-3 font-mono text-xs text-slate-800">
                          <code>{part.value}</code>
                        </pre>
                      ) : (
                        <p key={partIndex} className="whitespace-pre-wrap text-sm text-text-secondary"><MathText text={part.value} /></p>
                      ))}
                    </div>
                  );
                })}
              </section>
            )}

            {visualBlocks.map((block, i) => <VisualBlockRenderer key={i} block={block} />)}
          </div>
        )}
      </div>
    </div>
  );
}

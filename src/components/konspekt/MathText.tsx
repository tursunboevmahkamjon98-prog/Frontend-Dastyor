import katex from "katex";
import { stripLeakedExportMarkup } from "@/lib/sanitize-text";

/** Renders a string that may contain inline `$...$` LaTeX spans — the same
 * convention ai_service.py's konspekt prompt uses and export_builder.py's
 * `_math_inline` already converts for PDF/docx (see that function's
 * docstring). The web viewer never had an equivalent: every `$x+2=5$` span
 * was shown as literal text, dollar signs and all, instead of a typeset
 * formula. KaTeX renders client-side so this needs no server round-trip
 * (unlike the PDF path's rasterized/vector approach) — cheap enough to
 * call on every paragraph/cell that might contain math.
 *
 * `stripLeakedExportMarkup` still runs first: a handful of already-saved
 * documents have the PDF-only artifact baked into their text (see that
 * function's docstring) and this must not try to KaTeX-render `<img ...>`
 * as if it were math. */
export default function MathText({ text, className }: { text: string; className?: string }) {
  const clean = stripLeakedExportMarkup(text);
  if (!clean.includes("$")) return <>{clean}</>;

  // A fresh RegExp per call (not a shared module-level one) — a `g`-flagged
  // regex carries mutable `lastIndex` state, and reusing one instance
  // across renders/calls is exactly the kind of shared mutable state the
  // project's purity lint (react-hooks/immutability) flags, since this
  // component itself may run concurrently for many cells in one page.
  const mathSpan = /\$([^$]+)\$/g;
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let key = 0;
  while ((match = mathSpan.exec(clean))) {
    if (match.index > lastIndex) parts.push(clean.slice(lastIndex, match.index));
    const html = renderKatex(match[1]);
    parts.push(
      html ? (
        <span key={key++} className={className} dangerouslySetInnerHTML={{ __html: html }} />
      ) : (
        match[1] // unrenderable — show the expression without the dollars, same fallback as the PDF path
      )
    );
    lastIndex = mathSpan.lastIndex;
  }
  if (lastIndex < clean.length) parts.push(clean.slice(lastIndex));
  return <>{parts}</>;
}

function renderKatex(latex: string): string | null {
  try {
    return katex.renderToString(latex, { throwOnError: false, output: "html", displayMode: false });
  } catch {
    return null;
  }
}

import katex from "katex";
import { stripLeakedExportMarkup } from "@/lib/sanitize-text";


export default function MathText({ text, className }: { text: string; className?: string }) {
  const clean = stripLeakedExportMarkup(text);
  if (!clean.includes("$")) return <>{clean}</>;

  
  
  
  
  
  const mathSpan = /\$([^$]+)\$/g;
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let key = 0;
  while ((match = mathSpan.exec(clean))) {
    if (match.index > lastIndex) parts.push(clean.slice(lastIndex, match.index));
    const html = renderKatex(repairStackedSubscript(match[1]));
    parts.push(
      html ? (
        <span key={key++} className={className} dangerouslySetInnerHTML={{ __html: html }} />
      ) : (
        match[1] 
      )
    );
    lastIndex = mathSpan.lastIndex;
  }
  if (lastIndex < clean.length) parts.push(clean.slice(lastIndex));
  return <>{parts}</>;
}

// The model occasionally writes "P_{1V}_{1}" meaning "P with subscript 1,
// times V with subscript 1" -- it merges the next variable's letters into
// the first subscript group, then adds a second subscript right after.
// KaTeX rejects two stacked subscripts on one base ("Double subscript")
// outright, so without this the whole expression falls back to raw LaTeX
// text. Move the trailing letters out from between the two subscripts.
function repairStackedSubscript(latex: string): string {
  return latex.replace(/_\{(\d+)([A-Za-zА-Яа-яЁёҚқҒғҲҳҶҷӢӣ]+)\}(_\{)/g, "_{$1}$2$3");
}

function renderKatex(latex: string): string | null {
  try {
    return katex.renderToString(latex, { throwOnError: false, output: "html", displayMode: false });
  } catch {
    return null;
  }
}

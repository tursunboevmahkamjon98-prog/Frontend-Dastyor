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
    const html = renderKatex(match[1]);
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

function renderKatex(latex: string): string | null {
  try {
    return katex.renderToString(latex, { throwOnError: false, output: "html", displayMode: false });
  } catch {
    return null;
  }
}

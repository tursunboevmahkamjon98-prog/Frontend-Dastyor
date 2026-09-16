"use client";

import { useState } from "react";
import { Copy, Check } from "lucide-react";


export default function CodeBlock({
  code,
  language,
  explanation,
}: {
  code: string;
  language?: string;
  explanation?: string;
}) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      
      
    }
  }

  return (
    <div className="mb-5 overflow-hidden rounded-2xl border border-border-light">
      <div className="flex items-center justify-between bg-primary px-3.5 py-1.5">
        <span className="text-[10px] font-bold uppercase tracking-wide text-white">{language || "code"}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[10px] font-medium text-white/90 hover:bg-white/10"
        >
          {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
          {copied ? "Скопировано" : "Копировать"}
        </button>
      </div>
      <pre className="overflow-x-auto bg-[#1e293b] px-4 py-3">
        <code className="font-mono text-[13px] leading-relaxed whitespace-pre text-[#e2e8f0]">{code}</code>
      </pre>
      {explanation && (
        <p className="border-t border-border-light bg-surface px-4 py-2.5 text-xs italic text-text-secondary">
          {explanation}
        </p>
      )}
    </div>
  );
}

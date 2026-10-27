"use client";

import { useEffect, useState } from "react";
import { ExternalLink, Loader2 } from "lucide-react";
import { fetchMaterialExport, ExportBody, ApiError } from "@/lib/api";
import { useT } from "@/lib/i18n";


export default function PdfPreview({ body }: { body: ExportBody }) {
  const t = useT();
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | true | null>(null);

  
  
  
  
  const bodySnapshot = JSON.stringify(body);

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;
    fetchMaterialExport("pdf", JSON.parse(bodySnapshot) as ExportBody)
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : true);
      });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
    
  }, [bodySnapshot]);

  return (
    <div className="mb-6 overflow-hidden rounded-2xl border border-border-light bg-surface">
      <div className="flex items-center justify-end gap-2 border-b border-border-light px-3 py-2">
        <a
          href={url ?? undefined}
          target="_blank"
          rel="noreferrer"
          aria-disabled={!url}
          className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium transition ${
            url
              ? "text-text-secondary hover:bg-surface-muted hover:text-text-primary"
              : "pointer-events-none text-text-tertiary opacity-50"
          }`}
        >
          <ExternalLink className="h-3.5 w-3.5" />
          {t("material.openFull")}
        </a>
      </div>

      {error ? (
        <p className="px-4 py-10 text-center text-sm text-error">{error === true ? t("material.pdfFailed") : error}</p>
      ) : url ? (
        
        
        
        
        
        <iframe
          src={`${url}#toolbar=0&navpanes=0&scrollbar=0&view=FitH`}
          title="PDF"
          className="h-[78vh] w-full bg-white"
        />
      ) : (
        <p className="flex items-center justify-center gap-2 px-4 py-16 text-sm text-text-secondary">
          <Loader2 className="h-4 w-4 animate-spin" />
          {t("material.pdfPreparing")}
        </p>
      )}
    </div>
  );
}

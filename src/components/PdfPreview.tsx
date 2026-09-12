"use client";

import { useEffect, useState } from "react";
import { Download, ExternalLink, Loader2 } from "lucide-react";
import { fetchMaterialExport, downloadMaterial, ExportBody, ApiError } from "@/lib/api";
import { useT } from "@/lib/i18n";

/** Shows a material's real exported PDF inline, in the page, where the
 * teacher is already reading it — not behind a button in a modal.
 *
 * Renders the very bytes the download button produces (see
 * fetchMaterialExport) inside an <iframe> rather than re-drawing the
 * material JSON in HTML: a second HTML renderer would inevitably drift
 * from export_builder.py, and the whole point is to show exactly what is
 * about to be printed and handed out.
 *
 * The blob URL is created once the bytes arrive and revoked on unmount, so
 * a session that opens many materials doesn't leak one object URL per
 * view. */
export default function PdfPreview({ body }: { body: ExportBody }) {
  const t = useT();
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  // Re-fetches whenever the content actually changes (an AI edit or a
  // section regeneration), so the PDF on screen never lags the konspekt
  // it is supposed to be showing. Keyed on the serialised content rather
  // than the object, which is a new reference on every render.
  const contentKey = JSON.stringify(body.content);

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;
    setUrl(null);
    setError(null);

    fetchMaterialExport("pdf", body)
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : t("material.pdfFailed"));
      });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contentKey]);

  async function handleDownload() {
    setDownloading(true);
    try {
      await downloadMaterial("pdf", body);
    } catch {
      // The preview is already on screen; a failed save is self-evident.
    } finally {
      setDownloading(false);
    }
  }

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
        <button
          onClick={handleDownload}
          disabled={!url || downloading}
          className="flex items-center gap-1.5 rounded-lg bg-surface-muted px-2.5 py-1.5 text-xs font-medium text-text-primary transition hover:bg-primary-50 disabled:opacity-50"
        >
          {downloading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
          {t("material.download")}
        </button>
      </div>

      {error ? (
        <p className="px-4 py-10 text-center text-sm text-primary-dark">{error}</p>
      ) : url ? (
        // #toolbar=0&navpanes=0 strips the browser's own PDF chrome — the
        // dark control strip and the thumbnail sidebar — so what shows is
        // just the pages themselves. Its zoom/print/download controls are
        // redundant here anyway: this panel has its own download and
        // open-full-screen buttons above.
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

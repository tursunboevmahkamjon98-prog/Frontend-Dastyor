/** Strips a legacy artifact from konspekt content: `_math_inline` in
 * backend/app/export_builder.py rewrites inline `$formula$` spans into a
 * ReportLab-only `<img src="C:\...\uploads\math\....png" width="..."
 * height="..." valign="..."/>` tag — meant to live only inside a transient
 * PDF-build Paragraph string, never in the stored `content` JSON that this
 * web viewer also reads. A handful of already-generated documents ended up
 * with that tag literally saved as their cell/paragraph text (from an
 * older build where the path bug let it leak into the persisted content),
 * so it shows up as raw text instead of the formula it was standing in
 * for. Stripping it here fixes every existing affected document without a
 * data migration, and guards the web view if the same mistake recurs. */
const REPORTLAB_IMG_TAG = /<img\s+src="[^"]*"[^>]*\/?>/gi;

export function stripLeakedExportMarkup(text: string): string {
  return text.includes("<img") ? text.replace(REPORTLAB_IMG_TAG, "").replace(/\s{2,}/g, " ").trim() : text;
}

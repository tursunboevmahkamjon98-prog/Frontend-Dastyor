
const REPORTLAB_IMG_TAG = /<img\s+src="[^"]*"[^>]*\/?>/gi;

export function stripLeakedExportMarkup(text: string): string {
  return text.includes("<img") ? text.replace(REPORTLAB_IMG_TAG, "").replace(/\s{2,}/g, " ").trim() : text;
}

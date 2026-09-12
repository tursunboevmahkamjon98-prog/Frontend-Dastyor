import MathText from "./MathText";

/** A single "pay attention" callout for a konspekt's `important_notes`
 * entries — visually distinct from a regular bullet (left accent bar +
 * tinted background) so it reads as a genuine highlight, matching the
 * same treatment given to it in the docx/pdf exports (see
 * docx_builder.py's _add_important_note / export_builder.py's
 * _pdf_important_note). */
export default function ImportantNoteCard({ text }: { text: string }) {
  return (
    <div className="mb-3 flex items-start gap-2.5 rounded-xl border-l-[3px] border-primary bg-primary-50 px-3.5 py-2.5">
      <span className="mt-0.5 shrink-0 text-primary" aria-hidden>
        ☝️
      </span>
      <p className="text-sm italic leading-relaxed text-primary-dark">
        <MathText text={text} />
      </p>
    </div>
  );
}

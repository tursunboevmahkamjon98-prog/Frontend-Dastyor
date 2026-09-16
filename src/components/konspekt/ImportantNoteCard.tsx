import MathText from "./MathText";


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

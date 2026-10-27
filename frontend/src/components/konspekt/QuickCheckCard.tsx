
import MathText from "./MathText";

export default function QuickCheckCard({ question, answer }: { question: string; answer?: string }) {
  return (
    <div className="mb-3 overflow-hidden rounded-xl border-l-[3px] border-success bg-success/10 px-3.5 py-2.5">
      <p className="flex items-start gap-2 text-sm text-text-primary">
        <span className="mt-0.5 shrink-0 font-bold text-success" aria-hidden>
          ?
        </span>
        <span>
          <MathText text={question} />
        </span>
      </p>
      {answer && (
        <p className="mt-1.5 pl-5 text-sm italic text-success">
          Ответ: <MathText text={answer} />
        </p>
      )}
    </div>
  );
}

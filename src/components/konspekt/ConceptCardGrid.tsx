import MathText from "./MathText";

/** Renders `formulas` and `concept_cards` — the two subject-specific
 * "Расмхо" (reference cards) fields ai_service.py's _konspekt_prompt
 * requests for STEM subjects / Информатика (see _FORMULA_SUBJECTS /
 * _CONCEPT_CARD_SUBJECTS). These already rendered in the docx/pdf exports
 * (docx_builder.py's _add_formula_card / _add_concept_card_grid) but were
 * never shown on the web viewer at all — this is that missing piece,
 * matching the same look: a colored-header card grid over a light body
 * holding a small reference table and/or note. */

interface Formula {
  formula: string;
  explanation?: string;
}

interface ConceptCard {
  title: string;
  tag?: string;
  table?: string[][];
  formula?: string;
  note?: string;
}

export function FormulaCards({ formulas }: { formulas: (Formula | string)[] }) {
  if (!formulas || formulas.length === 0) return null;
  return (
    <div className="mb-5 space-y-3">
      {formulas.map((f, i) => {
        const formula = typeof f === "string" ? f : f.formula;
        const explanation = typeof f === "string" ? "" : f.explanation;
        return (
          <div key={i} className="rounded-xl border border-border-light bg-surface-muted px-4 py-3 text-center">
            <p className="font-serif text-lg font-bold text-primary">
              <MathText text={formula} />
            </p>
            {explanation && (
              <p className="mt-1 text-xs italic text-text-secondary">
                <MathText text={explanation} />
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}

export function ConceptCardGrid({ cards }: { cards: ConceptCard[] }) {
  if (!cards || cards.length === 0) return null;
  // An odd count left the last card alone in its own row, filling only the
  // left column and leaving a blank gap on the right — spans it across
  // both columns instead so the grid never ends on a lopsided half-empty row.
  const isOddLast = (i: number) => cards.length % 2 === 1 && i === cards.length - 1;
  return (
    <div className="mb-5 grid grid-cols-1 gap-3 sm:grid-cols-2">
      {cards.map((card, i) => (
        <div key={i} className={`overflow-hidden rounded-xl border border-border-light ${isOddLast(i) ? "sm:col-span-2" : ""}`}>
          <div className="bg-primary px-3 py-2 text-center">
            <p className="text-sm font-bold text-white">{card.title}</p>
            {card.tag && <p className="text-xs italic text-white/80">{card.tag}</p>}
          </div>
          <div className="bg-surface-muted p-3">
            {card.table && card.table.length > 0 && (
              <table className="w-full border-collapse text-center text-xs">
                <tbody>
                  {card.table.map((row, ri) => (
                    <tr key={ri}>
                      {row.map((cell, ci) => (
                        <td
                          key={ci}
                          className={`border border-border-light px-2 py-1 ${
                            ri === 0 ? "bg-border-light font-semibold text-text-primary" : "text-text-secondary"
                          }`}
                        >
                          <MathText text={cell} />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {card.formula && (
              <p className="mt-2 text-center font-serif font-bold text-primary">
                <MathText text={card.formula} />
              </p>
            )}
            {card.note && (
              <p className="mt-2 text-center text-xs italic text-text-secondary">
                <MathText text={card.note} />
              </p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

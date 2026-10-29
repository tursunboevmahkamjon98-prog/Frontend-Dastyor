import { ReactNode } from "react";

/* The three auth pages were each carrying their own copy of these strings.
 * One definition means a change to the input focus ring or the button's
 * disabled state lands everywhere instead of in whichever file was edited. */
export const inputClass =
  "min-h-12 w-full rounded-[1rem] border border-border bg-surface px-4 py-3 text-body text-text-primary shadow-[inset_0_2px_4px_rgba(40,30,28,0.035)] outline-none transition-[border-color,box-shadow] duration-150 placeholder:text-text-tertiary focus:border-primary focus:ring-4 focus:ring-primary/10";

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-meta font-medium text-text-secondary">{label}</span>
      {children}
    </label>
  );
}

export function SubmitButton({
  children,
  disabled,
}: {
  children: ReactNode;
  disabled?: boolean;
}) {
  return (
    <button
      type="submit"
      disabled={disabled}
      className="min-h-[3.25rem] w-full rounded-[1rem] bg-primary px-5 py-3 text-body font-semibold text-white shadow-[0_8px_18px_rgba(225,29,46,0.22),inset_0_1px_0_rgba(255,255,255,0.22)] transition-[background-color,box-shadow] duration-150 hover:bg-primary-dark hover:shadow-[0_10px_22px_rgba(184,18,31,0.24)] disabled:pointer-events-none disabled:opacity-50"
    >
      {children}
    </button>
  );
}

/* Errors use the dedicated --color-error token rather than the brand. They
 * used to be drawn in brand red, which only read as "error" while the brand
 * happened to be red too. */
export function ErrorNote({ children }: { children: ReactNode }) {
  return (
    <p role="alert" className="mb-4 rounded-control border border-error/30 bg-error/10 px-3.5 py-2.5 text-meta text-error">
      {children}
    </p>
  );
}

export function AuthHeading({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="mb-6">
      <span className="mb-3 block h-1.5 w-10 rounded-full bg-primary shadow-[0_2px_5px_rgba(225,29,46,0.25)]" aria-hidden="true" />
      <h1 className="text-[1.8rem] font-semibold leading-tight tracking-[-0.025em] text-text-primary">{title}</h1>
      <p className="mt-2 text-body leading-relaxed text-text-secondary">{subtitle}</p>
    </div>
  );
}

export function AuthCard({ children }: { children: ReactNode }) {
  return (
    <div className="relative rounded-[1.6rem] border border-border-light bg-surface p-5 shadow-[0_18px_48px_rgba(85,45,42,0.09),0_3px_10px_rgba(85,45,42,0.04),inset_0_1px_0_white] sm:p-7">{children}</div>
  );
}

/* Small coloured step circle, shared by any numbered flow (currently just
 * the book-upload wizard) instead of each screen re-typing its own
 * "01 ·" text marker. */
export function StepBadge({ n, small = false }: { n: number; small?: boolean }) {
  return (
    <span
      className={`flex shrink-0 items-center justify-center rounded-full bg-secondary font-bold tabular-nums text-white ${small ? "h-5 w-5 text-[10px]" : "h-7 w-7 text-xs"}`}
    >
      {n}
    </span>
  );
}

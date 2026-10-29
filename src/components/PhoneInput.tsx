"use client";


export default function PhoneInput({
  value,
  onChange,
  autoFocus,
}: {
  value: string;
  onChange: (digits: string) => void;
  autoFocus?: boolean;
}) {
  return (
    <div className="flex overflow-hidden rounded-xl border border-border bg-white shadow-[inset_0_2px_3px_rgba(0,0,0,0.04)] transition focus-within:border-primary focus-within:ring-4 focus-within:ring-primary/10">
      <span className="flex items-center border-r border-border-light bg-surface-muted px-3.5 text-sm font-medium text-text-secondary">
        +992
      </span>
      <input
        type="tel"
        inputMode="numeric"
        required
        autoFocus={autoFocus}
        maxLength={9}
        value={value}
        onChange={(e) => onChange(e.target.value.replace(/\D/g, "").slice(0, 9))}
        className="w-full min-w-0 flex-1 bg-transparent px-3.5 py-2.5 text-sm text-text-primary outline-none"
        placeholder="938887766"
      />
    </div>
  );
}

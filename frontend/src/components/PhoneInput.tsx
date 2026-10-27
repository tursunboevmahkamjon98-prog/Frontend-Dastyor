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
    <div className="flex min-h-12 overflow-hidden rounded-[1rem] border border-border bg-surface shadow-[inset_0_2px_4px_rgba(40,30,28,0.035)] transition-colors duration-150 focus-within:border-primary focus-within:ring-4 focus-within:ring-primary/10">
      <span className="flex items-center border-r border-border-light bg-surface-muted px-3.5 text-body font-medium text-text-secondary">
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
        className="w-full min-w-0 flex-1 bg-transparent px-3.5 py-2.5 text-body text-text-primary outline-none placeholder:text-text-tertiary"
        placeholder="938887766"
      />
    </div>
  );
}

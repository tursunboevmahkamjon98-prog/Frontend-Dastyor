"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/lib/theme";
import { useT } from "@/lib/i18n";

export default function ThemeToggle({ className = "" }: { className?: string }) {
  const { theme, toggleTheme } = useTheme();
  const t = useT();
  const Icon = theme === "dark" ? Sun : Moon;

  return (
    <button
      type="button"
      onClick={toggleTheme}
      title={t("theme.toggle")}
      aria-label={t("theme.toggle")}
      className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-text-secondary transition hover:bg-surface-muted hover:text-text-primary ${className}`}
    >
      <Icon className="h-4.5 w-4.5" />
    </button>
  );
}

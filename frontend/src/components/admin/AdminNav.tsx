"use client";

import Link from "next/link";

// Deliberately plain (matches today's admin console) — a full branded
// sidebar needs shadcn/ui and globals.css changes this feature avoids
// touching for now. Each CRM page includes this at the top.
const LINKS: { href: string; label: string }[] = [
  { href: "/admin", label: "Консоль" },
  { href: "/admin/overview", label: "Обзор" },
  { href: "/admin/payments", label: "Платежи" },
  { href: "/admin/balance", label: "Баланс" },
  { href: "/admin/cards", label: "Карты" },
  { href: "/admin/expenses", label: "Расходы" },
  { href: "/admin/reports", label: "Отчёты" },
  { href: "/admin/roles", label: "Администраторы" },
  { href: "/admin/audit", label: "Журнал" },
];

export default function AdminNav() {
  return (
    <nav style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 16, font: "13px/1.4 system-ui, sans-serif" }}>
      {LINKS.map((l) => (
        <Link key={l.href} href={l.href} style={{ textDecoration: "underline" }}>
          {l.label}
        </Link>
      ))}
    </nav>
  );
}

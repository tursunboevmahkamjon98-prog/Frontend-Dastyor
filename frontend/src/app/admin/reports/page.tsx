"use client";

import { useEffect, useState } from "react";
import AdminNav from "@/components/admin/AdminNav";
import { ApiError } from "@/lib/api";
import { ledgerApi, expensesApi, type BalanceTransactionOut, type ExpenseOut } from "@/lib/admin-crm-api";

const tile: React.CSSProperties = { border: "1px solid #e5e5e5", borderRadius: 8, padding: 16, minWidth: 180, flex: "1 1 180px" };
const tileValue: React.CSSProperties = { fontSize: 24, fontWeight: 700 };
const btn: React.CSSProperties = { padding: "6px 14px", borderRadius: 4, border: "1px solid #d1d5db", background: "#fff", cursor: "pointer" };

function toCsv(rows: Record<string, unknown>[]): string {
  if (rows.length === 0) return "";
  const headers = Object.keys(rows[0]);
  const lines = [headers.join(",")];
  for (const r of rows) {
    lines.push(headers.map((h) => JSON.stringify(r[h] ?? "")).join(","));
  }
  return lines.join("\n");
}

function download(filename: string, content: string) {
  const blob = new Blob([content], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function AdminReportsPage() {
  const [topups, setTopups] = useState<BalanceTransactionOut[] | null>(null);
  const [expenses, setExpenses] = useState<ExpenseOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    ledgerApi.listTransactions({ kind: "topup", limit: 500 }).then(setTopups).catch((e) => setError(e instanceof ApiError ? e.message : "Ошибка"));
    expensesApi.list().then(setExpenses).catch((e) => setError(e instanceof ApiError ? e.message : "Ошибка"));
  }, []);

  const topupsTotal = topups?.reduce((s, t) => s + t.amount_somoni, 0) ?? null;
  const expensesTotal = expenses?.reduce((s, e) => s + e.amount_somoni, 0) ?? null;
  const net = topupsTotal != null && expensesTotal != null ? topupsTotal - expensesTotal : null;

  return (
    <div style={{ font: "13px/1.5 system-ui, sans-serif" }}>
      <AdminNav />
      <h1 style={{ fontSize: 18, fontWeight: 700, marginBottom: 12 }}>Отчёты</h1>
      {error && <div style={{ color: "#991b1b", marginBottom: 12 }}>{error}</div>}

      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 16 }}>
        <div style={tile}>
          <div style={{ ...tileValue, color: "#059669" }}>{topupsTotal != null ? topupsTotal.toFixed(2) : "…"}</div>
          <div>Подтверждённые пополнения (сомони)</div>
        </div>
        <div style={tile}>
          <div style={{ ...tileValue, color: "#b91c1c" }}>{expensesTotal != null ? expensesTotal.toFixed(2) : "…"}</div>
          <div>Расходы (сомони)</div>
        </div>
        <div style={tile}>
          <div style={tileValue}>{net != null ? net.toFixed(2) : "…"}</div>
          <div>Чистая разница за всё время</div>
        </div>
      </div>
      <p style={{ color: "#9ca3af", fontSize: 12, marginBottom: 16 }}>
        Это не окончательная чистая прибыль: сюда пока не входят расходы на AI/сервер, если они не внесены на странице «Расходы».
      </p>

      <div style={{ display: "flex", gap: 8 }}>
        <button style={btn} disabled={!topups} onClick={() => topups && download("topups.csv", toCsv(topups as unknown as Record<string, unknown>[]))}>
          Экспорт пополнений (CSV)
        </button>
        <button style={btn} disabled={!expenses} onClick={() => expenses && download("expenses.csv", toCsv(expenses as unknown as Record<string, unknown>[]))}>
          Экспорт расходов (CSV)
        </button>
      </div>
    </div>
  );
}

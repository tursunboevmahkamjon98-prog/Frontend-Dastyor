"use client";

import { useCallback, useEffect, useState } from "react";
import AdminNav from "@/components/admin/AdminNav";
import { ApiError } from "@/lib/api";
import { expensesApi, type ExpenseOut } from "@/lib/admin-crm-api";

const cell: React.CSSProperties = { border: "1px solid #e5e5e5", padding: "6px 10px" };
const head: React.CSSProperties = { ...cell, background: "#f3f4f6", textAlign: "left", fontWeight: 600 };
const input: React.CSSProperties = { border: "1px solid #d1d5db", borderRadius: 4, padding: "4px 8px", marginRight: 6 };
const btnPrimary: React.CSSProperties = { padding: "6px 14px", borderRadius: 4, border: "1px solid #e11d2e", background: "#e11d2e", color: "#fff", cursor: "pointer" };

export default function AdminExpensesPage() {
  const [rows, setRows] = useState<ExpenseOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({ category: "", amount_somoni: "", note: "" });
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    setError(null);
    expensesApi.list().then(setRows).catch((e) => setError(e instanceof ApiError ? e.message : "Ошибка"));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function createExpense() {
    const amount = parseFloat(form.amount_somoni);
    if (!form.category || !amount || amount <= 0) return;
    setBusy(true);
    setError(null);
    try {
      await expensesApi.create({
        category: form.category,
        amount_somoni: amount,
        note: form.note || undefined,
        spent_at: new Date().toISOString(),
      });
      setForm({ category: "", amount_somoni: "", note: "" });
      load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Ошибка создания");
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    if (!confirm("Удалить расход?")) return;
    try {
      await expensesApi.remove(id);
      load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Ошибка удаления");
    }
  }

  const total = rows?.reduce((s, r) => s + r.amount_somoni, 0) ?? 0;

  return (
    <div style={{ font: "13px/1.5 system-ui, sans-serif" }}>
      <AdminNav />
      <h1 style={{ fontSize: 18, fontWeight: 700, marginBottom: 12 }}>Расходы</h1>
      {error && <div style={{ color: "#991b1b", marginBottom: 12 }}>{error}</div>}

      <div style={{ marginBottom: 16, padding: 12, border: "1px solid #e5e5e5", borderRadius: 8 }}>
        <input style={input} placeholder="Категория" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} />
        <input style={input} placeholder="Сумма (сомони)" value={form.amount_somoni} onChange={(e) => setForm({ ...form, amount_somoni: e.target.value })} />
        <input style={input} placeholder="Примечание" value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} />
        <button style={btnPrimary} disabled={busy} onClick={createExpense}>Добавить расход</button>
      </div>

      {!rows && !error && <div>Загрузка...</div>}
      {rows && rows.length === 0 && <p style={{ color: "#6b7280" }}>Нет расходов.</p>}
      {rows && rows.length > 0 && (
        <>
          <p style={{ marginBottom: 8, fontWeight: 600 }}>Итого: {total.toFixed(2)} сомони</p>
          <table style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                <th style={head}>Категория</th>
                <th style={head}>Сумма</th>
                <th style={head}>Примечание</th>
                <th style={head}>Дата</th>
                <th style={head}></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td style={cell}>{r.category}</td>
                  <td style={cell}>{r.amount_somoni.toFixed(2)}</td>
                  <td style={cell}>{r.note ?? "—"}</td>
                  <td style={cell}>{new Date(r.spent_at).toLocaleDateString("ru-RU")}</td>
                  <td style={cell}>
                    <button style={{ ...input, cursor: "pointer" }} onClick={() => remove(r.id)}>Удалить</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}

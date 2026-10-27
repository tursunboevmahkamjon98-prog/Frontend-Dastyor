"use client";

import { useCallback, useEffect, useState } from "react";
import AdminNav from "@/components/admin/AdminNav";
import { ApiError } from "@/lib/api";
import { cardsApi, type CardOut } from "@/lib/admin-crm-api";

const cell: React.CSSProperties = { border: "1px solid #e5e5e5", padding: "6px 10px" };
const head: React.CSSProperties = { ...cell, background: "#f3f4f6", textAlign: "left", fontWeight: 600 };
const input: React.CSSProperties = { border: "1px solid #d1d5db", borderRadius: 4, padding: "4px 8px", marginRight: 6 };
const btnPrimary: React.CSSProperties = { padding: "6px 14px", borderRadius: 4, border: "1px solid #e11d2e", background: "#e11d2e", color: "#fff", cursor: "pointer" };

export default function AdminCardsPage() {
  const [rows, setRows] = useState<CardOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({ bank_name: "", holder_name: "", card_number: "", note: "" });
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    setError(null);
    cardsApi.list().then(setRows).catch((e) => setError(e instanceof ApiError ? e.message : "Ошибка"));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function createCard() {
    if (!form.bank_name || !form.holder_name || !form.card_number) return;
    setBusy(true);
    setError(null);
    try {
      await cardsApi.create(form);
      setForm({ bank_name: "", holder_name: "", card_number: "", note: "" });
      load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Ошибка создания");
    } finally {
      setBusy(false);
    }
  }

  async function toggleActive(c: CardOut) {
    try {
      await cardsApi.update(c.id, { is_active: !c.is_active });
      load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Ошибка");
    }
  }

  async function remove(c: CardOut) {
    if (!confirm(`Удалить карту ${c.bank_name}?`)) return;
    try {
      await cardsApi.remove(c.id);
      load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Ошибка удаления");
    }
  }

  return (
    <div style={{ font: "13px/1.5 system-ui, sans-serif" }}>
      <AdminNav />
      <h1 style={{ fontSize: 18, fontWeight: 700, marginBottom: 12 }}>Карты и реквизиты</h1>
      {error && <div style={{ color: "#991b1b", marginBottom: 12 }}>{error}</div>}

      <div style={{ marginBottom: 16, padding: 12, border: "1px solid #e5e5e5", borderRadius: 8 }}>
        <input style={input} placeholder="Банк" value={form.bank_name} onChange={(e) => setForm({ ...form, bank_name: e.target.value })} />
        <input style={input} placeholder="Владелец" value={form.holder_name} onChange={(e) => setForm({ ...form, holder_name: e.target.value })} />
        <input style={input} placeholder="Номер карты" value={form.card_number} onChange={(e) => setForm({ ...form, card_number: e.target.value })} />
        <input style={input} placeholder="Примечание" value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} />
        <button style={btnPrimary} disabled={busy} onClick={createCard}>Добавить карту</button>
      </div>

      {!rows && !error && <div>Загрузка...</div>}
      {rows && rows.length === 0 && <p style={{ color: "#6b7280" }}>Нет карт.</p>}
      {rows && rows.length > 0 && (
        <table style={{ borderCollapse: "collapse", width: "100%" }}>
          <thead>
            <tr>
              <th style={head}>Банк</th>
              <th style={head}>Владелец</th>
              <th style={head}>Номер</th>
              <th style={head}>Статус</th>
              <th style={head}>Действия</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.id}>
                <td style={cell}>{c.bank_name}</td>
                <td style={cell}>{c.holder_name}</td>
                <td style={cell}>{c.card_number_masked}</td>
                <td style={cell}>{c.is_active ? "Активна" : "Отключена"}</td>
                <td style={cell}>
                  <button style={{ ...input, cursor: "pointer" }} onClick={() => toggleActive(c)}>
                    {c.is_active ? "Отключить" : "Включить"}
                  </button>
                  <button style={{ ...input, cursor: "pointer" }} onClick={() => remove(c)}>Удалить</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

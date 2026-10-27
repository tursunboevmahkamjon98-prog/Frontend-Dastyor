"use client";

import { useCallback, useEffect, useState } from "react";
import AdminNav from "@/components/admin/AdminNav";
import { ApiError } from "@/lib/api";
import { ledgerApi, type BalanceTransactionOut } from "@/lib/admin-crm-api";

const cell: React.CSSProperties = { border: "1px solid #e5e5e5", padding: "6px 10px" };
const head: React.CSSProperties = { ...cell, background: "#f3f4f6", textAlign: "left", fontWeight: 600 };

export default function AdminBalancePage() {
  const [rows, setRows] = useState<BalanceTransactionOut[] | null>(null);
  const [kind, setKind] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    ledgerApi
      .listTransactions({ kind: kind || undefined, limit: 200 })
      .then(setRows)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Ошибка загрузки"));
  }, [kind]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div style={{ font: "13px/1.5 system-ui, sans-serif" }}>
      <AdminNav />
      <h1 style={{ fontSize: 18, fontWeight: 700, marginBottom: 12 }}>Баланс и транзакции</h1>
      <div style={{ marginBottom: 12 }}>
        <select value={kind} onChange={(e) => setKind(e.target.value)}>
          <option value="">Все типы</option>
          <option value="topup">Пополнение</option>
          <option value="charge">Списание</option>
          <option value="free">Бесплатно</option>
        </select>
      </div>
      {error && <div style={{ color: "#991b1b", marginBottom: 12 }}>{error}</div>}
      {!rows && !error && <div>Загрузка...</div>}
      {rows && rows.length === 0 && <p style={{ color: "#6b7280" }}>Нет операций.</p>}
      {rows && rows.length > 0 && (
        <table style={{ borderCollapse: "collapse", width: "100%" }}>
          <thead>
            <tr>
              <th style={head}>Пользователь</th>
              <th style={head}>Тип</th>
              <th style={head}>Сумма</th>
              <th style={head}>Баланс после</th>
              <th style={head}>Кто</th>
              <th style={head}>Причина</th>
              <th style={head}>Дата</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td style={cell}>{r.user_name ?? r.user_id ?? "—"}</td>
                <td style={cell}>{r.kind}</td>
                <td style={cell}>{r.amount_somoni.toFixed(2)}</td>
                <td style={cell}>{r.balance_after_somoni.toFixed(2)}</td>
                <td style={cell}>{r.actor_name ?? "—"}</td>
                <td style={cell}>{r.reason ?? "—"}</td>
                <td style={cell}>{new Date(r.created_at).toLocaleString("ru-RU")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

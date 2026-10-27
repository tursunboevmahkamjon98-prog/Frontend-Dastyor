"use client";

import { useCallback, useEffect, useState } from "react";
import AdminNav from "@/components/admin/AdminNav";
import { ApiError } from "@/lib/api";
import { ledgerApi, type AuditLogEntryOut } from "@/lib/admin-crm-api";

const cell: React.CSSProperties = { border: "1px solid #e5e5e5", padding: "6px 10px", verticalAlign: "top" };
const head: React.CSSProperties = { ...cell, background: "#f3f4f6", textAlign: "left", fontWeight: 600 };
const input: React.CSSProperties = { border: "1px solid #d1d5db", borderRadius: 4, padding: "4px 8px", marginRight: 6 };

export default function AdminAuditPage() {
  const [event, setEvent] = useState("");
  const [rows, setRows] = useState<AuditLogEntryOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    ledgerApi
      .listAuditLog({ event: event || undefined, limit: 200 })
      .then(setRows)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Ошибка загрузки"));
  }, [event]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div style={{ font: "13px/1.5 system-ui, sans-serif" }}>
      <AdminNav />
      <h1 style={{ fontSize: 18, fontWeight: 700, marginBottom: 12 }}>Журнал аудита</h1>
      <div style={{ marginBottom: 12 }}>
        <input style={input} placeholder="Фильтр по событию (например card_created)" value={event} onChange={(e) => setEvent(e.target.value)} />
      </div>
      {error && <div style={{ color: "#991b1b", marginBottom: 12 }}>{error}</div>}
      {!rows && !error && <div>Загрузка...</div>}
      {rows && rows.length === 0 && <p style={{ color: "#6b7280" }}>Записей нет.</p>}
      {rows && rows.length > 0 && (
        <table style={{ borderCollapse: "collapse", width: "100%" }}>
          <thead>
            <tr>
              <th style={head}>Событие</th>
              <th style={head}>Кто</th>
              <th style={head}>Детали</th>
              <th style={head}>Дата</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td style={cell}>{r.event}</td>
                <td style={cell}>
                  {r.actor_name ?? (r.actor_telegram_id ? `Telegram ${r.actor_telegram_id}` : r.actor_user_id ?? "—")}
                </td>
                <td style={cell}><code style={{ fontSize: 11 }}>{r.detail}</code></td>
                <td style={cell}>{new Date(r.created_at).toLocaleString("ru-RU")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

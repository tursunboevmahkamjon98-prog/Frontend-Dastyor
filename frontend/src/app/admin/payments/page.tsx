"use client";

import { useCallback, useEffect, useState } from "react";
import AdminNav from "@/components/admin/AdminNav";
import { ApiError } from "@/lib/api";
import { paymentsApi, type AdminPaymentRequestOut } from "@/lib/admin-crm-api";

const cell: React.CSSProperties = { border: "1px solid #e5e5e5", padding: "6px 10px", verticalAlign: "top" };
const head: React.CSSProperties = { ...cell, background: "#f3f4f6", textAlign: "left", fontWeight: 600 };
const btn: React.CSSProperties = { marginRight: 6, padding: "4px 10px", borderRadius: 4, border: "1px solid #d1d5db", background: "#fff", cursor: "pointer" };
const btnPrimary: React.CSSProperties = { ...btn, background: "#e11d2e", color: "#fff", borderColor: "#e11d2e" };

export default function AdminPaymentsPage() {
  const [status, setStatus] = useState("pending");
  const [rows, setRows] = useState<AdminPaymentRequestOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    paymentsApi
      .list(status || undefined)
      .then(setRows)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Ошибка загрузки"));
  }, [status]);

  useEffect(() => {
    load();
  }, [load]);

  async function act(fn: () => Promise<unknown>, id: string) {
    setBusyId(id);
    setError(null);
    try {
      await fn();
      load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Ошибка операции");
    } finally {
      setBusyId(null);
    }
  }

  function approve(r: AdminPaymentRequestOut) {
    const sure = confirm(`Подтвердить оплату ${r.public_code} на ${r.requested_somoni.toFixed(2)} сомони?`);
    if (!sure) return;
    act(() => paymentsApi.approve(r.id), r.id);
  }

  function reject(r: AdminPaymentRequestOut) {
    const note = prompt("Причина отклонения:") ?? "";
    act(() => paymentsApi.reject(r.id, note), r.id);
  }

  function requestInfo(r: AdminPaymentRequestOut) {
    const note = prompt("Что нужно уточнить у учителя?") ?? "";
    act(() => paymentsApi.requestInfo(r.id, note), r.id);
  }

  return (
    <div style={{ font: "13px/1.5 system-ui, sans-serif" }}>
      <AdminNav />
      <h1 style={{ fontSize: 18, fontWeight: 700, marginBottom: 12 }}>Платежи (Telegram)</h1>
      <div style={{ marginBottom: 12 }}>
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="pending">Ожидают проверки</option>
          <option value="needs_info">Нужна доп. информация</option>
          <option value="approved">Подтверждено</option>
          <option value="rejected">Отклонено</option>
          <option value="">Все</option>
        </select>
      </div>
      {error && <div style={{ color: "#991b1b", marginBottom: 12 }}>{error}</div>}
      {!rows && !error && <div>Загрузка...</div>}
      {rows && rows.length === 0 && <p style={{ color: "#6b7280" }}>Нет заявок.</p>}
      {rows && rows.length > 0 && (
        <table style={{ borderCollapse: "collapse", width: "100%" }}>
          <thead>
            <tr>
              <th style={head}>Код</th>
              <th style={head}>Учитель</th>
              <th style={head}>Заявлено</th>
              <th style={head}>OCR сумма</th>
              <th style={head}>OCR отправитель / ссылка</th>
              <th style={head}>Статус</th>
              <th style={head}>Действия</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td style={cell}>{r.public_code}</td>
                <td style={cell}>{r.user_name} {r.user_short_id ? `(#${r.user_short_id})` : ""}</td>
                <td style={cell}>{r.requested_somoni.toFixed(2)}</td>
                <td style={cell}>{r.ocr_amount_somoni != null ? r.ocr_amount_somoni.toFixed(2) : "—"}</td>
                <td style={cell}>
                  {r.ocr_sender ?? "—"}
                  {r.ocr_reference ? ` / ${r.ocr_reference}` : ""}
                  {r.receipt_file_id && (
                    <div style={{ color: "#9ca3af", fontSize: 11 }}>
                      Чек есть, просмотр изображения пока недоступен в CRM
                    </div>
                  )}
                </td>
                <td style={cell}>{r.status}</td>
                <td style={cell}>
                  {(r.status === "pending" || r.status === "needs_info") && (
                    <>
                      <button style={btnPrimary} disabled={busyId === r.id} onClick={() => approve(r)}>
                        Подтвердить
                      </button>
                      <button style={btn} disabled={busyId === r.id} onClick={() => reject(r)}>
                        Отклонить
                      </button>
                      <button style={btn} disabled={busyId === r.id} onClick={() => requestInfo(r)}>
                        Уточнить
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import AdminNav from "@/components/admin/AdminNav";
import { adminApi, ApiError, type AdminDashboardStats } from "@/lib/api";
import { paymentsApi, cardsApi } from "@/lib/admin-crm-api";

const tile: React.CSSProperties = {
  border: "1px solid #e5e5e5",
  borderRadius: 8,
  padding: 16,
  minWidth: 160,
  flex: "1 1 160px",
};

const tileValue: React.CSSProperties = { fontSize: 28, fontWeight: 700, color: "#e11d2e" };
const tileLabel: React.CSSProperties = { color: "#6b7280", fontSize: 13 };

export default function AdminOverviewPage() {
  const [stats, setStats] = useState<AdminDashboardStats | null>(null);
  const [pendingPayments, setPendingPayments] = useState<number | null>(null);
  const [activeCards, setActiveCards] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    adminApi.stats().then(setStats).catch((e) => setError(e instanceof ApiError ? e.message : "Ошибка"));
    paymentsApi.list("pending").then((r) => setPendingPayments(r.length)).catch(() => setPendingPayments(null));
    cardsApi.list().then((r) => setActiveCards(r.filter((c) => c.is_active).length)).catch(() => setActiveCards(null));
  }, []);

  return (
    <div style={{ font: "13px/1.5 system-ui, sans-serif" }}>
      <AdminNav />
      <h1 style={{ fontSize: 18, fontWeight: 700, marginBottom: 12 }}>Обзор</h1>
      {error && <div style={{ color: "#991b1b", marginBottom: 12 }}>{error}</div>}
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <div style={tile}>
          <div style={tileValue}>{stats ? stats.total_users : "…"}</div>
          <div style={tileLabel}>Пользователей</div>
        </div>
        <div style={tile}>
          <div style={tileValue}>{stats ? stats.total_materials : "…"}</div>
          <div style={tileLabel}>Материалов</div>
        </div>
        <div style={tile}>
          <div style={tileValue}>{pendingPayments ?? "…"}</div>
          <div style={tileLabel}>Платежей на проверке (Telegram)</div>
        </div>
        <div style={tile}>
          <div style={tileValue}>{activeCards ?? "…"}</div>
          <div style={tileLabel}>Активных карт</div>
        </div>
      </div>
      <p style={{ color: "#9ca3af", marginTop: 16, fontSize: 12 }}>
        Данные получены из реального API. Если значение не загрузилось — API пока недоступен, а не "0".
      </p>
    </div>
  );
}

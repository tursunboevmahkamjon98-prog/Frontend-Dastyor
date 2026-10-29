"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ApiError } from "@/lib/api";
import { adminRolesApi as adminApi, type AdminRosterOut, type AdminTier } from "@/lib/admin-roles-api";

// Deliberately plain, matching today's admin console (admin/page.tsx) —
// this page exists to make Stage 2 (the migration-review worklist)
// usable, not to be the finished CRM. The branded sidebar/shell and a
// redesigned version of this page land together in a later stage.

const TIERS: { value: AdminTier; label: string }[] = [
  { value: "super", label: "Супер-администратор" },
  { value: "finance", label: "Финансы" },
  { value: "support", label: "Поддержка" },
  { value: "readonly", label: "Только просмотр" },
];

const TIER_LABEL: Record<AdminTier | "unset", string> = {
  super: "Супер-администратор",
  finance: "Финансы",
  support: "Поддержка",
  readonly: "Только просмотр",
  unset: "Супер-администратор (по умолчанию)",
};

const cell: React.CSSProperties = {
  border: "1px solid #e5e5e5",
  padding: "6px 10px",
  verticalAlign: "top",
};

const head: React.CSSProperties = {
  ...cell,
  background: "#f3f4f6",
  textAlign: "left",
  fontWeight: 600,
  color: "#374151",
};

export default function AdminRolesPage() {
  const [roster, setRoster] = useState<AdminRosterOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [pendingTier, setPendingTier] = useState<Record<string, AdminTier>>({});

  const load = useCallback(() => {
    setError(null);
    adminApi
      .roster()
      .then(setRoster)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Не удалось загрузить список"));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handlePromote(userId: string, tier: AdminTier) {
    setBusyId(userId);
    setError(null);
    try {
      await adminApi.promote(userId, tier);
      load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Не удалось назначить роль");
    } finally {
      setBusyId(null);
    }
  }

  async function handleIgnore(userId: string) {
    setBusyId(userId);
    setError(null);
    try {
      await adminApi.ignore(userId);
      load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Не удалось отклонить заявку");
    } finally {
      setBusyId(null);
    }
  }

  async function handleDemote(userId: string) {
    if (!confirm("Снять права администратора у этого пользователя?")) return;
    setBusyId(userId);
    setError(null);
    try {
      await adminApi.demote(userId);
      load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Не удалось снять права");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div style={{ font: "13px/1.5 system-ui, sans-serif" }}>
      <div style={{ marginBottom: 16 }}>
        <Link href="/admin" style={{ textDecoration: "underline" }}>
          ← к консоли
        </Link>
      </div>
      <h1 style={{ fontSize: 18, fontWeight: 700, marginBottom: 4 }}>Администраторы и роли</h1>
      <p style={{ color: "#6b7280", marginBottom: 20 }}>
        Права администратора в Telegram-боте и на сайте теперь — одно и то же: роль пользователя.
        Заявки ниже — это администраторы, назначенные ранее через бота, чья веб-роль ещё не
        подтверждена. Ничего не происходит автоматически — каждую заявку нужно подтвердить или
        отклонить вручную.
      </p>

      {error && (
        <div style={{ background: "#fef2f2", color: "#991b1b", padding: "8px 12px", borderRadius: 4, marginBottom: 16 }}>
          {error}
        </div>
      )}

      {!roster && !error && <div>Загрузка...</div>}

      {roster && (
        <>
          <h2 style={{ fontSize: 15, fontWeight: 600, margin: "20px 0 8px" }}>
            Требуют проверки ({roster.unreviewed.length})
          </h2>
          {roster.unreviewed.length === 0 ? (
            <p style={{ color: "#6b7280" }}>Нет заявок, ожидающих проверки.</p>
          ) : (
            <table style={{ borderCollapse: "collapse", width: "100%", marginBottom: 24 }}>
              <thead>
                <tr>
                  <th style={head}>Пользователь</th>
                  <th style={head}>ID Dastyor</th>
                  <th style={head}>Telegram ID</th>
                  <th style={head}>Назначен</th>
                  <th style={head}>Действия</th>
                </tr>
              </thead>
              <tbody>
                {roster.unreviewed.map((r) => (
                  <tr key={r.grant_id}>
                    <td style={cell}>{r.full_name ?? "—"}</td>
                    <td style={cell}>{r.short_id ?? "—"}</td>
                    <td style={cell}>{r.telegram_user_id ?? "ещё не привязан"}</td>
                    <td style={cell}>{new Date(r.added_at).toLocaleString("ru-RU")}</td>
                    <td style={cell}>
                      {r.user_id ? (
                        <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
                          <select
                            value={pendingTier[r.user_id] ?? "support"}
                            onChange={(e) =>
                              setPendingTier((prev) => ({ ...prev, [r.user_id as string]: e.target.value as AdminTier }))
                            }
                            disabled={busyId === r.user_id}
                          >
                            {TIERS.map((t) => (
                              <option key={t.value} value={t.value}>
                                {t.label}
                              </option>
                            ))}
                          </select>
                          <button
                            onClick={() => handlePromote(r.user_id as string, pendingTier[r.user_id as string] ?? "support")}
                            disabled={busyId === r.user_id}
                          >
                            Подтвердить
                          </button>
                          <button
                            onClick={() => handleIgnore(r.user_id as string)}
                            disabled={busyId === r.user_id}
                          >
                            Отклонить
                          </button>
                        </div>
                      ) : (
                        <span style={{ color: "#6b7280" }}>Аккаунт удалён</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <h2 style={{ fontSize: 15, fontWeight: 600, margin: "20px 0 8px" }}>
            Действующие администраторы ({roster.admins.length})
          </h2>
          <table style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                <th style={head}>Имя</th>
                <th style={head}>ID Dastyor</th>
                <th style={head}>Роль</th>
                <th style={head}>Действия</th>
              </tr>
            </thead>
            <tbody>
              {roster.admins.map((a) => (
                <tr key={a.user_id}>
                  <td style={cell}>{a.full_name}</td>
                  <td style={cell}>{a.short_id ?? "—"}</td>
                  <td style={cell}>{TIER_LABEL[a.admin_tier ?? "unset"]}</td>
                  <td style={cell}>
                    <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                      <select
                        value={a.admin_tier ?? "super"}
                        onChange={(e) => handlePromote(a.user_id, e.target.value as AdminTier)}
                        disabled={busyId === a.user_id}
                      >
                        {TIERS.map((t) => (
                          <option key={t.value} value={t.value}>
                            {t.label}
                          </option>
                        ))}
                      </select>
                      <button onClick={() => handleDemote(a.user_id)} disabled={busyId === a.user_id}>
                        Снять права
                      </button>
                    </div>
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

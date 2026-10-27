"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  adminApi,
  ApiError,
  API_ORIGIN,
  type AdminUserOut,
  type AdminSmsResult,
  type AdminDashboardStats,
  type AdminMaterialOut,
  type AdminTopupRequestOut,
  type MaterialType,
} from "@/lib/api";

const PAGE_SIZE = 200;
const MAT_PAGE_SIZE = 50;

const MAT_TYPES: MaterialType[] = [
  "konspekt", "lektsiya", "test", "prezentatsiya", "amaliy", "igra",
];

const cell: React.CSSProperties = {
  border: "1px solid #e5e5e5",
  padding: "6px 10px",
  verticalAlign: "top",
  whiteSpace: "nowrap",
};

// For an "действия" column with several buttons: nowrap on an ordinary
// cell forced every action onto one unbroken line, so a row with six
// buttons made the whole table — users, materials, everything — scroll
// sideways just to reach "удалить". Wrapping here, and only here, keeps
// every other column's nowrap alignment while letting actions stack.
const actionsCell: React.CSSProperties = {
  ...cell,
  whiteSpace: "normal",
  minWidth: 260,
};

const head: React.CSSProperties = {
  ...cell,
  background: "#f3f4f6",
  textAlign: "left",
  fontWeight: 600,
  color: "#374151",
};

// A little cohesion, kept to this one page: before this, every button,
// input and table row reached for its own ad-hoc inline gray, which read
// as patched-together rather than designed. One small stylesheet, scoped
// under .admin-console so it cannot leak onto the rest of the app, gives
// every element the same radius, hover and row rhythm without rewriting
// each inline style by hand.
const ADMIN_STYLE = `
.admin-console button {
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.15s ease, border-color 0.15s ease;
}
.admin-console button:hover:not(:disabled) {
  background-color: #f1f5f9;
  border-color: #9ca3af;
}
.admin-console button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
.admin-console input, .admin-console select, .admin-console textarea {
  border-radius: 6px;
  outline: none;
}
.admin-console input:focus, .admin-console select:focus, .admin-console textarea:focus {
  border-color: #6b7280;
}
.admin-console table tbody tr:nth-child(even) td {
  background-color: #fafafa;
}
.admin-console table tbody tr:hover td {
  background-color: #f3f4f6;
}
.admin-console .admin-tab {
  border-radius: 8px 8px 0 0;
}
.admin-console .admin-tab:hover:not(.admin-tab-active) {
  background-color: #e5e7eb;
}
.admin-console a {
  color: #2563eb;
}
`;

const TABS = [
  { id: "users", label: "Пользователи" },
  { id: "materials", label: "Материалы" },
  { id: "topups", label: "Заявки на пополнение" },
  { id: "sms", label: "SMS" },
] as const;
type Tab = (typeof TABS)[number]["id"];

export default function AdminConsolePage() {
  const [tab, setTab] = useState<Tab>("users");
  const [stats, setStats] = useState<AdminDashboardStats | null>(null);
  const [users, setUsers] = useState<AdminUserOut[]>([]);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [smsText, setSmsText] = useState("");
  const [sending, setSending] = useState(false);
  const [smsResults, setSmsResults] = useState<AdminSmsResult[] | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const [topUp, setTopUp] = useState<Record<string, string>>({});
  const [materials, setMaterials] = useState<AdminMaterialOut[]>([]);
  const [matTotal, setMatTotal] = useState(0);
  const [matLoading, setMatLoading] = useState(false);
  const [matQ, setMatQ] = useState("");
  const [matType, setMatType] = useState<MaterialType | "">("");
  const [matOwner, setMatOwner] = useState<{ id: string; name: string } | null>(null);
  const [matOffset, setMatOffset] = useState(0);

  const [topupRequests, setTopupRequests] = useState<AdminTopupRequestOut[]>([]);
  const [topupStatusFilter, setTopupStatusFilter] = useState<"pending" | "approved" | "rejected">("pending");
  const [topupLoading, setTopupLoading] = useState(false);
  const [topupAmounts, setTopupAmounts] = useState<Record<string, string>>({});
  const [topupBusy, setTopupBusy] = useState<string | null>(null);

  const [payInstructions, setPayInstructions] = useState("");
  const [payInstructionsDraft, setPayInstructionsDraft] = useState("");
  const [payInstructionsLoaded, setPayInstructionsLoaded] = useState(false);
  const [payInstructionsSaving, setPayInstructionsSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const rows = await adminApi.listUsers({ q: q || undefined, limit: PAGE_SIZE });
      setUsers(rows);
      setSelected((prev) => {
        const alive = new Set(rows.map((r) => r.id));
        return new Set([...prev].filter((id) => alive.has(id)));
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось загрузить пользователей");
    } finally {
      setLoading(false);
    }
  }, [q]);

  useEffect(() => {
    const t = setTimeout(load, 250);
    return () => clearTimeout(t);
  }, [load]);

  useEffect(() => {
    const t = setTimeout(() => {
      adminApi.stats().then(setStats).catch(() => setStats(null));
    }, 0);
    return () => clearTimeout(t);
  }, []);

  function replace(user: AdminUserOut) {
    setUsers((prev) => prev.map((u) => (u.id === user.id ? user : u)));
  }

  async function act(fn: () => Promise<void>, label: string) {
    setError(null);
    setNote(null);
    try {
      await fn();
      setNote(label);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ошибка");
    }
  }

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    setSelected((prev) => (prev.size === users.length ? new Set() : new Set(users.map((u) => u.id))));
  }

  const loadMaterials = useCallback(async () => {
    setMatLoading(true);
    try {
      const page = await adminApi.listMaterials({
        q: matQ || undefined,
        type: matType || undefined,
        user_id: matOwner?.id,
        limit: MAT_PAGE_SIZE,
        offset: matOffset,
      });
      setMaterials(page.items);
      setMatTotal(page.total);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось загрузить материалы");
    } finally {
      setMatLoading(false);
    }
  }, [matQ, matType, matOwner, matOffset]);

  useEffect(() => {
    const t = setTimeout(loadMaterials, 250);
    return () => clearTimeout(t);
  }, [loadMaterials]);

  const loadTopupRequests = useCallback(async () => {
    setTopupLoading(true);
    try {
      const rows = await adminApi.listTopupRequests(topupStatusFilter);
      setTopupRequests(rows);
      setTopupAmounts((prev) => {
        const next: Record<string, string> = {};
        for (const r of rows) next[r.id] = prev[r.id] ?? String(r.requested_somoni);
        return next;
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось загрузить заявки");
    } finally {
      setTopupLoading(false);
    }
  }, [topupStatusFilter]);

  useEffect(() => {
    loadTopupRequests();
  }, [loadTopupRequests]);

  async function approveTopup(r: AdminTopupRequestOut) {
    const amount = Number(topupAmounts[r.id]);
    if (!Number.isFinite(amount) || amount <= 0) {
      setError("Введите сумму больше нуля");
      return;
    }
    setTopupBusy(r.id);
    setError(null);
    setNote(null);
    try {
      await adminApi.approveTopupRequest(r.id, amount);
      setNote(`${r.user_name}: зачислено ${amount} сомони`);
      await loadTopupRequests();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ошибка");
    } finally {
      setTopupBusy(null);
    }
  }

  async function rejectTopup(r: AdminTopupRequestOut) {
    setTopupBusy(r.id);
    setError(null);
    setNote(null);
    try {
      await adminApi.rejectTopupRequest(r.id);
      setNote(`${r.user_name}: заявка отклонена`);
      await loadTopupRequests();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ошибка");
    } finally {
      setTopupBusy(null);
    }
  }

  useEffect(() => {
    if (tab !== "topups" || payInstructionsLoaded) return;
    adminApi.getPayInstructions().then((r) => {
      setPayInstructions(r.text);
      setPayInstructionsDraft(r.text);
      setPayInstructionsLoaded(true);
    }).catch(() => setPayInstructionsLoaded(true));
  }, [tab, payInstructionsLoaded]);

  async function savePayInstructions() {
    setPayInstructionsSaving(true);
    setError(null);
    setNote(null);
    try {
      const r = await adminApi.setPayInstructions(payInstructionsDraft);
      setPayInstructions(r.text);
      setNote("Реквизиты оплаты сохранены. Остальные администраторы уведомлены в Telegram.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось сохранить реквизиты");
    } finally {
      setPayInstructionsSaving(false);
    }
  }

  function filterByOwner(user: AdminUserOut) {
    setMatOwner({ id: user.id, name: user.full_name });
    setMatOffset(0);
    document.getElementById("materials")?.scrollIntoView({ behavior: "smooth" });
  }

  const withPhone = users.filter((u) => selected.has(u.id) && u.phone).length;
  const noPhone = selected.size - withPhone;

  async function sendBulk() {
    if (!smsText.trim() || selected.size === 0) return;
    setSending(true);
    setError(null);
    setNote(null);
    setSmsResults(null);
    try {
      const report = await adminApi.sendBulkSms([...selected], smsText);
      setSmsResults(report.results);
      setNote(`Отправлено: ${report.sent}, не отправлено: ${report.failed}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось отправить");
    } finally {
      setSending(false);
    }
  }

  async function sendOne(user: AdminUserOut) {
    if (!smsText.trim()) {
      setError("Сначала напишите текст SMS ниже");
      return;
    }
    setSending(true);
    setError(null);
    setNote(null);
    setSmsResults(null);
    try {
      const r = await adminApi.sendSms(user.id, smsText);
      setSmsResults([r]);
      setNote(r.sent ? `Отправлено: ${user.full_name}` : `Не отправлено: ${r.error ?? "?"}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось отправить");
    } finally {
      setSending(false);
    }
  }

  return (
    <div
      className="admin-console"
      style={{
        font: "13px/1.5 -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        color: "#111827",
        background: "#f9fafb",
        minHeight: "100vh",
        padding: "20px 24px 48px",
      }}
    >
      <style>{ADMIN_STYLE}</style>

      <h1 style={{ fontSize: 18, fontWeight: 700, marginBottom: 10 }}>Админ-консоль</h1>

      {stats && (
        <p style={{ marginBottom: 10, color: "#4b5563" }}>
          всего: {stats.total_users} польз. · {stats.total_materials} материалов (конспекты{" "}
          {stats.total_konspekts}, тесты {stats.total_tests}, презентации {stats.total_presentations})
        </p>
      )}

      {error && (
        <p style={{ color: "#991b1b", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 6, padding: "6px 10px", marginBottom: 8 }}>
          {error}
        </p>
      )}
      {note && (
        <p style={{ color: "#166534", background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 6, padding: "6px 10px", marginBottom: 8 }}>
          {note}
        </p>
      )}

      <div style={{ marginBottom: 16, borderBottom: "1px solid #d1d5db", display: "flex", gap: 2 }}>
        {TABS.map((tb) => (
          <button
            key={tb.id}
            onClick={() => setTab(tb.id)}
            className={`admin-tab${tab === tb.id ? " admin-tab-active" : ""}`}
            style={{
              font: "inherit",
              padding: "8px 16px",
              border: "1px solid #d1d5db",
              borderBottom: tab === tb.id ? "2px solid #111827" : "1px solid #d1d5db",
              background: tab === tb.id ? "#fff" : "#f3f4f6",
              fontWeight: tab === tb.id ? 600 : 400,
              marginBottom: -1,
            }}
          >
            {tb.label}
          </button>
        ))}
      </div>

      <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10, padding: 16 }}>

      {tab === "users" && (
      <>
      <div style={{ marginBottom: 8 }}>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="поиск: имя, телефон, email"
          style={{ border: "1px solid #d1d5db", padding: "3px 6px", width: 280, font: "inherit" }}
        />{" "}
        <button onClick={load} disabled={loading} style={{ border: "1px solid #d1d5db", padding: "3px 8px", font: "inherit" }}>
          {loading ? "..." : "обновить"}
        </button>{" "}
        <span>
          показано {users.length} (лимит {PAGE_SIZE}), выбрано {selected.size}
        </span>
      </div>
      <div style={{ overflowX: "auto", marginBottom: 12 }}>
        <table style={{ borderCollapse: "collapse", width: "100%" }}>
          <thead>
            <tr>
              <th style={head}>
                <input type="checkbox" checked={users.length > 0 && selected.size === users.length} onChange={toggleAll} />
              </th>
              <th style={head}>имя</th>
              <th style={head}>телефон</th>
              <th style={head}>email</th>
              <th style={head}>роль</th>
              <th style={head}>premium</th>
              <th style={head}>баланс</th>
              <th style={head}>к/т/п</th>
              <th style={head}>яз</th>
              <th style={head}>создан</th>
              <th style={head}>действия</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td style={cell}>
                  <input type="checkbox" checked={selected.has(u.id)} onChange={() => toggle(u.id)} />
                </td>
                <td style={cell}>{u.full_name}</td>
                <td style={cell}>{u.phone ?? "—"}</td>
                <td style={cell}>{u.email ?? "—"}</td>
                <td style={cell}>{u.role}</td>
                <td style={cell}>{u.is_premium ? "да" : "нет"}</td>
                <td style={cell}>{u.balance_somoni.toFixed(2)}</td>
                <td style={cell}>
                  {u.konspekt_count}/{u.test_count}/{u.presentation_count}
                </td>
                <td style={cell}>{u.language}</td>
                <td style={cell}>{new Date(u.created_at).toLocaleDateString("ru-RU")}</td>
                <td style={actionsCell}>
                  <button onClick={() => filterByOwner(u)} style={{ font: "inherit" }}>
                    материалы
                  </button>{" "}
                  <button
                    onClick={() =>
                      act(async () => replace(await adminApi.setRole(u.id, u.role === "admin" ? "user" : "admin")),
                        `${u.full_name}: роль изменена`)
                    }
                    style={{ font: "inherit" }}
                  >
                    {u.role === "admin" ? "снять админа" : "сделать админом"}
                  </button>{" "}
                  <button
                    onClick={() =>
                      act(async () => replace(await adminApi.setPremium(u.id, !u.is_premium)),
                        `${u.full_name}: premium ${u.is_premium ? "снят" : "выдан"}`)
                    }
                    style={{ font: "inherit" }}
                  >
                    {u.is_premium ? "снять premium" : "выдать premium"}
                  </button>{" "}
                  <input
                    value={topUp[u.id] ?? ""}
                    onChange={(e) => setTopUp((p) => ({ ...p, [u.id]: e.target.value }))}
                    placeholder="сомони"
                    style={{ width: 70, border: "1px solid #d1d5db", font: "inherit" }}
                  />
                  <button
                    onClick={() => {
                      const amount = Number(topUp[u.id]);
                      if (!Number.isFinite(amount) || amount <= 0) {
                        setError("Введите сумму больше нуля");
                        return;
                      }
                      act(async () => {
                        replace(await adminApi.addBalance(u.id, amount, "админ-консоль"));
                        setTopUp((p) => ({ ...p, [u.id]: "" }));
                      }, `${u.full_name}: +${amount} сомони`);
                    }}
                    style={{ font: "inherit" }}
                  >
                    пополнить
                  </button>{" "}
                  <button onClick={() => sendOne(u)} disabled={sending || !u.phone} style={{ font: "inherit" }}>
                    SMS
                  </button>{" "}
                  {confirmDelete === u.id ? (
                    <>
                      <button
                        onClick={() =>
                          act(async () => {
                            await adminApi.removeUser(u.id);
                            setUsers((prev) => prev.filter((x) => x.id !== u.id));
                            setConfirmDelete(null);
                          }, `${u.full_name}: удалён`)
                        }
                        style={{ font: "inherit", color: "#b00" }}
                      >
                        точно удалить
                      </button>{" "}
                      <button onClick={() => setConfirmDelete(null)} style={{ font: "inherit" }}>
                        отмена
                      </button>
                    </>
                  ) : (
                    <button onClick={() => setConfirmDelete(u.id)} style={{ font: "inherit" }}>
                      удалить
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      </>
      )}

      {tab === "materials" && (
      <>
      <h2 id="materials" style={{ fontSize: 14, fontWeight: 700, marginBottom: 6 }}>
        Материалы
      </h2>

      <div style={{ marginBottom: 8 }}>
        <input
          value={matQ}
          onChange={(e) => { setMatQ(e.target.value); setMatOffset(0); }}
          placeholder="поиск: название, предмет"
          style={{ border: "1px solid #d1d5db", padding: "3px 6px", width: 280, font: "inherit" }}
        />{" "}
        <select
          value={matType}
          onChange={(e) => { setMatType(e.target.value as MaterialType | ""); setMatOffset(0); }}
          style={{ border: "1px solid #d1d5db", padding: "3px 6px", font: "inherit" }}
        >
          <option value="">все типы</option>
          {MAT_TYPES.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>{" "}
        {matOwner && (
          <>
            <span>автор: {matOwner.name}</span>{" "}
            <button onClick={() => { setMatOwner(null); setMatOffset(0); }} style={{ font: "inherit" }}>
              снять фильтр
            </button>{" "}
          </>
        )}
        <button onClick={loadMaterials} disabled={matLoading} style={{ border: "1px solid #d1d5db", padding: "3px 8px", font: "inherit" }}>
          {matLoading ? "..." : "обновить"}
        </button>{" "}
        <span>
          {matTotal === 0 ? "ничего не найдено" : `${matOffset + 1}–${Math.min(matOffset + MAT_PAGE_SIZE, matTotal)} из ${matTotal}`}
        </span>{" "}
        <button onClick={() => setMatOffset(Math.max(matOffset - MAT_PAGE_SIZE, 0))} disabled={matOffset === 0} style={{ font: "inherit" }}>
          назад
        </button>{" "}
        <button onClick={() => setMatOffset(matOffset + MAT_PAGE_SIZE)} disabled={matOffset + MAT_PAGE_SIZE >= matTotal} style={{ font: "inherit" }}>
          вперёд
        </button>
      </div>

      <div style={{ overflowX: "auto", marginBottom: 12 }}>
        <table style={{ borderCollapse: "collapse", width: "100%" }}>
          <thead>
            <tr>
              <th style={head}>тип</th>
              <th style={head}>название</th>
              <th style={head}>предмет</th>
              <th style={head}>класс</th>
              <th style={head}>автор</th>
              <th style={head}>создан</th>
              <th style={head}>действия</th>
            </tr>
          </thead>
          <tbody>
            {materials.map((m) => (
              <tr key={`${m.type}-${m.id}`}>
                <td style={cell}>{m.type}</td>
                <td style={{ ...cell, whiteSpace: "normal", minWidth: 260 }}>{m.title || "—"}</td>
                <td style={cell}>{m.subject}</td>
                <td style={cell}>{m.grade}</td>
                <td style={cell}>
                  {m.owner_name}
                  {m.owner_phone ? ` (${m.owner_phone})` : ""}
                </td>
                <td style={cell}>{new Date(m.created_at).toLocaleDateString("ru-RU")}</td>
                <td style={actionsCell}>
                  <Link
                    href={`/dashboard/materials/${m.type}/${m.id}`}
                    target="_blank"
                    style={{ textDecoration: "underline" }}
                  >
                    открыть
                  </Link>{" "}
                  <button
                    onClick={() =>
                      act(async () => {
                        await adminApi.removeMaterial(m.type, m.id);
                        setMaterials((prev) => prev.filter((x) => x.id !== m.id));
                        setMatTotal((n) => Math.max(n - 1, 0));
                      }, `${m.title || m.id}: удалён`)
                    }
                    style={{ font: "inherit", color: "#b00" }}
                  >
                    удалить
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      </>
      )}

      {tab === "topups" && (
      <>
      <h2 style={{ fontSize: 14, fontWeight: 700, marginBottom: 6 }}>Реквизиты оплаты</h2>
      <p style={{ marginBottom: 8, color: "#6b7280" }}>
        Этот текст (карта/реквизиты) видят все учителя — и на сайте, и в Telegram-боте, это одно и то же значение.
        Изменение здесь уведомляет остальных администраторов в Telegram.
      </p>
      <textarea
        value={payInstructionsDraft}
        onChange={(e) => setPayInstructionsDraft(e.target.value)}
        rows={4}
        placeholder="Например: Карта Алиф 1234 5678 9012 3456, получатель Имя Фамилия"
        style={{ width: "100%", maxWidth: 520, border: "1px solid #d1d5db", padding: 8, font: "inherit", display: "block" }}
      />
      <div style={{ marginTop: 6, marginBottom: 20 }}>
        <button
          onClick={savePayInstructions}
          disabled={payInstructionsSaving || payInstructionsDraft === payInstructions}
          style={{ border: "1px solid #d1d5db", padding: "6px 14px", font: "inherit", fontWeight: 600 }}
        >
          {payInstructionsSaving ? "сохраняем..." : "сохранить реквизиты"}
        </button>{" "}
        {payInstructionsDraft !== payInstructions && !payInstructionsSaving && (
          <span style={{ color: "#92400e" }}>есть несохранённые изменения</span>
        )}
      </div>

      <h2 style={{ fontSize: 14, fontWeight: 700, marginBottom: 6 }}>Заявки на пополнение (сайт)</h2>
      <div style={{ marginBottom: 8 }}>
        {(["pending", "approved", "rejected"] as const).map((s) => (
          <button
            key={s}
            onClick={() => setTopupStatusFilter(s)}
            style={{
              font: "inherit",
              marginRight: 6,
              padding: "3px 8px",
              border: "1px solid #d1d5db",
              background: topupStatusFilter === s ? "#ddd" : "transparent",
            }}
          >
            {s === "pending" ? "ожидают" : s === "approved" ? "зачислены" : "отклонены"}
          </button>
        ))}
        <button onClick={loadTopupRequests} disabled={topupLoading} style={{ border: "1px solid #d1d5db", padding: "3px 8px", font: "inherit" }}>
          {topupLoading ? "..." : "обновить"}
        </button>
      </div>

      <div style={{ overflowX: "auto", marginBottom: 12 }}>
        <table style={{ borderCollapse: "collapse", width: "100%" }}>
          <thead>
            <tr>
              <th style={head}>пользователь</th>
              <th style={head}>телефон</th>
              <th style={head}>баланс</th>
              <th style={head}>запрошено</th>
              <th style={head}>комментарий</th>
              <th style={head}>чек</th>
              <th style={head}>создана</th>
              <th style={head}>действия</th>
            </tr>
          </thead>
          <tbody>
            {topupRequests.length === 0 && (
              <tr>
                <td style={cell} colSpan={8}>
                  {topupLoading ? "загрузка..." : "ничего не найдено"}
                </td>
              </tr>
            )}
            {topupRequests.map((r) => (
              <tr key={r.id}>
                <td style={cell}>
                  {r.user_name} {r.user_short_id ? `(#${r.user_short_id})` : ""}
                </td>
                <td style={cell}>{r.user_phone ?? "—"}</td>
                <td style={cell}>{r.user_balance_somoni.toFixed(2)}</td>
                <td style={cell}>{r.requested_somoni.toFixed(2)}</td>
                <td style={{ ...cell, whiteSpace: "normal", minWidth: 160 }}>{r.note ?? "—"}</td>
                <td style={cell}>
                  {r.receipt_url ? (
                    <a href={`${API_ORIGIN}${r.receipt_url}`} target="_blank" rel="noreferrer" style={{ textDecoration: "underline" }}>
                      открыть
                    </a>
                  ) : (
                    "—"
                  )}
                </td>
                <td style={cell}>{new Date(r.created_at).toLocaleString("ru-RU")}</td>
                <td style={actionsCell}>
                  {r.status === "pending" ? (
                    <>
                      <input
                        value={topupAmounts[r.id] ?? ""}
                        onChange={(e) => setTopupAmounts((p) => ({ ...p, [r.id]: e.target.value }))}
                        style={{ width: 60, border: "1px solid #d1d5db", font: "inherit" }}
                      />{" "}
                      <button onClick={() => approveTopup(r)} disabled={topupBusy === r.id} style={{ font: "inherit" }}>
                        зачислить
                      </button>{" "}
                      <button onClick={() => rejectTopup(r)} disabled={topupBusy === r.id} style={{ font: "inherit", color: "#b00" }}>
                        отклонить
                      </button>
                    </>
                  ) : r.status === "approved" ? (
                    <span style={{ color: "#070" }}>зачислено {r.credited_somoni?.toFixed(2)}</span>
                  ) : (
                    <span style={{ color: "#b00" }}>отклонена</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      </>
      )}

      {tab === "sms" && (
      <>
      <h2 style={{ fontSize: 14, fontWeight: 700, marginBottom: 6 }}>SMS</h2>
      <textarea
        value={smsText}
        onChange={(e) => setSmsText(e.target.value)}
        maxLength={480}
        rows={4}
        placeholder="Текст сообщения"
        style={{ width: "100%", maxWidth: 600, border: "1px solid #d1d5db", padding: 6, font: "inherit" }}
      />
      <div style={{ marginTop: 6 }}>
        <span>{smsText.length}/480 символов</span>{" "}
        <button onClick={sendBulk} disabled={sending || selected.size === 0 || !smsText.trim()} style={{ font: "inherit", padding: "3px 8px" }}>
          {sending ? "отправка..." : `отправить выбранным (${withPhone})`}
        </button>{" "}
        {noPhone > 0 && <span style={{ color: "#b00" }}>без номера: {noPhone}</span>}
      </div>
      <p style={{ marginTop: 6, color: "#555" }}>
        Кнопка SMS в строке отправляет тот же текст одному пользователю.
      </p>

      {smsResults?.some((r) => r.dry_run) && (
        <p style={{ marginTop: 6, color: "#b00" }}>
          SMS_DRY_RUN включён на сервере — ни одно сообщение реально не ушло.
        </p>
      )}

      {smsResults && (
        <table style={{ borderCollapse: "collapse", marginTop: 10 }}>
          <thead>
            <tr>
              <th style={head}>кому</th>
              <th style={head}>номер</th>
              <th style={head}>итог</th>
            </tr>
          </thead>
          <tbody>
            {smsResults.map((r) => (
              <tr key={r.user_id}>
                <td style={cell}>{r.full_name}</td>
                <td style={cell}>{r.phone ?? "—"}</td>
                <td style={{ ...cell, color: r.sent ? "#070" : "#b00" }}>{r.sent ? "отправлено" : r.error ?? "ошибка"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      </>
      )}
      </div>
    </div>
  );
}

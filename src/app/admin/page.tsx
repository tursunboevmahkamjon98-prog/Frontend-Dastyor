"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  adminApi,
  ApiError,
  type AdminUserOut,
  type AdminSmsResult,
  type AdminDashboardStats,
  type AdminMaterialOut,
} from "@/lib/api";

const PAGE_SIZE = 200;

const cell: React.CSSProperties = {
  border: "1px solid #ccc",
  padding: "3px 6px",
  verticalAlign: "top",
  whiteSpace: "nowrap",
};

const head: React.CSSProperties = { ...cell, background: "#eee", textAlign: "left" };

export default function AdminConsolePage() {
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
  const [openUser, setOpenUser] = useState<AdminUserOut | null>(null);
  const [materials, setMaterials] = useState<AdminMaterialOut[] | null>(null);
  const [materialsLoading, setMaterialsLoading] = useState(false);

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

  async function showMaterials(user: AdminUserOut) {
    if (openUser?.id === user.id) {
      setOpenUser(null);
      setMaterials(null);
      return;
    }
    setOpenUser(user);
    setMaterials(null);
    setMaterialsLoading(true);
    setError(null);
    try {
      const page = await adminApi.listMaterials({ user_id: user.id, limit: 100 });
      setMaterials(page.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось загрузить материалы");
    } finally {
      setMaterialsLoading(false);
    }
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
    <div style={{ font: "13px/1.4 monospace", color: "#111" }}>
      <h1 style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>Админ-консоль</h1>

      {stats && (
        <p style={{ marginBottom: 8 }}>
          всего: {stats.total_users} польз. · {stats.total_materials} материалов (конспекты{" "}
          {stats.total_konspekts}, тесты {stats.total_tests}, презентации {stats.total_presentations})
        </p>
      )}

      <div style={{ marginBottom: 8 }}>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="поиск: имя, телефон, email"
          style={{ border: "1px solid #999", padding: "3px 6px", width: 280, font: "inherit" }}
        />{" "}
        <button onClick={load} disabled={loading} style={{ border: "1px solid #999", padding: "3px 8px", font: "inherit" }}>
          {loading ? "..." : "обновить"}
        </button>{" "}
        <span>
          показано {users.length} (лимит {PAGE_SIZE}), выбрано {selected.size}
        </span>
      </div>

      {error && <p style={{ color: "#b00", marginBottom: 6 }}>{error}</p>}
      {note && <p style={{ color: "#070", marginBottom: 6 }}>{note}</p>}

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
                <td style={cell}>
                  <button onClick={() => showMaterials(u)} style={{ font: "inherit" }}>
                    {openUser?.id === u.id ? "скрыть материалы" : "материалы"}
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
                    style={{ width: 70, border: "1px solid #999", font: "inherit" }}
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

      {openUser && (
        <div style={{ marginBottom: 12 }}>
          <h2 style={{ fontSize: 14, fontWeight: 700, marginBottom: 6 }}>
            Материалы: {openUser.full_name} {openUser.phone ? `(${openUser.phone})` : ""}
          </h2>
          {materialsLoading && <p>загрузка...</p>}
          {materials && materials.length === 0 && <p>нет материалов</p>}
          {materials && materials.length > 0 && (
            <table style={{ borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th style={head}>тип</th>
                  <th style={head}>название</th>
                  <th style={head}>предмет</th>
                  <th style={head}>класс</th>
                  <th style={head}>создан</th>
                  <th style={head}>действия</th>
                </tr>
              </thead>
              <tbody>
                {materials.map((m) => (
                  <tr key={`${m.type}-${m.id}`}>
                    <td style={cell}>{m.type}</td>
                    <td style={{ ...cell, whiteSpace: "normal", maxWidth: 400 }}>{m.title || "—"}</td>
                    <td style={cell}>{m.subject}</td>
                    <td style={cell}>{m.grade}</td>
                    <td style={cell}>{new Date(m.created_at).toLocaleDateString("ru-RU")}</td>
                    <td style={cell}>
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
                            setMaterials((prev) => (prev ? prev.filter((x) => x.id !== m.id) : prev));
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
          )}
        </div>
      )}

      <h2 style={{ fontSize: 14, fontWeight: 700, marginBottom: 6 }}>SMS</h2>
      <textarea
        value={smsText}
        onChange={(e) => setSmsText(e.target.value)}
        maxLength={480}
        rows={4}
        placeholder="Текст сообщения"
        style={{ width: "100%", maxWidth: 600, border: "1px solid #999", padding: 6, font: "inherit" }}
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
    </div>
  );
}

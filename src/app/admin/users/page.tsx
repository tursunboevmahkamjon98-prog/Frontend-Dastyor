"use client";

import { useEffect, useState, useCallback } from "react";
import { Search, Shield, ShieldOff, Trash2, Loader2, Crown, Wallet, FileText } from "lucide-react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { adminApi, AdminUserOut, ApiError } from "@/lib/api";

export default function AdminUsersPage() {
  const { user: me } = useAuth();
  const [query, setQuery] = useState("");
  const [users, setUsers] = useState<AdminUserOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [topUpOpenId, setTopUpOpenId] = useState<string | null>(null);
  const [topUpAmount, setTopUpAmount] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      // listUsers takes an AdminListUsersParams object, not a bare
      // search string — passing the string compiled to an error that
      // failed `next build`.
      setUsers(await adminApi.listUsers(query ? { q: query } : {}));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось загрузить");
    } finally {
      setLoading(false);
    }
  }, [query]);

  useEffect(() => {
    const t = setTimeout(load, 250); // debounce search
    return () => clearTimeout(t);
  }, [load]);

  async function toggleRole(u: AdminUserOut) {
    const nextRole = u.role === "admin" ? "user" : "admin";
    setBusyId(u.id);
    setError(null);
    try {
      const updated = await adminApi.setRole(u.id, nextRole);
      setUsers((prev) => prev.map((x) => (x.id === u.id ? updated : x)));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось изменить роль");
    } finally {
      setBusyId(null);
    }
  }

  // Free tier: 1 konspekt/test/presentation/lecture per account (see
  // backend's _check_free_limit) — no payment gateway wired up yet, so
  // this toggle is the only way to grant is_premium today, done by hand
  // once a teacher has paid some other way.
  async function togglePremium(u: AdminUserOut) {
    setBusyId(u.id);
    setError(null);
    try {
      const updated = await adminApi.setPremium(u.id, !u.is_premium);
      setUsers((prev) => prev.map((x) => (x.id === u.id ? updated : x)));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось изменить статус");
    } finally {
      setBusyId(null);
    }
  }

  async function addBalance(u: AdminUserOut) {
    const amount = Number(topUpAmount);
    if (!amount || amount <= 0) return;
    setBusyId(u.id);
    setError(null);
    try {
      const updated = await adminApi.addBalance(u.id, amount);
      setUsers((prev) => prev.map((x) => (x.id === u.id ? updated : x)));
      setTopUpOpenId(null);
      setTopUpAmount("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось пополнить баланс");
    } finally {
      setBusyId(null);
    }
  }

  async function remove(u: AdminUserOut) {
    // Irreversible and cascades to every material the account owns (see
    // backend/app/routers/admin.py) — worth a native confirm() here even
    // though the rest of the app moved to the undo-toast pattern, since
    // there's no equivalent "undo" story for an admin nuking someone
    // else's whole account.
    if (!confirm(`Удалить аккаунт «${u.phone ?? u.email}» и все его материалы (${u.konspekt_count + u.test_count + u.presentation_count} шт.)? Это необратимо.`)) return;
    setBusyId(u.id);
    setError(null);
    try {
      await adminApi.removeUser(u.id);
      setUsers((prev) => prev.filter((x) => x.id !== u.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось удалить");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <h1 className="mb-1 text-2xl font-bold text-text-primary">Пользователи</h1>
      <p className="mb-5 text-sm text-text-secondary">Все зарегистрированные аккаунты</p>

      <div className="relative mb-4">
        <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-text-tertiary" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Поиск по имени или телефону..."
          className="w-full rounded-xl border border-border bg-surface py-2.5 pl-10 pr-4 text-sm text-text-primary outline-none focus:border-primary"
        />
      </div>

      {error && <p className="mb-4 rounded-xl bg-primary-50 px-4 py-2.5 text-sm text-primary-dark">{error}</p>}

      {loading ? (
        <p className="py-10 text-center text-sm text-text-secondary">Загрузка...</p>
      ) : users.length === 0 ? (
        <p className="py-10 text-center text-sm text-text-secondary">Ничего не найдено</p>
      ) : (
        <div className="overflow-hidden rounded-2xl border border-border-light bg-surface">
          <div className="divide-y divide-border-light">
            {users.map((u) => {
              const isMe = u.id === me?.id;
              const isAdmin = u.role === "admin";
              const totalMaterials = u.konspekt_count + u.test_count + u.presentation_count;
              return (
                <div key={u.id} className="flex items-center gap-3 p-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="truncate font-medium text-text-primary">{u.full_name}</p>
                      {isAdmin && (
                        <span className="shrink-0 rounded-full bg-primary-50 px-2 py-0.5 text-[10px] font-semibold text-primary-dark">
                          ADMIN
                        </span>
                      )}
                      {u.is_premium && (
                        <span className="flex shrink-0 items-center gap-0.5 rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-700">
                          <Crown className="h-2.5 w-2.5" />
                          PREMIUM
                        </span>
                      )}
                      {isMe && <span className="shrink-0 text-[10px] text-text-tertiary">(вы)</span>}
                    </div>
                    <p className="truncate text-xs text-text-secondary">{u.phone ?? u.email}</p>
                    <p className="mt-0.5 text-xs text-text-tertiary">
                      {totalMaterials} материалов ({u.konspekt_count} конспект, {u.test_count} тест, {u.presentation_count} през.) •
                      {" "}
                      {new Date(u.created_at).toLocaleDateString("ru-RU")}
                      {" • "}
                      <span className="font-medium text-text-secondary">{u.balance_somoni.toFixed(0)} с.</span>
                    </p>
                    {topUpOpenId === u.id && (
                      <div className="mt-2 flex items-center gap-2">
                        <input
                          autoFocus
                          type="number"
                          min={1}
                          value={topUpAmount}
                          onChange={(e) => setTopUpAmount(e.target.value)}
                          onKeyDown={(e) => e.key === "Enter" && addBalance(u)}
                          placeholder="Сумма, сомони"
                          className="w-32 rounded-lg border border-border bg-white px-2.5 py-1.5 text-xs outline-none focus:border-primary"
                        />
                        <button
                          onClick={() => addBalance(u)}
                          disabled={busyId === u.id}
                          className="rounded-lg bg-primary px-2.5 py-1.5 text-xs font-medium text-white disabled:opacity-40"
                        >
                          Пополнить
                        </button>
                        <button
                          onClick={() => { setTopUpOpenId(null); setTopUpAmount(""); }}
                          className="text-xs text-text-tertiary hover:text-text-secondary"
                        >
                          Отмена
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Straight to what this account has actually made.
                      The admin materials list could already be searched
                      by hand, but "which of these rows are hers" is not
                      a search — it is a filter, and it belongs on the
                      row that raises the question. */}
                  <Link
                    href={`/admin/materials?user=${u.id}`}
                    title={`Материалы: ${u.full_name}`}
                    className="flex shrink-0 items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-xs font-medium text-text-secondary hover:bg-surface-muted"
                  >
                    <FileText className="h-3.5 w-3.5" />
                  </Link>

                  <button
                    onClick={() => setTopUpOpenId(topUpOpenId === u.id ? null : u.id)}
                    disabled={busyId === u.id}
                    title="Пополнить баланс вручную (после оплаты через Telegram/WhatsApp/телефон)"
                    className="flex shrink-0 items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-xs font-medium text-text-secondary hover:bg-surface-muted disabled:opacity-40"
                  >
                    <Wallet className="h-3.5 w-3.5" />
                  </button>

                  <button
                    onClick={() => togglePremium(u)}
                    disabled={busyId === u.id}
                    title={u.is_premium ? "Убрать premium (вернуть на бесплатный тариф)" : "Выдать premium вручную"}
                    className={`flex shrink-0 items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium disabled:opacity-40 ${
                      u.is_premium
                        ? "border-amber-300 bg-amber-50 text-amber-700 hover:bg-amber-100"
                        : "border-border text-text-secondary hover:bg-surface-muted"
                    }`}
                  >
                    {busyId === u.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Crown className="h-3.5 w-3.5" />}
                  </button>

                  <button
                    onClick={() => toggleRole(u)}
                    disabled={busyId === u.id || isMe}
                    title={isMe ? "Нельзя изменить свою роль" : isAdmin ? "Убрать права админа" : "Сделать админом"}
                    className="flex shrink-0 items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-xs font-medium text-text-secondary hover:bg-surface-muted disabled:opacity-40"
                  >
                    {busyId === u.id ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : isAdmin ? (
                      <ShieldOff className="h-3.5 w-3.5" />
                    ) : (
                      <Shield className="h-3.5 w-3.5" />
                    )}
                  </button>

                  <button
                    onClick={() => remove(u)}
                    disabled={busyId === u.id || isMe}
                    title={isMe ? "Нельзя удалить себя отсюда" : "Удалить аккаунт"}
                    className="shrink-0 rounded-lg p-1.5 text-text-tertiary hover:text-primary disabled:opacity-40"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

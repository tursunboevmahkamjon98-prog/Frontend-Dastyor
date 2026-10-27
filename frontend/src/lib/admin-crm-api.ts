// New CRM endpoints (Stages 3-5 backend). Kept separate from lib/api.ts
// on purpose — that file carries extensive unrelated uncommitted work,
// and this feature must never touch it further. Reuses its exported
// getToken()/ApiError for a consistent fetch convention without
// importing anything that would require editing that file.
import { getToken, ApiError } from "./api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/api";

async function request<T>(path: string, options: { method?: string; body?: unknown } = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_URL}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof data.detail === "string" ? data.detail : "Ошибка запроса";
    throw new ApiError(detail, res.status);
  }
  return data as T;
}

function qs(params: Record<string, unknown>): string {
  const parts = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== "")
    .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`);
  return parts.length ? `?${parts.join("&")}` : "";
}

export interface AdminPaymentRequestOut {
  id: string;
  public_code: string;
  user_id: string;
  user_name: string;
  user_short_id: string | null;
  requested_somoni: number;
  status: string;
  receipt_file_id: string | null;
  ocr_amount_somoni: number | null;
  ocr_sender: string | null;
  ocr_recipient: string | null;
  ocr_reference: string | null;
  ocr_confidence: number;
  ocr_warnings: string | null;
  credited_somoni: number | null;
  decision_note: string | null;
  created_at: string;
}

export interface CardOut {
  id: string;
  bank_name: string;
  holder_name: string;
  card_number_masked: string;
  currency: string;
  note: string | null;
  is_active: boolean;
  sort_order: number;
}

export interface ExpenseOut {
  id: string;
  category: string;
  amount_somoni: number;
  note: string | null;
  spent_at: string;
  created_at: string;
}

export interface BalanceTransactionOut {
  id: string;
  kind: string;
  amount_somoni: number;
  balance_before_somoni: number;
  balance_after_somoni: number;
  actor_name: string | null;
  reason: string | null;
  user_id: string | null;
  user_name: string | null;
  created_at: string;
}

export interface AuditLogEntryOut {
  id: string;
  subject: string;
  event: string;
  actor_kind: string;
  actor_telegram_id: number | null;
  actor_user_id: string | null;
  actor_name: string | null;
  detail: string | null;
  created_at: string;
}

export const paymentsApi = {
  list: (status?: string) =>
    request<AdminPaymentRequestOut[]>(`/admin/payment-requests${qs({ status })}`),
  approve: (id: string, amount_override_somoni?: number, correction_reason?: string) =>
    request<AdminPaymentRequestOut>(`/admin/payment-requests/${id}/approve`, {
      method: "POST",
      body: { amount_override_somoni, correction_reason },
    }),
  reject: (id: string, note?: string) =>
    request<AdminPaymentRequestOut>(`/admin/payment-requests/${id}/reject`, {
      method: "POST",
      body: { note },
    }),
  requestInfo: (id: string, note?: string) =>
    request<AdminPaymentRequestOut>(`/admin/payment-requests/${id}/request-info`, {
      method: "POST",
      body: { note },
    }),
};

export const cardsApi = {
  list: () => request<CardOut[]>("/admin/cards"),
  create: (data: { bank_name: string; holder_name: string; card_number: string; currency?: string; note?: string; is_active?: boolean }) =>
    request<CardOut>("/admin/cards", { method: "POST", body: data }),
  update: (id: string, data: Partial<{ bank_name: string; holder_name: string; card_number: string; currency: string; note: string; is_active: boolean; sort_order: number }>) =>
    request<CardOut>(`/admin/cards/${id}`, { method: "PUT", body: data }),
  remove: (id: string) => request<void>(`/admin/cards/${id}`, { method: "DELETE" }),
};

export const expensesApi = {
  list: (category?: string) => request<ExpenseOut[]>(`/admin/expenses${qs({ category })}`),
  create: (data: { category: string; amount_somoni: number; note?: string; spent_at: string }) =>
    request<ExpenseOut>("/admin/expenses", { method: "POST", body: data }),
  remove: (id: string) => request<void>(`/admin/expenses/${id}`, { method: "DELETE" }),
};

export const ledgerApi = {
  listTransactions: (params: { user_id?: string; kind?: string; limit?: number } = {}) =>
    request<BalanceTransactionOut[]>(`/admin/balance-transactions${qs(params)}`),
  listAuditLog: (params: { event?: string; actor_user_id?: string; limit?: number } = {}) =>
    request<AuditLogEntryOut[]>(`/admin/audit-log${qs(params)}`),
};

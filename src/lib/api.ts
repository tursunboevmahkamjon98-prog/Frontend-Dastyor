const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001/api";


export const API_ORIGIN = API_URL.replace(/\/api\/?$/, "");

const TOKEN_KEY = "teachai_web_token";
const REFRESH_TOKEN_KEY = "teachai_web_refresh_token";
const DEVICE_TOKEN_KEY = "dastyor_web_device_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_KEY, token);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setRefreshToken(token: string) {
  if (typeof window === "undefined") return;
  localStorage.setItem(REFRESH_TOKEN_KEY, token);
}


export function clearToken() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}


export function getDeviceToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(DEVICE_TOKEN_KEY);
}

export function setDeviceToken(token: string) {
  if (typeof window === "undefined") return;
  localStorage.setItem(DEVICE_TOKEN_KEY, token);
}


export function forgetDevice() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(DEVICE_TOKEN_KEY);
}

export class ApiError extends Error {
  
  
  
  
  
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.status = status;
  }
}


function extractError(detail: unknown, status?: number): string {
  if (detail == null && status != null && status >= 502 && status <= 504) {
    return "Сервер не успел ответить (шлюз прервал запрос). Попробуйте ещё раз.";
  }
  if (detail == null) return "Ошибка сервера";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((e) => (e && typeof e === "object" && "msg" in e ? String((e as { msg: unknown }).msg) : String(e)))
      .filter(Boolean);
    return messages.length > 0 ? messages.join("\n") : JSON.stringify(detail);
  }
  if (typeof detail === "object" && "msg" in (detail as object)) {
    return String((detail as { msg: unknown }).msg);
  }
  return String(detail);
}







let refreshInFlight: Promise<boolean> | null = null;

async function refreshTokens(): Promise<boolean> {
  const rt = getRefreshToken();
  if (!rt) return false;
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      try {
        const res = await fetch(`${API_URL}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: rt }),
        });
        if (!res.ok) return false;
        const data = await res.json();
        setToken(data.access_token);
        setRefreshToken(data.refresh_token);
        return true;
      } catch {
        return false;
      } finally {
        refreshInFlight = null;
      }
    })();
  }
  return refreshInFlight;
}

async function request<T>(
  path: string,
  options: { method?: string; body?: unknown; auth?: boolean; signal?: AbortSignal } = {},
  _isRetry = false
): Promise<T> {
  const { method = "GET", body, auth = true, signal } = options;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (err) {
    
    
    
    
    
    if (signal?.aborted) throw err;
    throw new ApiError("Не удалось подключиться к серверу");
  }

  
  
  
  
  
  
  if (response.status === 401 && auth && !_isRetry) {
    const refreshed = await refreshTokens();
    if (refreshed) return request<T>(path, options, true);
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && auth) clearToken();
    throw new ApiError(extractError(data.detail, response.status), response.status);
  }
  return data as T;
}

export interface UserOut {
  id: string;
  full_name: string;
  
  
  email: string | null;
  phone: string | null;
  phone_verified: boolean;
  
  
  
  is_premium: boolean;
  balance_somoni: number;
  avatar_url: string | null;
  language: string;
  role: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: UserOut;
  
  
  
  device_token?: string | null;
}

export type MaterialType = "konspekt" | "lektsiya" | "test" | "prezentatsiya" | "amaliy" | "igra";

export interface DashboardStats {
  konspekt_count: number;
  test_count: number;
  presentation_count: number;
  lecture_count: number;
  practical_count: number;
  game_count: number;
}

export interface MaterialOut {
  id: string;
  title: string;
  subject: string;
  grade: string;
  content?: string | null;
  questions_json?: string | null;
  slides_json?: string | null;
  tasks_json?: string | null;
  game_json?: string | null;
  is_favorite: boolean;
  
  has_undo?: boolean;
  
  time_limit_seconds?: number | null;
  created_at: string;
  updated_at: string;
}



export interface QuizSetQuestion {
  question: string;
  options: string[];
  correct_index: number;
  explanation: string;
}

export interface QuizSetResponse {
  questions: QuizSetQuestion[];
}

export interface GameAttemptOut {
  id: string;
  game_id: string;
  mode: "solo" | "duel";
  score: number;
  score_p1: number | null;
  score_p2: number | null;
  won: boolean;
  rounds_cleared: number;
  total_rounds: number;
  max_streak: number;
  created_at: string;
}

export interface SearchResultItem {
  id: string;
  type: MaterialType;
  title: string;
  subject: string;
  grade: string;
  created_at: string;
}

export interface GenerateResult {
  status: string;
  id: string;
  material_type: MaterialType;
  content: Record<string, unknown>;
}

export interface GenerateAllResult {
  status: string;
  
  
  ids: Partial<Record<MaterialType, string>>;
  content: {
    konspekt?: Record<string, unknown> | null;
    test?: Record<string, unknown> | null;
    prezentatsiya?: Record<string, unknown> | null;
    lektsiya?: Record<string, unknown> | null;
    amaliy?: Record<string, unknown> | null;
    errors?: Partial<Record<MaterialType, string>> | null;
  };
  
  
  skipped?: MaterialType[] | null;
}

const LIST_PATH: Record<MaterialType, string> = {
  konspekt: "/materials/konspekts",
  lektsiya: "/materials/lectures",
  test: "/materials/tests",
  prezentatsiya: "/materials/presentations",
  amaliy: "/materials/practical-tasks",
  igra: "/materials/games",
};






const CONTENT_FIELD_BY_TYPE: Record<MaterialType, "content" | "slides_json" | "questions_json" | "tasks_json" | "game_json"> = {
  konspekt: "content",
  lektsiya: "content",
  prezentatsiya: "slides_json",
  test: "questions_json",
  amaliy: "tasks_json",
  igra: "game_json",
};

export const materialsApi = {
  stats: () => request<DashboardStats>("/materials/stats"),
  search: (q: string) => request<SearchResultItem[]>(`/materials/search?q=${encodeURIComponent(q)}`),
  list: (type: MaterialType, params: { q?: string } = {}) => {
    const qs = params.q ? `?q=${encodeURIComponent(params.q)}` : "";
    return request<MaterialOut[]>(`${LIST_PATH[type]}${qs}`);
  },
  get: (type: MaterialType, id: string) => request<MaterialOut>(`${LIST_PATH[type]}/${id}`),
  
  
  
  
  update: (
    type: MaterialType,
    id: string,
    data: Partial<{
      is_favorite: boolean;
      title: string;
      content: string;
      slides_json: string;
      questions_json: string;
      tasks_json: string;
      game_json: string;
      time_limit_seconds: number | null;
    }>
  ) => request<MaterialOut>(`${LIST_PATH[type]}/${id}`, { method: "PUT", body: data }),
  remove: (type: MaterialType, id: string) => request<void>(`${LIST_PATH[type]}/${id}`, { method: "DELETE" }),
  
  
  
  
  
  
  create: (type: MaterialType, data: Record<string, unknown>) =>
    request<MaterialOut>(LIST_PATH[type], { method: "POST", body: data }),
  
  duplicate: async (type: MaterialType, id: string): Promise<MaterialOut> => {
    const source = await materialsApi.get(type, id);
    const field = CONTENT_FIELD_BY_TYPE[type];
    const body: Record<string, unknown> = {
      title: `${source.title} (копия)`,
      subject: source.subject,
      grade: source.grade,
    };
    const value = (source as unknown as Record<string, unknown>)[field];
    if (value !== undefined) body[field] = value;
    return materialsApi.create(type, body);
  },
  
  undoKonspektContent: (id: string, type: "konspekt" | "lektsiya" = "konspekt") =>
    request<MaterialOut>(`${LIST_PATH[type]}/${id}/undo`, { method: "POST" }),
  
  fetchMissingImage: (id: string, type: "konspekt" | "lektsiya" = "konspekt") =>
    request<MaterialOut>(`${LIST_PATH[type]}/${id}/fetch-image`, { method: "POST" }),
  
  replaceLessonImage: (id: string, index: number, type: "konspekt" | "lektsiya" = "konspekt") =>
    request<MaterialOut>(`${LIST_PATH[type]}/${id}/replace-image`, {
      method: "POST",
      body: { index },
    }),
  
  regenerateKonspektSection: (
    body: {
      topic: string;
      subject: string;
      language: string;
      level: string;
      grade: string;
      section: string;
      existing_content: Record<string, unknown>;
    },
    materialType: "konspekt" | "lektsiya" = "konspekt"
  ) =>
    request<{ status: string; item: Record<string, unknown> }>("/materials/regenerate-item", {
      method: "POST",
      body: { material_type: materialType, item_index: 0, existing_items: [], ...body },
    }),
  
  regeneratePresentationSlide: (body: {
    topic: string;
    subject: string;
    language: string;
    level: string;
    grade: string;
    item_index: number;
    existing_items: Record<string, unknown>[];
  }) =>
    request<{ status: string; item: Record<string, unknown> }>("/materials/regenerate-item", {
      method: "POST",
      body: { material_type: "prezentatsiya", ...body },
    }),
  
  regenerateTestQuestion: (body: {
    topic: string;
    subject: string;
    language: string;
    level: string;
    grade: string;
    item_index: number;
    existing_items: Record<string, unknown>[];
  }) =>
    request<{ status: string; item: Record<string, unknown> }>("/materials/regenerate-item", {
      method: "POST",
      body: { material_type: "test", ...body },
    }),
  
  regeneratePracticalTask: (body: {
    topic: string;
    subject: string;
    language: string;
    level: string;
    grade: string;
    item_index: number;
    existing_items: Record<string, unknown>[];
    kind: "individual_tasks" | "group_tasks";
  }) => {
    const { kind, ...rest } = body;
    return request<{ status: string; item: Record<string, unknown> }>("/materials/regenerate-item", {
      method: "POST",
      body: { material_type: "amaliy", section: kind, ...rest },
    });
  },
  
  rerollGame: (id: string, body: { language?: string; level?: string } = {}) =>
    request<MaterialOut>(`/materials/games/${id}/reroll`, { method: "POST", body }),

  
  generateQuizSet: (body: {
    topic: string;
    subject: string;
    grade?: string;
    level?: string;
    language?: string;
    count?: number;
  }) => request<QuizSetResponse>("/materials/quiz-set", { method: "POST", body }),
  
  submitGameAttempt: (
    gameId: string,
    body: {
      mode: "solo" | "duel";
      score: number;
      score_p1?: number | null;
      score_p2?: number | null;
      won: boolean;
      rounds_cleared: number;
      total_rounds: number;
      max_streak?: number;
    }
  ) => request<GameAttemptOut>(`/materials/games/${gameId}/attempts`, { method: "POST", body }),
  
  listGameAttempts: (gameId: string) => request<GameAttemptOut[]>(`/materials/games/${gameId}/attempts`),
  
  chatEdit: (body: {
    material_type: MaterialType;
    topic: string;
    subject: string;
    language: string;
    level: string;
    grade: string;
    instruction: string;
    content: Record<string, unknown>;
  }) => request<{ status: string; content: Record<string, unknown> }>("/materials/chat-edit", { method: "POST", body }),
  generate: (body: {
    material_type: MaterialType;
    topic: string;
    subject: string;
    language: string;
    level: string;
    grade: string;
    slide_count?: number;
    question_count?: number;
    test_type?: string;
    include_homework?: boolean;
    include_fun_facts?: boolean;
    include_assessment?: boolean;
    
    
    
    template?: string;
  }, signal?: AbortSignal) => request<GenerateResult>("/materials/generate", { method: "POST", body, signal }),
  
  generateAll: (body: {
    topic: string;
    subject: string;
    language: string;
    level: string;
    grade: string;
    slide_count?: number;
    question_count?: number;
    test_type?: string;
    
    types?: MaterialType[];
  }) =>
    request<GenerateAllResult>("/materials/generate-all", { method: "POST", body }),
  
  uploadSource: async (file: File): Promise<{ status: string; text: string; truncated: boolean; filename: string }> => {
    const token = getToken();
    const form = new FormData();
    form.append("file", file);
    const response = await fetch(`${API_URL}/materials/upload-source`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new ApiError(extractError(data.detail));
    return data;
  },
  
  uploadLessonImage: async (
    id: string,
    index: number,
    file: File,
    type: "konspekt" | "lektsiya" = "konspekt"
  ): Promise<MaterialOut> => {
    const token = getToken();
    const form = new FormData();
    form.append("file", file);
    const response = await fetch(`${API_URL}${LIST_PATH[type]}/${id}/upload-image?index=${index}`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new ApiError(extractError(data.detail));
    return data;
  },
};


export type KonspektStreamEvent =
  | { stage: string; status: "start" | "done"; [key: string]: unknown }
  | { type: "token"; delta: string }
  | { type: "field_start" | "field_done"; field: string }
  | { type: "complete"; content: Record<string, unknown>; id: string }
  | { type: "error"; message: string; code: string };

export interface GenerateKonspektStreamBody {
  topic: string;
  subject: string;
  language: string;
  level: string;
  grade: string;
  include_homework: boolean;
  include_fun_facts: boolean;
  include_assessment: boolean;
  generation_mode: "ai" | "source";
  source_text?: string | null;
  
  
  template?: string;
}


export async function streamGenerateKonspekt(
  body: GenerateKonspektStreamBody,
  onEvent: (event: KonspektStreamEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const token = getToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let response: Response;
  try {
    response = await fetch(`${API_URL}/materials/generate-konspekt-stream`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") return;
    throw new ApiError("Не удалось подключиться к серверу");
  }

  if (!response.ok || !response.body) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(extractError(data.detail) || "Не удалось начать генерацию");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      
      
      
      let sepIndex: number;
      while ((sepIndex = buffer.indexOf("\n\n")) !== -1) {
        const frame = buffer.slice(0, sepIndex);
        buffer = buffer.slice(sepIndex + 2);
        const line = frame.split("\n").find((l) => l.startsWith("data:"));
        if (!line) continue;
        const payload = line.slice("data:".length).trim();
        if (!payload) continue;
        try {
          onEvent(JSON.parse(payload) as KonspektStreamEvent);
        } catch {
          
          
        }
      }
    }
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") return;
    throw new ApiError("Соединение прервано во время генерации");
  }
}

const DOWNLOAD_EXT: Record<string, string> = {
  docx: "docx",
  pptx: "pptx",
  pdf: "pdf",
  txt: "txt",
};


export type ExportBody = {
  material_type: MaterialType;
  content: Record<string, unknown>;
  language?: string;
};


export async function fetchMaterialExport(
  format: keyof typeof DOWNLOAD_EXT,
  body: ExportBody
): Promise<Blob> {
  const token = getToken();
  const response = await fetch(`${API_URL}/materials/download-${format}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(extractError(data.detail));
  }
  return response.blob();
}

export async function downloadMaterial(
  format: keyof typeof DOWNLOAD_EXT,
  body: ExportBody
) {
  const blob = await fetchMaterialExport(format, body);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${body.content.title ?? "material"}.${DOWNLOAD_EXT[format]}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}


export async function downloadAllZip(body: {
  topic: string;
  language?: string;
  konspekt?: Record<string, unknown> | null;
  test?: Record<string, unknown> | null;
  prezentatsiya?: Record<string, unknown> | null;
  lektsiya?: Record<string, unknown> | null;
  amaliy?: Record<string, unknown> | null;
}) {
  const token = getToken();
  const response = await fetch(`${API_URL}/materials/download-zip`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(extractError(data.detail));
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${body.topic || "materials"}.zip`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export const authApi = {
  
  
  sendRegisterCode: (phone: string) =>
    request<{ status: string; message: string }>("/auth/register/send-code", {
      method: "POST",
      body: { phone },
      auth: false,
    }),
  register: (full_name: string, phone: string, code: string, password: string) =>
    request<TokenResponse>("/auth/register", { method: "POST", body: { full_name, phone, code, password }, auth: false }),
  
  
  
  
  login: (phone: string, password: string) =>
    request<TokenResponse>("/auth/login", { method: "POST", body: { phone, password }, auth: false }),
  
  
  
  
  loginSendCode: (phone: string, password: string) =>
    request<TokenResponse | { status: string; message: string }>("/auth/login/send-code", {
      method: "POST",
      body: { phone, password, device_token: getDeviceToken() },
      auth: false,
    }),
  
  
  loginVerify: (phone: string, code: string) =>
    request<TokenResponse>("/auth/login/verify", { method: "POST", body: { phone, code }, auth: false }),
  
  
  registerEmail: (full_name: string, email: string, password: string) =>
    request<TokenResponse>("/auth/register-email", { method: "POST", body: { full_name, email, password }, auth: false }),
  loginEmail: (email: string, password: string) =>
    request<TokenResponse>("/auth/login-email", { method: "POST", body: { email, password }, auth: false }),
  
  
  
  google: (credential: string) =>
    request<TokenResponse>("/auth/google", { method: "POST", body: { credential }, auth: false }),
  me: () => request<UserOut>("/auth/me"),
  forgotPassword: (phone: string) =>
    request<{ status: string; message: string }>("/auth/forgot-password", { method: "POST", body: { phone }, auth: false }),
  verifyCode: (phone: string, code: string) =>
    request<{ status: string; message: string }>("/auth/verify-code", { method: "POST", body: { phone, code }, auth: false }),
  resetPassword: (phone: string, code: string, new_password: string) =>
    request<{ status: string; message: string }>("/auth/reset-password", {
      method: "POST",
      body: { phone, code, new_password },
      auth: false,
    }),
  updateMe: (data: { full_name?: string; language?: string }) =>
    request<UserOut>("/auth/me", { method: "PUT", body: data }),
  changePassword: (current_password: string, new_password: string) =>
    request<{ status: string; message: string }>("/auth/change-password", {
      method: "POST",
      body: { current_password, new_password },
    }),
  uploadAvatar: async (file: File): Promise<UserOut> => {
    const token = getToken();
    const form = new FormData();
    form.append("file", file);
    const response = await fetch(`${API_URL}/auth/avatar`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new ApiError(extractError(data.detail));
    return data;
  },
  deleteAvatar: () => request<UserOut>("/auth/avatar", { method: "DELETE" }),
  
  
  
  
  
  
  logout: (refresh_token: string) =>
    request<{ status: string }>("/auth/logout", { method: "POST", body: { refresh_token }, auth: false }),
};

export interface AdminDashboardStats {
  total_users: number;
  total_konspekts: number;
  total_tests: number;
  total_presentations: number;
  total_materials: number;
}

export interface AdminUserOut {
  id: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  role: string;
  
  
  
  is_premium: boolean;
  
  
  
  
  
  balance_somoni: number;
  language: string;
  created_at: string;
  konspekt_count: number;
  test_count: number;
  presentation_count: number;
}

export type AdminUserSort =
  | "created_desc" | "created_asc" | "balance_desc" | "balance_asc"
  | "materials_desc" | "materials_asc" | "name_asc";

export interface AdminListUsersParams {
  q?: string;
  sort?: AdminUserSort;
  premium_only?: boolean;
  admin_only?: boolean;
  limit?: number;
  offset?: number;
}




export interface AdminMaterialOut {
  id: string;
  type: MaterialType;
  title: string;
  subject: string;
  grade: string;
  owner_id: string;
  owner_name: string;
  owner_phone: string | null;
  created_at: string;
}

export interface AdminMaterialsPage {
  items: AdminMaterialOut[];
  total: number;
}

export interface BalanceTransactionOut {
  id: string;
  
  kind: string;
  amount_somoni: number;
  balance_before_somoni: number;
  balance_after_somoni: number;
  
  actor_name: string | null;
  reason: string | null;
  material_type: string | null;
  created_at: string;
}







function qs(params: object): string {
  const parts = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== "")
    .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`);
  return parts.length ? `?${parts.join("&")}` : "";
}




export const adminApi = {
  stats: () => request<AdminDashboardStats>("/admin/stats"),
  listUsers: (params: AdminListUsersParams = {}) =>
    request<AdminUserOut[]>(`/admin/users${qs(params)}`),
  countUsers: (params: Pick<AdminListUsersParams, "q" | "premium_only" | "admin_only"> = {}) =>
    request<{ total: number }>(`/admin/users/count${qs(params)}`),
  setRole: (userId: string, role: "user" | "admin") =>
    request<AdminUserOut>(`/admin/users/${userId}/role`, { method: "PUT", body: { role } }),
  setPremium: (userId: string, is_premium: boolean) =>
    request<AdminUserOut>(`/admin/users/${userId}/premium`, { method: "PUT", body: { is_premium } }),
  addBalance: (userId: string, amount_somoni: number, reason?: string) =>
    request<AdminUserOut>(`/admin/users/${userId}/balance`, {
      method: "PUT",
      body: { amount_somoni, reason },
    }),
  
  
  balanceHistory: (userId: string, params: { limit?: number; offset?: number } = {}) =>
    request<BalanceTransactionOut[]>(`/admin/users/${userId}/balance-history${qs(params)}`),
  removeUser: (userId: string) => request<void>(`/admin/users/${userId}`, { method: "DELETE" }),
  
  
  listMaterials: (params: { type?: MaterialType; q?: string; user_id?: string; limit?: number; offset?: number } = {}) =>
    request<AdminMaterialsPage>(`/admin/materials${qs(params)}`),
  removeMaterial: (type: MaterialType, id: string) =>
    request<void>(`/admin/materials/${type}/${id}`, { method: "DELETE" }),
};






export const billingApi = {
  balance: () => request<{ balance_somoni: number }>("/billing/balance"),
};

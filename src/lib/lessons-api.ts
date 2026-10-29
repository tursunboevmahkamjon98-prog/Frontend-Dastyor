import { ApiError, getToken } from "./api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/api";
export const LESSON_TYPES = ["konspekt", "lektsiya", "prezentatsiya", "test", "amaliy"] as const;
export type LessonType = (typeof LESSON_TYPES)[number];
export interface LessonSummary { subject: string; grade: string; topic: string; material_count: number; last_touched: string; }
export interface LessonMaterialRef { id: string; created_at: string; }
export interface LessonDetail { subject: string; grade: string; topic: string; materials: Record<LessonType, LessonMaterialRef | null>; }
export interface LessonGenerateResult { status: string; id: string; material_type: LessonType; was_free: boolean; balance_somoni: number; }

async function request<T>(path: string, body?: unknown): Promise<T> {
  const token = getToken();
  const response = await fetch(`${API_URL}${path}`, {
    method: body === undefined ? "GET" : "POST",
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(typeof data.detail === "string" ? data.detail : "Request failed", response.status);
  return data as T;
}

export const lessonsApi = {
  list: () => request<LessonSummary[]>("/lessons"),
  detail: (subject: string, grade: string, topic: string) =>
    request<LessonDetail>(`/lessons/materials?subject=${encodeURIComponent(subject)}&grade=${encodeURIComponent(grade)}&topic=${encodeURIComponent(topic)}`),
  generate: (body: { material_type: LessonType; topic: string; subject: string; language: string; level: string; grade: string }) =>
    request<LessonGenerateResult>("/lessons/generate", body),
};
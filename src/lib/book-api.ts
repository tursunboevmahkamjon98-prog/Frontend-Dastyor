import { ApiError, getToken, streamGenerateAll, type GenerateAllBody, type GenerateAllResult } from "./api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/api";

export interface BookSource {
  id: string; title: string; page_count: number;
  chapters: { title: string; start_page: number; end_page: number }[];
  ocr_pages: number; unreadable_pages: number; expires_at: number;
}

export interface BookLibraryItem {
  id: string;
  title: string;
  subject: string;
  extension: string;
  size_bytes: number;
  grade_hint: string | null;
}

export interface BookGenerateBody extends GenerateAllBody {
  source_id: string; scope: "all" | "chapter" | "pages";
  chapter_index?: number; page_start?: number; page_end?: number;
}

export interface BookTopicsStatus {
  status: "pending" | "ready" | "failed" | "unavailable";
  topics: string[] | null;
}

export interface BookAutoSelectResult {
  book: BookLibraryItem;
  source: BookSource;
  topics: BookTopicsStatus;
}

export const bookApi = {
  library: (subject?: string, grade?: string, signal?: AbortSignal): Promise<BookLibraryItem[]> => {
    const params = new URLSearchParams();
    if (subject) params.set("subject", subject);
    if (grade) params.set("grade", grade);
    const query = params.toString() ? `?${params.toString()}` : "";
    const headers: Record<string, string> = {};
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
    return fetch(`${API_URL}/materials/book-library${query}`, {
      headers,
      signal,
      cache: "no-store",
    }).then(async (response) => {
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new ApiError(typeof data.detail === "string" ? data.detail : "Book library failed", response.status);
      return data as BookLibraryItem[];
    });
  },
  autoSelect: async (subject: string, grade: string, signal?: AbortSignal): Promise<BookAutoSelectResult> => {
    const params = new URLSearchParams({ subject, grade });
    const token = getToken();
    const response = await fetch(`${API_URL}/materials/book-library/auto?${params.toString()}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      signal,
      cache: "no-store",
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new ApiError(typeof data.detail === "string" ? data.detail : "Book auto-select failed", response.status);
    return data as BookAutoSelectResult;
  },
  selectLibrary: async (bookId: string): Promise<BookSource & { topics?: BookTopicsStatus }> => {
    const token = getToken();
    const response = await fetch(`${API_URL}/materials/book-library/${encodeURIComponent(bookId)}`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      cache: "no-store",
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new ApiError(typeof data.detail === "string" ? data.detail : "Book selection failed", response.status);
    return data as BookSource & { topics?: BookTopicsStatus };
  },
  topics: async (bookId: string, signal?: AbortSignal): Promise<BookTopicsStatus> => {
    const token = getToken();
    const response = await fetch(`${API_URL}/materials/book-library/${encodeURIComponent(bookId)}/topics`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      signal,
      cache: "no-store",
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new ApiError(typeof data.detail === "string" ? data.detail : "Book topics failed", response.status);
    return data as BookTopicsStatus;
  },
  upload: async (file: File): Promise<BookSource> => {
    const form = new FormData(); form.append("file", file);
    const token = getToken();
    const response = await fetch(`${API_URL}/materials/book-sources`, {
      method: "POST", headers: token ? { Authorization: `Bearer ${token}` } : {}, body: form,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new ApiError(typeof data.detail === "string" ? data.detail : "Book upload failed", response.status);
    return data as BookSource;
  },
  generate: (body: BookGenerateBody, signal?: AbortSignal): Promise<GenerateAllResult> =>
    streamGenerateAll(body, signal, "/materials/generate-from-book-stream"),
};


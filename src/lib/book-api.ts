import { ApiError, getToken, streamGenerateAll, type GenerateAllBody, type GenerateAllResult } from "./api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/api";

export interface BookSource {
  id: string; title: string; page_count: number;
  chapters: { title: string; start_page: number; end_page: number }[];
  ocr_pages: number; unreadable_pages: number; expires_at: number;
}

export interface BookGenerateBody extends GenerateAllBody {
  source_id: string; scope: "all" | "chapter" | "pages";
  chapter_index?: number; page_start?: number; page_end?: number;
}

export const bookApi = {
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


"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { materialsApi, ApiError } from "@/lib/api";
import TestPlayer from "@/components/TestPlayer";

/** The pupil's test-taking page.
 *
 * A route of its own, not a mode inside the teacher's material viewer.
 * The viewer opens a test as something to inspect and edit — its download
 * row, its AI chat-edit box, its per-question time-limit control and its
 * history of past attempts are all teacher tools, and none of them belong
 * on the screen of someone about to answer the questions. This page is a
 * link a teacher can hand over: it loads the test and goes straight into
 * the quiz.
 *
 * It is still an authenticated route — GET /materials/tests/{id} is
 * ownership-checked server-side and answers 404 for anyone else's test,
 * so "hand the link to a pupil" means an account that already has access,
 * not an open URL. Sharing a test with an arbitrary pupil account would
 * need a real sharing model (a share token, or a class roster) on the
 * backend; this page does not invent one client-side.
 */
export default function TestPlayPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = params.id;

  const [item, setItem] = useState<{
    title: string;
    content: Record<string, unknown>;
    timeLimit: number | null;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    materialsApi
      .get("test", id)
      .then((loaded) => {
        let content: Record<string, unknown> = {};
        try {
          content = JSON.parse(loaded.questions_json ?? "{}");
        } catch {
          content = {};
        }
        setItem({
          title: loaded.title,
          content,
          timeLimit: loaded.time_limit_seconds ?? null,
        });
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Не удалось загрузить тест"));
  }, [id]);

  if (error) {
    return (
      <div className="px-4 pt-16 text-center">
        <p className="text-sm text-primary-dark">{error}</p>
        <button
          onClick={() => router.push("/dashboard/materials")}
          className="mt-4 text-sm font-medium text-text-secondary underline"
        >
          К материалам
        </button>
      </div>
    );
  }

  if (!item) {
    return (
      <div className="flex justify-center px-4 pt-20">
        <Loader2 className="h-6 w-6 animate-spin text-text-tertiary" />
      </div>
    );
  }

  const questions = (item.content.questions as unknown[] | undefined) ?? [];
  if (questions.length === 0) {
    return (
      <div className="px-4 pt-16 text-center text-sm text-text-secondary">
        В этом тесте пока нет вопросов.
      </div>
    );
  }

  return (
    <TestPlayer
      content={item.content}
      materialId={id}
      initialTimeLimit={item.timeLimit}
      autoStart
      onExit={() => router.push(`/dashboard/materials/test/${id}`)}
    />
  );
}

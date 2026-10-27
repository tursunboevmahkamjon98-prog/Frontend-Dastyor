"use client";

import { RotateCw } from "lucide-react";
import { getViewerStrings } from "@/lib/content-lang";

interface PracticalTaskItem {
  title?: string;
  difficulty?: string;
  group_size?: string;
  roles?: string[];
  instructions?: string;
  expected_outcome?: string;
}

const DIFFICULTY_STYLE: Record<string, string> = {
  easy: "bg-success/10 text-success",
  medium: "bg-warning/10 text-warning",
  hard: "bg-error/10 text-error",
};

function TaskCard({
  task,
  index,
  kind,
  regenerateTitle,
  onRegenerate,
  regenerating,
}: {
  task: PracticalTaskItem;
  index: number;
  kind: "individual_tasks" | "group_tasks";
  regenerateTitle: string;
  onRegenerate?: (kind: "individual_tasks" | "group_tasks", index: number) => void;
  regenerating: boolean;
}) {
  return (
    <li className="py-5 first:pt-0">
      <div className="mb-2 flex items-start gap-3">
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary-50 text-meta font-semibold text-primary-accent">
          {index + 1}
        </span>
        <p className="min-w-0 flex-1 pt-0.5 text-body font-medium leading-snug text-text-primary">{task.title}</p>
        <div className="flex shrink-0 items-center gap-1.5">
          {task.difficulty && (
            <span
              className={`rounded-full px-2.5 py-0.5 text-micro font-semibold uppercase ${
                DIFFICULTY_STYLE[task.difficulty.toLowerCase()] ?? "bg-surface-muted text-text-secondary"
              }`}
            >
              {task.difficulty}
            </span>
          )}
          {onRegenerate && (
            <button
              onClick={() => onRegenerate(kind, index)}
              disabled={regenerating}
              title={regenerateTitle}
              className="rounded-control p-1.5 text-text-tertiary transition-colors duration-150 hover:bg-surface-muted hover:text-primary-accent disabled:opacity-50"
            >
              <RotateCw className={`h-3.5 w-3.5 ${regenerating ? "animate-spin" : ""}`} />
            </button>
          )}
        </div>
      </div>

      <div className="ml-10">
        {task.group_size && <p className="mb-1.5 text-micro text-text-tertiary">{task.group_size}</p>}
        {task.instructions && <p className="mb-2 text-meta leading-relaxed text-text-secondary">{task.instructions}</p>}
        {(task.roles?.length ?? 0) > 0 && (
          <ul className="mb-2 space-y-1 text-meta text-text-secondary">
            {task.roles!.map((role, j) => (
              <li key={j} className="flex gap-1.5">
                <span className="text-text-tertiary">·</span>
                {role}
              </li>
            ))}
          </ul>
        )}
        {task.expected_outcome && (
          <p className="rounded-control bg-surface-muted px-3 py-2 text-micro text-text-tertiary">{task.expected_outcome}</p>
        )}
      </div>
    </li>
  );
}

/* Redrawn the same way the test viewer was: a numbered sequence with a
 * hairline divider between items instead of every task boxed separately,
 * with individual and group work kept as two clearly labelled runs
 * rather than visually identical cards a teacher has to read the small
 * print of to tell apart.
 */
export default function PracticalViewer({
  content,
  language,
  onRegenerateTask,
  regeneratingTask,
}: {
  content: Record<string, unknown>;
  language?: string | null;
  onRegenerateTask?: (kind: "individual_tasks" | "group_tasks", index: number) => void;
  regeneratingTask?: { kind: "individual_tasks" | "group_tasks"; index: number } | null;
}) {
  const strings = getViewerStrings(language);
  const description = content.description as string | undefined;
  const individual = (content.individual_tasks as PracticalTaskItem[] | undefined) ?? [];
  const group = (content.group_tasks as PracticalTaskItem[] | undefined) ?? [];

  return (
    <div>
      {description && <p className="mb-6 text-meta italic text-text-secondary">{description}</p>}
      {individual.length > 0 && (
        <div className="mb-6">
          <h3 className="mb-1 text-micro font-semibold uppercase tracking-wide text-text-tertiary">
            {strings.individualTasks}
          </h3>
          <ul className="divide-y divide-border-light">
            {individual.map((t, i) => (
              <TaskCard
                key={i}
                task={t}
                index={i}
                kind="individual_tasks"
                regenerateTitle={strings.regenerateTask}
                onRegenerate={onRegenerateTask}
                regenerating={regeneratingTask?.kind === "individual_tasks" && regeneratingTask.index === i}
              />
            ))}
          </ul>
        </div>
      )}
      {group.length > 0 && (
        <div>
          <h3 className="mb-1 text-micro font-semibold uppercase tracking-wide text-text-tertiary">
            {strings.groupTasks}
          </h3>
          <ul className="divide-y divide-border-light">
            {group.map((t, i) => (
              <TaskCard
                key={i}
                task={t}
                index={i}
                kind="group_tasks"
                regenerateTitle={strings.regenerateTask}
                onRegenerate={onRegenerateTask}
                regenerating={regeneratingTask?.kind === "group_tasks" && regeneratingTask.index === i}
              />
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

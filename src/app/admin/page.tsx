"use client";

import { useEffect, useState } from "react";
import { Users, BookOpen, ClipboardCheck, Presentation, Map, Layers } from "lucide-react";
import { adminApi, AdminDashboardStats, ApiError } from "@/lib/api";

const CARDS: { key: keyof AdminDashboardStats; label: string; icon: typeof Users; bg: string; color: string }[] = [
  { key: "total_users", label: "Пользователи", icon: Users, bg: "bg-primary-50", color: "text-primary-dark" },
  { key: "total_konspekts", label: "Конспекты", icon: BookOpen, bg: "bg-note-bg", color: "text-note-icon" },
  { key: "total_tests", label: "Тесты", icon: ClipboardCheck, bg: "bg-test-bg", color: "text-test-icon" },
  { key: "total_presentations", label: "Презентации", icon: Presentation, bg: "bg-pres-bg", color: "text-pres-icon" },
  { key: "total_materials", label: "Всего материалов", icon: Layers, bg: "bg-surface-muted", color: "text-text-secondary" },
];

export default function AdminOverviewPage() {
  const [stats, setStats] = useState<AdminDashboardStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    adminApi
      .stats()
      .then(setStats)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Не удалось загрузить"));
  }, []);

  return (
    <div>
      <h1 className="mb-1 text-2xl font-bold text-text-primary">Обзор</h1>
      <p className="mb-6 text-sm text-text-secondary">Общая статистика по всему сайту</p>

      {error && <p className="text-sm text-primary-dark">{error}</p>}

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {CARDS.map(({ key, label, icon: Icon, bg, color }) => (
          <div key={key} className={`rounded-2xl border border-border-light ${bg} p-4`}>
            <div className={`mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-surface/70 ${color}`}>
              <Icon className="h-4 w-4" />
            </div>
            <p className="text-2xl font-bold text-text-primary">{stats ? stats[key] : "–"}</p>
            <p className="text-xs font-medium text-text-secondary">{label}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

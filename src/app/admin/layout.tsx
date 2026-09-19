"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace("/login");
    } else if (user.role !== "admin") {
      router.replace("/dashboard");
    }
  }, [loading, user, router]);

  if (loading || !user || user.role !== "admin") {
    return (
      <div style={{ padding: 24, font: "13px/1.4 monospace" }}>Загрузка...</div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", background: "#fff", padding: "12px 16px" }}>
      <div style={{ font: "13px/1.4 monospace", marginBottom: 12 }}>
        <Link href="/dashboard" style={{ textDecoration: "underline" }}>
          ← к сайту
        </Link>
      </div>
      {children}
    </div>
  );
}

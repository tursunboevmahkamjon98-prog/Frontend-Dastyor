"use client";

import { useState, FormEvent, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { LogOut, Lock, Languages, ChevronRight, X, Loader2, Camera, Trash2, ShieldCheck, Wallet } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { authApi, ApiError, API_ORIGIN } from "@/lib/api";
import { LANGUAGES } from "@/lib/material-types";
import { useT, useLocale } from "@/lib/i18n";
import { localeFromAccountLanguage } from "@/lib/messages";

const FIELD = "w-full rounded-xl border border-border bg-surface px-4 py-2.5 text-sm text-text-primary outline-none focus:border-primary";

export default function ProfilePage() {
  const t = useT();
  const { user, logout, setUser } = useAuth();
  const router = useRouter();
  const [openModal, setOpenModal] = useState<"password" | "language" | null>(null);

  if (!user) return null;

  return (
    <div className="mx-auto max-w-xl px-4 pt-8 sm:px-6">
      <div className="mb-6 flex flex-col items-center text-center">
        <AvatarUploader user={user} onSaved={setUser} />
        <h1 className="mt-3 text-xl font-bold text-text-primary">{user.full_name}</h1>
        <p className="text-sm text-text-secondary">{user.phone ?? user.email}</p>
        <span className="mt-2 rounded-full bg-primary-50 px-3 py-1 text-xs font-semibold text-primary-dark">
          {t("profile.teacher")}
        </span>
      </div>

      {}
      <Link
        href="/dashboard/billing"
        className="mb-6 flex items-center gap-4 rounded-2xl border border-border-light bg-surface p-4 transition hover:shadow-sm"
      >
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary-50">
          <Wallet className="h-5 w-5 text-primary" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs text-text-tertiary">{t("billing.current")}</p>
          <p className="text-xl font-bold text-text-primary">
            {user.balance_somoni.toFixed(2)} {t("nav.somoni")}
          </p>
        </div>
        {}
        <span className="shrink-0 rounded-xl bg-primary-50 px-4 py-2.5 text-xs font-semibold text-primary-dark">
          {t("billing.soon")}
        </span>
      </Link>

      <div className="mb-6 divide-y divide-border-light overflow-hidden rounded-2xl border border-border-light bg-surface">
        <MenuRow icon={Lock} label={t("profile.password")} onClick={() => setOpenModal("password")} />
        <MenuRow icon={Languages} label={t("profile.language")} value={user.language} onClick={() => setOpenModal("language")} />
      </div>

      {}
      {user.role === "admin" && (
        <Link
          href="/admin"
          className="mb-6 flex w-full items-center gap-3 rounded-2xl border border-primary/30 bg-primary-50 p-4 hover:shadow-sm"
        >
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary text-white">
            <ShieldCheck className="h-4 w-4" />
          </div>
          <span className="flex-1 text-left text-sm font-semibold text-primary-dark">{t("profile.adminPanel")}</span>
          <ChevronRight className="h-4 w-4 text-primary-dark" />
        </Link>
      )}

      <button
        onClick={() => {
          logout();
          router.push("/login");
        }}
        className="flex w-full items-center justify-center gap-2 rounded-xl border border-primary/30 py-3 text-sm font-semibold text-primary hover:bg-primary-50"
      >
        <LogOut className="h-4 w-4" />
        {t("profile.logout")}
      </button>

      {}
      <p className="mt-6 text-center text-xs text-text-tertiary">
        <Link href="/terms" className="underline hover:text-primary">
          {t("register.terms")}
        </Link>
        {"  ·  "}
        <Link href="/privacy" className="underline hover:text-primary">
          {t("register.privacy")}
        </Link>
      </p>

      {openModal === "password" && <PasswordModal onClose={() => setOpenModal(null)} />}
      {openModal === "language" && (
        <LanguageModal current={user.language} onClose={() => setOpenModal(null)} onSaved={setUser} />
      )}
    </div>
  );
}


function AvatarUploader({
  user,
  onSaved,
}: {
  user: import("@/lib/api").UserOut;
  onSaved: (u: import("@/lib/api").UserOut) => void;
}) {
  const t = useT();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const src = user.avatar_url ? (user.avatar_url.startsWith("http") ? user.avatar_url : `${API_ORIGIN}${user.avatar_url}`) : null;
  const initials = user.full_name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");

  async function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = ""; 
    if (!file) return;
    setError(null);
    setBusy(true);
    try {
      const updated = await authApi.uploadAvatar(file);
      onSaved(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("profile.photoUploadFailed"));
    } finally {
      setBusy(false);
    }
  }

  async function onRemove() {
    setError(null);
    setBusy(true);
    try {
      const updated = await authApi.deleteAvatar();
      onSaved(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("profile.photoRemoveFailed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col items-center">
      <div className="relative h-24 w-24">
        <div className="flex h-24 w-24 items-center justify-center overflow-hidden rounded-full bg-primary-50 text-2xl font-bold text-primary-dark">
          {src ? (
            
            
            
            <img src={src} alt="" className="h-full w-full object-cover" />
          ) : (
            initials || "?"
          )}
        </div>
        {busy && (
          <div className="absolute inset-0 flex items-center justify-center rounded-full bg-black/40">
            <Loader2 className="h-5 w-5 animate-spin text-white" />
          </div>
        )}
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={busy}
          aria-label={t("profile.changePhoto")}
          className="absolute -bottom-1 -right-1 flex h-8 w-8 items-center justify-center rounded-full border-2 border-surface bg-primary text-white shadow-sm hover:bg-primary-dark disabled:opacity-60"
        >
          <Camera className="h-3.5 w-3.5" />
        </button>
        {src && !busy && (
          <button
            type="button"
            onClick={onRemove}
            aria-label={t("profile.removePhoto")}
            className="absolute -bottom-1 -left-1 flex h-8 w-8 items-center justify-center rounded-full border-2 border-surface bg-surface text-text-tertiary shadow-sm hover:text-primary"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        )}
        <input ref={fileInputRef} type="file" accept=".jpg,.jpeg,.png,.webp" className="hidden" onChange={onFileChange} />
      </div>
      {error && <p className="mt-2 text-xs text-primary-dark">{error}</p>}
    </div>
  );
}

function MenuRow({
  icon: Icon,
  label,
  value,
  onClick,
}: {
  icon: typeof Lock;
  label: string;
  value?: string;
  onClick: () => void;
}) {
  return (
    <button onClick={onClick} className="flex w-full items-center gap-3 p-4 text-left hover:bg-surface-muted">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary-50">
        <Icon className="h-4 w-4 text-primary" />
      </div>
      <span className="flex-1 text-sm font-medium text-text-primary">{label}</span>
      {value && <span className="text-xs text-text-tertiary">{value}</span>}
      <ChevronRight className="h-4 w-4 text-text-tertiary" />
    </button>
  );
}

function ModalShell({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-30 flex items-end justify-center bg-black/40 p-0 sm:items-center sm:p-4">
      <div className="w-full max-w-sm rounded-t-3xl bg-surface p-6 sm:rounded-3xl">
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-lg font-bold text-text-primary">{title}</h2>
          <button onClick={onClose} className="text-text-tertiary">
            <X className="h-5 w-5" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

function PasswordModal({ onClose }: { onClose: () => void }) {
  const t = useT();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (next.length < 6) {
      setError(t("register.passwordTooShort"));
      return;
    }
    setSubmitting(true);
    try {
      await authApi.changePassword(current, next);
      setSuccess(true);
      setTimeout(onClose, 1200);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("common.error"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <ModalShell title={t("profile.changePassword")} onClose={onClose}>
      {success ? (
        <p className="rounded-xl bg-primary-50 px-4 py-3 text-sm text-primary-dark">{t("profile.passwordChanged")}</p>
      ) : (
        <form onSubmit={onSubmit} className="space-y-4">
          {error && <div className="rounded-xl bg-primary-50 px-4 py-3 text-sm text-primary-dark">{error}</div>}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-text-secondary">{t("profile.currentPassword")}</label>
            <input type="password" required value={current} onChange={(e) => setCurrent(e.target.value)} className={FIELD} />
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-medium text-text-secondary">{t("forgot.newPassword")}</label>
            <input type="password" required minLength={6} value={next} onChange={(e) => setNext(e.target.value)} className={FIELD} />
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-xl bg-primary py-2.5 text-sm font-semibold text-white hover:bg-primary-dark disabled:opacity-60"
          >
            {submitting ? t("profile.saving") : t("profile.save")}
          </button>
        </form>
      )}
    </ModalShell>
  );
}

function LanguageModal({
  current,
  onClose,
  onSaved,
}: {
  current: string;
  onClose: () => void;
  onSaved: (u: import("@/lib/api").UserOut) => void;
}) {
  const t = useT();
  
  
  
  
  const { setLocale } = useLocale();
  const [saving, setSaving] = useState<string | null>(null);

  async function pick(lang: string) {
    setSaving(lang);
    try {
      const updated = await authApi.updateMe({ language: lang });
      onSaved(updated);
      setLocale(localeFromAccountLanguage(lang));
      onClose();
    } finally {
      setSaving(null);
    }
  }

  return (
    <ModalShell title={t("profile.materialLanguage")} onClose={onClose}>
      <p className="mb-3 text-xs text-text-tertiary">{t("profile.languageHint")}</p>
      <div className="space-y-2">
        {LANGUAGES.map((lang) => (
          <button
            key={lang}
            onClick={() => pick(lang)}
            disabled={saving !== null}
            className={`flex w-full items-center justify-between rounded-xl border px-4 py-3 text-left text-sm font-medium transition ${
              current === lang ? "border-primary bg-primary-50 text-primary-dark" : "border-border bg-surface text-text-primary"
            }`}
          >
            {lang}
            {saving === lang && <Loader2 className="h-4 w-4 animate-spin" />}
          </button>
        ))}
      </div>
    </ModalShell>
  );
}

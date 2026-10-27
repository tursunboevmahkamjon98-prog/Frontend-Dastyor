"use client";

import { useEffect, useState, FormEvent, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  LogOut, Lock, Languages, ChevronRight, X, Loader2, Camera, Trash2, ShieldCheck, Wallet,
  Layers, Pencil, BadgeCheck, Info,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { authApi, materialsApi, ApiError, API_ORIGIN, type DashboardStats, type UserOut } from "@/lib/api";
import { LANGUAGES } from "@/lib/material-types";
import { useT, useLocale } from "@/lib/i18n";
import { localeFromAccountLanguage } from "@/lib/messages";

const FIELD = "w-full rounded-xl border border-border bg-surface px-4 py-2.5 text-sm text-text-primary outline-none focus:border-primary";

const LOCALE_TAG: Record<string, string> = { ru: "ru-RU", tg: "tg-TJ", en: "en-GB" };

/* The teacher's account, redesigned from a single centred column into a
 * page with an actual layout.
 *
 * Everything shown is real: the material count is the same /materials/stats
 * the dashboard home already calls, "verified" only appears when the
 * server's own phone_verified says so, and "premium" reads the same
 * is_premium flag admins set. Nothing here is a number invented for the
 * sake of having three stat tiles to show.
 */
export default function ProfilePage() {
  const t = useT();
  const { locale } = useLocale();
  const { user, logout, setUser } = useAuth();
  const router = useRouter();
  const [openModal, setOpenModal] = useState<"password" | "language" | "name" | null>(null);
  const [stats, setStats] = useState<DashboardStats | null>(null);

  useEffect(() => {
    materialsApi.stats().then(setStats).catch(() => {});
  }, []);

  if (!user) return null;

  const totalMaterials = stats
    ? stats.konspekt_count + stats.lecture_count + stats.test_count + stats.presentation_count + stats.practical_count
    : null;

  const memberSince = new Date(user.created_at).toLocaleDateString(LOCALE_TAG[locale] ?? "ru-RU", {
    year: "numeric",
    month: "long",
  });

  return (
    <div className="mx-auto w-full max-w-[960px] px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
      {/* Hero */}
      <div className="mb-5 flex flex-col gap-5 rounded-card border border-border-light bg-surface p-5 sm:flex-row sm:items-center sm:p-7">
        <AvatarUploader user={user} onSaved={setUser} />

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-heading font-semibold text-text-primary">{user.full_name}</h1>
            <span className="rounded-full bg-primary-50 px-2.5 py-1 text-micro font-semibold text-primary-accent">
              {t("profile.teacher")}
            </span>
          </div>
          <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-meta text-text-secondary">
            <span>{user.phone ?? user.email}</span>
            {user.phone_verified && (
              <span className="flex items-center gap-1 text-success">
                <BadgeCheck className="h-3.5 w-3.5" strokeWidth={2} />
                {t("profile.verified")}
              </span>
            )}
          </div>
        </div>

        <button
          type="button"
          onClick={() => setOpenModal("name")}
          className="flex shrink-0 items-center gap-1.5 self-start rounded-control border border-border px-3.5 py-2 text-meta font-semibold text-text-primary transition-colors duration-150 hover:bg-surface-muted sm:self-center"
        >
          <Pencil className="h-3.5 w-3.5" strokeWidth={2} />
          {t("profile.editProfile")}
        </button>
      </div>

      {/* Account overview */}
      <div className="mb-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Link
          href="/dashboard/billing"
          className="group flex items-center gap-3 rounded-card border border-border-light bg-surface p-4 transition-colors duration-150 hover:border-border"
        >
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-control bg-secondary-50">
            <Wallet className="h-4.5 w-4.5 text-secondary-accent" strokeWidth={2} />
          </span>
          <span className="min-w-0 flex-1">
            <span className="block text-micro text-text-tertiary">{t("billing.current")}</span>
            <span className="block text-body font-semibold tabular-nums text-text-primary">
              {user.balance_somoni.toFixed(2)} {t("nav.somoni")}
            </span>
          </span>
          <ChevronRight className="h-4 w-4 shrink-0 text-text-tertiary opacity-0 transition-opacity duration-150 group-hover:opacity-100" />
        </Link>

        <div className="flex items-center gap-3 rounded-card border border-border-light bg-surface p-4">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-control bg-note-bg">
            <Layers className="h-4.5 w-4.5 text-note-icon" strokeWidth={2} />
          </span>
          <span className="min-w-0 flex-1">
            <span className="block text-micro text-text-tertiary">{t("home.totalLabel")}</span>
            <span className="block text-body font-semibold tabular-nums text-text-primary">
              {totalMaterials === null ? "—" : totalMaterials}
            </span>
          </span>
        </div>

        <div className="flex items-center gap-3 rounded-card border border-border-light bg-surface p-4">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-control bg-amaliy-bg">
            <ShieldCheck className="h-4.5 w-4.5 text-amaliy-icon" strokeWidth={2} />
          </span>
          <span className="min-w-0 flex-1">
            <span className="block text-micro text-text-tertiary">{t("profile.accountStatus")}</span>
            <span className="block text-body font-semibold text-text-primary">
              {user.is_premium ? t("profile.statusPremium") : t("profile.statusStandard")}
            </span>
          </span>
        </div>
      </div>

      {/* Settings */}
      <div className="mb-5 grid gap-3 sm:grid-cols-2">
        <SettingCard
          icon={Lock}
          title={t("profile.security")}
          desc={t("profile.securityDesc")}
          onClick={() => setOpenModal("password")}
        />
        <SettingCard
          icon={Languages}
          title={t("profile.language")}
          desc={user.language}
          onClick={() => setOpenModal("language")}
        />
      </div>

      <div className="mb-5 rounded-card border border-border-light bg-surface p-5 sm:p-6">
        <div className="mb-3 flex items-center gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-control bg-primary-50">
            <Info className="h-4.5 w-4.5 text-primary-accent" strokeWidth={2} />
          </span>
          <h2 className="text-body font-semibold text-text-primary">{t("profile.accountInfo")}</h2>
        </div>
        <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
          <InfoRow label={t("login.phone")} value={user.phone ?? "—"} />
          <InfoRow label={t("register.email")} value={user.email ?? "—"} />
          <InfoRow label={t("profile.memberSince")} value={memberSince} />
        </dl>
      </div>

      {user.role === "admin" && (
        <Link
          href="/admin"
          className="mb-5 flex w-full items-center gap-3 rounded-card border border-primary/30 bg-primary-50 p-4 transition-colors duration-150 hover:bg-primary-50/70"
        >
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-control bg-primary text-white">
            <ShieldCheck className="h-4 w-4" strokeWidth={2} />
          </span>
          <span className="flex-1 text-left text-meta font-semibold text-primary-accent">{t("profile.adminPanel")}</span>
          <ChevronRight className="h-4 w-4 text-primary-accent" />
        </Link>
      )}

      <button
        onClick={() => {
          logout();
          router.push("/login");
        }}
        className="flex w-full items-center justify-center gap-2 rounded-xl border border-primary/30 py-3 text-sm font-semibold text-primary-accent transition-colors duration-150 hover:bg-primary-50"
      >
        <LogOut className="h-4 w-4" strokeWidth={2} />
        {t("profile.logout")}
      </button>

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
      {openModal === "name" && (
        <NameModal current={user.full_name} onClose={() => setOpenModal(null)} onSaved={setUser} />
      )}
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-micro text-text-tertiary">{label}</dt>
      <dd className="mt-0.5 truncate text-meta font-medium text-text-primary">{value}</dd>
    </div>
  );
}

function SettingCard({
  icon: Icon,
  title,
  desc,
  onClick,
}: {
  icon: typeof Lock;
  title: string;
  desc: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex items-center gap-3 rounded-card border border-border-light bg-surface p-4 text-left transition-colors duration-150 hover:border-border hover:bg-surface-muted"
    >
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-control bg-primary-50">
        <Icon className="h-4.5 w-4.5 text-primary-accent" strokeWidth={2} />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-meta font-semibold text-text-primary">{title}</span>
        <span className="block truncate text-micro text-text-tertiary">{desc}</span>
      </span>
      <ChevronRight className="h-4 w-4 shrink-0 text-text-tertiary" />
    </button>
  );
}

function AvatarUploader({
  user,
  onSaved,
}: {
  user: UserOut;
  onSaved: (u: UserOut) => void;
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
    <div className="flex shrink-0 flex-col items-center">
      <div className="relative h-28 w-28">
        <div className="flex h-28 w-28 items-center justify-center overflow-hidden rounded-full bg-primary-50 text-title font-semibold text-primary-accent">
          {src ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={src} alt="" className="h-full w-full object-cover" />
          ) : (
            initials || "?"
          )}
        </div>
        {busy && (
          <div className="absolute inset-0 flex items-center justify-center rounded-full bg-text-primary/40">
            <Loader2 className="h-5 w-5 animate-spin text-white" />
          </div>
        )}
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={busy}
          aria-label={t("profile.changePhoto")}
          className="absolute -bottom-1 -right-1 flex h-9 w-9 items-center justify-center rounded-full border-2 border-surface bg-primary text-white shadow-card transition-colors duration-150 hover:bg-primary-dark disabled:opacity-60"
        >
          <Camera className="h-4 w-4" strokeWidth={2} />
        </button>
        {src && !busy && (
          <button
            type="button"
            onClick={onRemove}
            aria-label={t("profile.removePhoto")}
            className="absolute -bottom-1 -left-1 flex h-9 w-9 items-center justify-center rounded-full border-2 border-surface bg-surface text-text-tertiary shadow-card transition-colors duration-150 hover:text-primary-accent"
          >
            <Trash2 className="h-4 w-4" strokeWidth={2} />
          </button>
        )}
        <input ref={fileInputRef} type="file" accept=".jpg,.jpeg,.png,.webp" className="hidden" onChange={onFileChange} />
      </div>
      {error && <p className="mt-2 max-w-[8rem] text-center text-micro text-error">{error}</p>}
    </div>
  );
}

function ModalShell({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-30 flex items-end justify-center bg-text-primary/40 p-0 sm:items-center sm:p-4">
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

function NameModal({
  current,
  onClose,
  onSaved,
}: {
  current: string;
  onClose: () => void;
  onSaved: (u: UserOut) => void;
}) {
  const t = useT();
  const [name, setName] = useState(current);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    setError(null);
    setSubmitting(true);
    try {
      const updated = await authApi.updateMe({ full_name: trimmed });
      onSaved(updated);
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("common.error"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <ModalShell title={t("profile.editProfile")} onClose={onClose}>
      <form onSubmit={onSubmit} className="space-y-4">
        {error && <div className="rounded-control border border-error/30 bg-error/10 px-4 py-3 text-sm text-error">{error}</div>}
        <div>
          <label className="mb-1.5 block text-sm font-medium text-text-secondary">{t("register.fullName")}</label>
          <input required value={name} onChange={(e) => setName(e.target.value)} className={FIELD} autoFocus />
        </div>
        <button
          type="submit"
          disabled={submitting || !name.trim()}
          className="w-full rounded-xl bg-primary py-2.5 text-sm font-semibold text-white transition-colors duration-150 hover:bg-primary-dark disabled:opacity-60"
        >
          {submitting ? t("profile.saving") : t("profile.save")}
        </button>
      </form>
    </ModalShell>
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
        <p className="rounded-control border border-success/30 bg-success/10 px-4 py-3 text-sm text-success">{t("profile.passwordChanged")}</p>
      ) : (
        <form onSubmit={onSubmit} className="space-y-4">
          {error && <div className="rounded-control border border-error/30 bg-error/10 px-4 py-3 text-sm text-error">{error}</div>}
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
  onSaved: (u: UserOut) => void;
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

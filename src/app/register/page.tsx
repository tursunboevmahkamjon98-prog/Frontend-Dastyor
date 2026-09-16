"use client";

import { useState, FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth, ApiError } from "@/lib/auth-context";
import { authApi } from "@/lib/api";
import AuthLayout from "@/components/AuthLayout";
import { useT } from "@/lib/i18n";
import GoogleSignInButton from "@/components/GoogleSignInButton";
import PhoneInput from "@/components/PhoneInput";










type Step = "form" | "otp";

export default function RegisterPage() {
  const t = useT();
  const { register, loginWithGoogle } = useAuth();
  const router = useRouter();
  const [step, setStep] = useState<Step>("form");
  const [fullName, setFullName] = useState("");
  const [digits, setDigits] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const phone = `+992${digits}`;

  function fail(err: unknown) {
    setError(err instanceof ApiError ? err.message : t("common.error"));
  }

  async function onSubmitForm(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (password.length < 6) {
      setError(t("register.passwordTooShort"));
      return;
    }
    setSubmitting(true);
    try {
      await authApi.sendRegisterCode(phone);
      setStep("otp");
    } catch (err) {
      fail(err);
    } finally {
      setSubmitting(false);
    }
  }

  async function onSubmitCode(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await register(fullName.trim(), phone, code.trim(), password);
      router.push("/dashboard");
    } catch (err) {
      fail(err);
    } finally {
      setSubmitting(false);
    }
  }

  async function onGoogleCredential(credential: string) {
    setError(null);
    setSubmitting(true);
    try {
      await loginWithGoogle(credential);
      router.push("/dashboard");
    } catch (err) {
      fail(err);
    } finally {
      setSubmitting(false);
    }
  }

  const inputClass =
    "w-full rounded-xl border border-border bg-surface px-4 py-2.5 text-sm text-text-primary outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/10";

  return (
    <AuthLayout illustration="/auth-illustration-register.svg">
      <div className="mb-8 lg:text-left">
        {}
        <img src="/logo.png" alt="Dastyor" className="mb-4 h-11 w-11 lg:hidden" />
        <h1 className="text-2xl font-bold text-text-primary sm:text-3xl">
          {step === "form" ? t("register.title") : t("register.otpTitle")}
        </h1>
        <p className="mt-1.5 text-sm text-text-secondary">
          {step === "form" ? t("register.subtitle") : `${t("login.otpSubtitle")} ${phone}`}
        </p>
      </div>

      <div className="rounded-[1.75rem] border border-border-light bg-surface p-6 shadow-xl shadow-black/[0.05] sm:p-7">
        {error && <div className="mb-4 rounded-xl bg-primary-50 px-4 py-3 text-sm text-primary-dark">{error}</div>}

        {step === "form" ? (
          <>
            <GoogleSignInButton onCredential={onGoogleCredential} onError={setError} />

            <form onSubmit={onSubmitForm} className="space-y-4">
              <div>
                <label className="mb-1.5 block text-sm font-medium text-text-secondary">{t("register.fullName")}</label>
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className={inputClass}
                  placeholder={t("register.fullNamePlaceholder")}
                />
              </div>

              <div>
                <label className="mb-1.5 block text-sm font-medium text-text-secondary">{t("login.phone")}</label>
                <PhoneInput value={digits} onChange={setDigits} />
              </div>

              <div>
                <label className="mb-1.5 block text-sm font-medium text-text-secondary">{t("login.password")}</label>
                <input
                  type="password"
                  required
                  minLength={6}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={inputClass}
                  placeholder={t("register.passwordPlaceholder")}
                />
              </div>

              <button
                type="submit"
                disabled={submitting || digits.length !== 9}
                className="w-full rounded-xl bg-primary py-2.5 text-sm font-semibold text-white shadow-lg shadow-primary/25 transition hover:-translate-y-0.5 hover:bg-primary-dark disabled:pointer-events-none disabled:opacity-60 disabled:hover:translate-y-0"
              >
                {submitting ? t("forgot.sending") : t("forgot.send")}
              </button>
            </form>
          </>
        ) : (
          <form onSubmit={onSubmitCode} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-text-secondary">{t("login.code")}</label>
              <input
                type="text"
                inputMode="numeric"
                required
                autoFocus
                maxLength={6}
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                className={`${inputClass} text-center text-xl font-semibold tracking-[0.4em]`}
                placeholder="000000"
              />
            </div>

            <button
              type="submit"
              disabled={submitting || code.length !== 6}
              className="w-full rounded-xl bg-primary py-2.5 text-sm font-semibold text-white shadow-lg shadow-primary/25 transition hover:-translate-y-0.5 hover:bg-primary-dark disabled:pointer-events-none disabled:opacity-60 disabled:hover:translate-y-0"
            >
              {submitting ? t("register.submitting") : t("register.submit")}
            </button>

            <button
              type="button"
              onClick={() => {
                setStep("form");
                setCode("");
                setError(null);
              }}
              className="w-full text-sm font-medium text-text-secondary hover:text-text-primary"
            >
              {t("common.back")}
            </button>
          </form>
        )}
      </div>

      {}
      <p className="mt-5 text-center text-xs leading-relaxed text-text-tertiary">
        {t("register.agree")}{" "}
        <Link href="/terms" className="underline hover:text-primary">
          {t("register.terms")}
        </Link>{" "}
        {t("register.and")}{" "}
        <Link href="/privacy" className="underline hover:text-primary">
          {t("register.privacy")}
        </Link>
      </p>

      <p className="mt-4 text-center text-sm text-text-secondary">
        {t("register.haveAccount")}{" "}
        <Link href="/login" className="font-semibold text-primary hover:underline">
          {t("register.login")}
        </Link>
      </p>
    </AuthLayout>
  );
}

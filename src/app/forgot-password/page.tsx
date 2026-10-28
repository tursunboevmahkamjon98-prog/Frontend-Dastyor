"use client";

import { useState, FormEvent, useEffect, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { authApi } from "@/lib/api";
import { ApiError } from "@/lib/auth-context";
import AuthLayout from "@/components/AuthLayout";
import { useT } from "@/lib/i18n";
import PhoneInput from "@/components/PhoneInput";

type Step = "phone" | "code" | "password";

export default function ForgotPasswordPage() {
  const t = useT();
  const router = useRouter();
  const [step, setStep] = useState<Step>("phone");
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  function startCooldown() {
    setCooldown(60);
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      setCooldown((c) => {
        if (c <= 1 && timerRef.current) clearInterval(timerRef.current);
        return c - 1;
      });
    }, 1000);
  }

  async function submitPhone(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await authApi.forgotPassword(`+992${phone}`);
      startCooldown();
      setStep("code");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("common.error"));
    } finally {
      setSubmitting(false);
    }
  }

  async function resendCode() {
    if (cooldown > 0) return;
    setError(null);
    try {
      await authApi.forgotPassword(`+992${phone}`);
      startCooldown();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("common.error"));
    }
  }

  async function submitCode(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await authApi.verifyCode(`+992${phone}`, code);
      setStep("password");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("common.error"));
    } finally {
      setSubmitting(false);
    }
  }

  async function submitNewPassword(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (newPassword.length < 6) {
      setError(t("register.passwordTooShort"));
      return;
    }
    setSubmitting(true);
    try {
      await authApi.resetPassword(`+992${phone}`, code, newPassword);
      router.push("/login");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("common.error"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout>
        <div className="mb-8 lg:text-left">
          {}
          <img src="/logo.png" alt="Dastyor" className="mb-4 h-11 w-11 lg:hidden" />
          <h1 className="text-2xl font-bold text-text-primary sm:text-3xl">{t("forgot.title")}</h1>
          <p className="mt-1.5 text-sm text-text-secondary">
            {step === "phone" && t("forgot.stepPhone")}
            {step === "code" && t("forgot.stepCode")}
            {step === "password" && t("forgot.stepPassword")}
          </p>
        </div>

        <div className="rounded-2xl border border-border-light bg-surface p-6 shadow-sm shadow-black/[0.03]">
          {error && (
            <div className="mb-4 rounded-xl bg-primary-50 px-4 py-3 text-sm text-primary-dark">{error}</div>
          )}

          {step === "phone" && (
            <form onSubmit={submitPhone} className="space-y-4">
              <div>
                <label className="mb-1.5 block text-sm font-medium text-text-secondary">{t("login.phone")}</label>
                <PhoneInput value={phone} onChange={setPhone} autoFocus />
              </div>
              <button
                type="submit"
                disabled={submitting || phone.length !== 9}
                className="w-full rounded-xl bg-primary py-2.5 text-sm font-semibold text-white transition hover:bg-primary-dark disabled:opacity-60"
              >
                {submitting ? t("forgot.sending") : t("forgot.send")}
              </button>
            </form>
          )}

          {step === "code" && (
            <form onSubmit={submitCode} className="space-y-4">
              <div>
                <label className="mb-1.5 block text-sm font-medium text-text-secondary">{t("forgot.code")}</label>
                <input
                  type="text"
                  required
                  inputMode="numeric"
                  maxLength={6}
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                  className="w-full rounded-xl border border-border bg-surface px-4 py-2.5 text-center text-lg tracking-[0.5em] text-text-primary outline-none focus:border-primary"
                  placeholder="000000"
                />
              </div>
              <button
                type="submit"
                disabled={submitting || code.length !== 6}
                className="w-full rounded-xl bg-primary py-2.5 text-sm font-semibold text-white transition hover:bg-primary-dark disabled:opacity-60"
              >
                {submitting ? t("forgot.checking") : t("login.verify")}
              </button>
              <button
                type="button"
                onClick={resendCode}
                disabled={cooldown > 0}
                className="w-full text-sm font-medium text-primary disabled:text-text-tertiary"
              >
                {cooldown > 0 ? `${t("forgot.resend")} (${cooldown})` : t("forgot.resend")}
              </button>
            </form>
          )}

          {step === "password" && (
            <form onSubmit={submitNewPassword} className="space-y-4">
              <div>
                <label className="mb-1.5 block text-sm font-medium text-text-secondary">{t("forgot.newPassword")}</label>
                <input
                  type="password"
                  required
                  minLength={6}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full rounded-xl border border-border bg-surface px-4 py-2.5 text-sm text-text-primary outline-none focus:border-primary"
                  placeholder={t("register.passwordPlaceholder")}
                />
              </div>
              <button
                type="submit"
                disabled={submitting}
                className="w-full rounded-xl bg-primary py-2.5 text-sm font-semibold text-white transition hover:bg-primary-dark disabled:opacity-60"
              >
                {submitting ? t("forgot.saving") : t("forgot.save")}
              </button>
            </form>
          )}
        </div>

        <p className="mt-6 text-center text-sm text-text-secondary">
          <Link href="/login" className="font-semibold text-primary hover:underline">
            {t("forgot.backToLogin")}
          </Link>
        </p>
    </AuthLayout>
  );
}

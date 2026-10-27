"use client";

import { useState, FormEvent, useEffect, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { authApi } from "@/lib/api";
import { ApiError } from "@/lib/auth-context";
import AuthLayout from "@/components/AuthLayout";
import { AuthCard, AuthHeading, ErrorNote, Field, SubmitButton, inputClass } from "@/components/ui";
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
      <AuthHeading
        title={t("forgot.title")}
        subtitle={
          step === "phone"
            ? t("forgot.stepPhone")
            : step === "code"
              ? t("forgot.stepCode")
              : t("forgot.stepPassword")
        }
      />

      <AuthCard>
        {error && <ErrorNote>{error}</ErrorNote>}

        {step === "phone" && (
          <form onSubmit={submitPhone} className="space-y-4">
            <Field label={t("login.phone")}>
              <PhoneInput value={phone} onChange={setPhone} autoFocus />
            </Field>
            <SubmitButton disabled={submitting || phone.length !== 9}>
              {submitting ? t("forgot.sending") : t("forgot.send")}
            </SubmitButton>
          </form>
        )}

        {step === "code" && (
          <form onSubmit={submitCode} className="space-y-4">
            <Field label={t("forgot.code")}>
              <input
                type="text"
                required
                inputMode="numeric"
                maxLength={6}
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                className={`${inputClass} text-center text-heading font-semibold tracking-[0.4em]`}
                placeholder="000000"
              />
            </Field>
            <SubmitButton disabled={submitting || code.length !== 6}>
              {submitting ? t("forgot.checking") : t("login.verify")}
            </SubmitButton>
            <button
              type="button"
              onClick={resendCode}
              disabled={cooldown > 0}
              className="w-full text-meta font-medium text-primary-accent transition-colors duration-150 hover:text-primary-dark disabled:text-text-tertiary"
            >
              {cooldown > 0 ? `${t("forgot.resend")} (${cooldown})` : t("forgot.resend")}
            </button>
          </form>
        )}

        {step === "password" && (
          <form onSubmit={submitNewPassword} className="space-y-4">
            <Field label={t("forgot.newPassword")}>
              <input
                type="password"
                required
                minLength={6}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className={inputClass}
                placeholder={t("register.passwordPlaceholder")}
              />
            </Field>
            <SubmitButton disabled={submitting}>
              {submitting ? t("forgot.saving") : t("forgot.save")}
            </SubmitButton>
          </form>
        )}
      </AuthCard>

      <p className="mt-5 text-center text-meta">
        <Link href="/login" className="font-semibold text-primary-accent hover:underline">
          {t("forgot.backToLogin")}
        </Link>
      </p>
    </AuthLayout>
  );
}

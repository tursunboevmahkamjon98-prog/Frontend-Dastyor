"use client";

import { Suspense, useState, FormEvent } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth, ApiError } from "@/lib/auth-context";
import { authApi } from "@/lib/api";
import AuthLayout from "@/components/AuthLayout";
import { useT } from "@/lib/i18n";
import GoogleSignInButton from "@/components/GoogleSignInButton";
import PhoneInput from "@/components/PhoneInput";
import { AuthCard, AuthHeading, ErrorNote, Field, SubmitButton, inputClass } from "@/components/ui";

type Step = "form" | "otp";

export default function RegisterPage() {
  const t = useT();
  return <Suspense fallback={<AuthLayout><p className="text-center text-meta text-text-secondary">{t("common.loading")}</p></AuthLayout>}><RegisterContent /></Suspense>;
}

function RegisterContent() {
  const t = useT();
  const { register, loginWithGoogle } = useAuth();
  const router = useRouter();
  const topic = useSearchParams().get("topic")?.trim().slice(0, 200);
  const destination = topic ? `/dashboard/create?${new URLSearchParams({ topic })}` : "/dashboard";
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
      router.push(destination);
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
      router.push(destination);
    } catch (err) {
      fail(err);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout>
      {topic && (
        <div className="mb-5 border-l-2 border-primary pl-4">
          <p className="text-micro font-semibold uppercase tracking-wide text-primary-accent">{t("auth.afterSignIn")}</p>
          <p className="mt-1 line-clamp-2 text-body font-medium text-text-primary">{topic}</p>
        </div>
      )}
      <ol className="mb-6 grid grid-cols-2 gap-2" aria-label={t("register.steps")}>
        <li aria-current={step === "form" ? "step" : undefined} className={`flex min-h-12 items-center gap-2 rounded-2xl border px-3 text-meta font-semibold transition-colors ${step === "form" ? "border-primary/20 bg-primary-50 text-primary-accent shadow-[inset_0_1px_0_white]" : "border-border-light bg-surface-muted/60 text-text-secondary"}`}>
          <span className={`flex h-7 w-7 items-center justify-center rounded-full text-xs tabular-nums ${step === "form" ? "bg-primary text-white shadow-sm" : "bg-white text-text-tertiary"}`}>01</span>{t("register.stepAccount")}
        </li>
        <li aria-current={step === "otp" ? "step" : undefined} className={`flex min-h-12 items-center gap-2 rounded-2xl border px-3 text-meta font-semibold transition-colors ${step === "otp" ? "border-primary/20 bg-primary-50 text-primary-accent shadow-[inset_0_1px_0_white]" : "border-border-light bg-surface-muted/60 text-text-tertiary"}`}>
          <span className={`flex h-7 w-7 items-center justify-center rounded-full text-xs tabular-nums ${step === "otp" ? "bg-primary text-white shadow-sm" : "bg-white text-text-tertiary"}`}>02</span>{t("register.stepConfirm")}
        </li>
      </ol>
      <AuthHeading
        title={step === "form" ? t("register.title") : t("register.otpTitle")}
        subtitle={step === "form" ? t("register.subtitle") : `${t("login.otpSubtitle")} ${phone}`}
      />

      <AuthCard>
        {error && <ErrorNote>{error}</ErrorNote>}

        {step === "form" ? (
          <>
            <GoogleSignInButton onCredential={onGoogleCredential} onError={setError} />

            <form onSubmit={onSubmitForm} className="space-y-4">
              <Field label={t("register.fullName")}>
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className={inputClass}
                  placeholder={t("register.fullNamePlaceholder")}
                />
              </Field>

              <Field label={t("login.phone")}>
                <PhoneInput value={digits} onChange={setDigits} />
              </Field>

              <Field label={t("login.password")}>
                <input
                  type="password"
                  required
                  minLength={6}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={inputClass}
                  placeholder={t("register.passwordPlaceholder")}
                />
              </Field>

              <SubmitButton disabled={submitting || digits.length !== 9}>
                {submitting ? t("forgot.sending") : t("forgot.send")}
              </SubmitButton>
            </form>
          </>
        ) : (
          <form onSubmit={onSubmitCode} className="space-y-4">
            <Field label={t("login.code")}>
              <input
                type="text"
                inputMode="numeric"
                required
                autoFocus
                maxLength={6}
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                className={`${inputClass} text-center text-heading font-semibold tracking-[0.4em]`}
                placeholder="000000"
              />
            </Field>

            <SubmitButton disabled={submitting || code.length !== 6}>
              {submitting ? t("register.submitting") : t("register.submit")}
            </SubmitButton>

            <button
              type="button"
              onClick={() => {
                setStep("form");
                setCode("");
                setError(null);
              }}
              className="w-full text-meta font-medium text-text-secondary transition-colors duration-150 hover:text-text-primary"
            >
              {t("common.back")}
            </button>
          </form>
        )}
      </AuthCard>

      <p className="mt-5 text-center text-micro leading-relaxed text-text-tertiary">
        {t("register.agree")}{" "}
        <Link href="/terms" className="underline hover:text-text-secondary">
          {t("register.terms")}
        </Link>{" "}
        {t("register.and")}{" "}
        <Link href="/privacy" className="underline hover:text-text-secondary">
          {t("register.privacy")}
        </Link>
      </p>

      <p className="mt-3 text-center text-meta text-text-secondary">
        {t("register.haveAccount")}{" "}
        <Link href={topic ? `/login?${new URLSearchParams({ topic })}` : "/login"} className="font-semibold text-primary-accent hover:underline">
          {t("register.login")}
        </Link>
      </p>
    </AuthLayout>
  );
}

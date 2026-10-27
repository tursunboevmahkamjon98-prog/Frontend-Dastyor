"use client";

import { Suspense, useState, FormEvent } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth, ApiError } from "@/lib/auth-context";
import AuthLayout from "@/components/AuthLayout";
import GoogleSignInButton from "@/components/GoogleSignInButton";
import PhoneInput from "@/components/PhoneInput";
import { AuthCard, AuthHeading, ErrorNote, Field, SubmitButton, inputClass } from "@/components/ui";
import { useT } from "@/lib/i18n";

export default function LoginPage() {
  const t = useT();
  return <Suspense fallback={<AuthLayout><p className="text-center text-meta text-text-secondary">{t("common.loading")}</p></AuthLayout>}><LoginContent /></Suspense>;
}

function LoginContent() {
  const t = useT();
  const { login, loginWithGoogle } = useAuth();
  const router = useRouter();
  const topic = useSearchParams().get("topic")?.trim().slice(0, 200);
  const destination = topic ? `/dashboard/create?${new URLSearchParams({ topic })}` : "/dashboard";
  const [digits, setDigits] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const phone = `+992${digits}`;

  function fail(err: unknown) {
    setError(err instanceof ApiError ? err.message : t("common.error"));
  }

  async function onSubmitCredentials(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(phone, password);
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
      <AuthHeading title={t("login.title")} subtitle={t("login.subtitle")} />

      <AuthCard>
        {error && <ErrorNote>{error}</ErrorNote>}

        <GoogleSignInButton onCredential={onGoogleCredential} onError={setError} />

        <form onSubmit={onSubmitCredentials} className="space-y-4">
          <Field label={t("login.phone")}>
            <PhoneInput value={digits} onChange={setDigits} autoFocus />
          </Field>

          <Field label={t("login.password")}>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={inputClass}
              placeholder="••••••••"
            />
          </Field>

          <SubmitButton disabled={submitting || digits.length !== 9}>
            {submitting ? t("login.submitting") : t("login.submit")}
          </SubmitButton>

          <p className="text-center">
            <Link
              href="/forgot-password"
              className="text-meta font-medium text-text-secondary transition-colors duration-150 hover:text-text-primary"
            >
              {t("login.forgot")}
            </Link>
          </p>
        </form>
      </AuthCard>

      <p className="mt-5 text-center text-meta text-text-secondary">
        {t("login.noAccount")}{" "}
        <Link href={topic ? `/register?${new URLSearchParams({ topic })}` : "/register"} className="font-semibold text-primary-accent hover:underline">
          {t("login.register")}
        </Link>
      </p>
    </AuthLayout>
  );
}

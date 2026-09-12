"use client";

import { useState, FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth, ApiError } from "@/lib/auth-context";
import AuthLayout from "@/components/AuthLayout";
import GoogleSignInButton from "@/components/GoogleSignInButton";
import PhoneInput from "@/components/PhoneInput";
import { useT } from "@/lib/i18n";

// Phone+password is the way in, matching how accounts are actually created
// (the phone app and /register both key on a number, not an email) — this
// page used to ask for an email, which meant an ordinary Dastyor teacher
// simply could not sign in on the website at all.
//
// Two steps, because the backend answers step 1 one of two ways (see
// routers/auth.py's login_send_code): tokens straight back when this
// browser is already trusted, or "code texted" when it isn't. Only the
// second case shows the code field, so a returning teacher on their own
// laptop never sees it.
type Step = "credentials" | "otp";

export default function LoginPage() {
  const t = useT();
  const { loginSendCode, loginVerify, loginWithGoogle } = useAuth();
  const router = useRouter();
  const [step, setStep] = useState<Step>("credentials");
  const [digits, setDigits] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
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
      const signedIn = await loginSendCode(phone, password);
      if (signedIn) router.push("/dashboard");
      else setStep("otp");
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
      await loginVerify(phone, code.trim());
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
    <AuthLayout>
      <div className="mb-8 lg:text-left">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/logo.png" alt="Dastyor" className="mb-4 h-11 w-11 lg:hidden" />
        <h1 className="text-2xl font-bold text-text-primary sm:text-3xl">
          {step === "credentials" ? t("login.title") : t("login.otpTitle")}
        </h1>
        <p className="mt-1.5 text-sm text-text-secondary">
          {step === "credentials"
            ? t("login.subtitle")
            : `${t("login.otpSubtitle")} ${phone}`}
        </p>
      </div>

      <div className="rounded-[1.75rem] border border-border-light bg-surface p-6 shadow-xl shadow-black/[0.05] sm:p-7">
        {error && <div className="mb-4 rounded-xl bg-primary-50 px-4 py-3 text-sm text-primary-dark">{error}</div>}

        {step === "credentials" ? (
          <>
            {/* Renders nothing at all (button AND its "or" rule) when
                Google sign-in isn't configured — see the component. */}
            <GoogleSignInButton onCredential={onGoogleCredential} onError={setError} />

            <form onSubmit={onSubmitCredentials} className="space-y-4">
              <div>
                <label className="mb-1.5 block text-sm font-medium text-text-secondary">{t("login.phone")}</label>
                <PhoneInput value={digits} onChange={setDigits} autoFocus />
              </div>

              <div>
                <label className="mb-1.5 block text-sm font-medium text-text-secondary">{t("login.password")}</label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={inputClass}
                  placeholder="••••••••"
                />
              </div>

              <div className="text-right">
                <Link href="/forgot-password" className="text-sm font-medium text-primary hover:underline">
                  {t("login.forgot")}
                </Link>
              </div>

              <button
                type="submit"
                disabled={submitting || digits.length !== 9}
                className="w-full rounded-xl bg-primary py-2.5 text-sm font-semibold text-white shadow-lg shadow-primary/25 transition hover:-translate-y-0.5 hover:bg-primary-dark disabled:pointer-events-none disabled:opacity-60 disabled:hover:translate-y-0"
              >
                {submitting ? t("login.submitting") : t("login.submit")}
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
              {submitting ? t("login.verifying") : t("login.verify")}
            </button>

            <button
              type="button"
              onClick={() => {
                setStep("credentials");
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

      <p className="mt-6 text-center text-sm text-text-secondary">
        {t("login.noAccount")}{" "}
        <Link href="/register" className="font-semibold text-primary hover:underline">
          {t("login.register")}
        </Link>
      </p>
    </AuthLayout>
  );
}

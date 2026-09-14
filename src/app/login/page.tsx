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
export default function LoginPage() {
  const t = useT();
  const { login, loginWithGoogle } = useAuth();
  const router = useRouter();
  const [digits, setDigits] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const phone = `+992${digits}`;

  function fail(err: unknown) {
    setError(err instanceof ApiError ? err.message : t("common.error"));
  }

  // Phone + password, straight to a session. Signing in used to run the
  // same SMS challenge registration does — a code texted on EVERY login,
  // with a device token to skip it on a browser that had passed one
  // before. In practice the skip rarely applied (a cleared cookie jar, a
  // second device, a reinstall all lose it) so teachers were texted a
  // code nearly every time they signed in: slow for them, and a real per
  // message cost on every single login.
  //
  // A password already proves who they are. The SMS challenge stays
  // where it establishes something a password cannot — registration
  // (proving the number is theirs) and password reset (proving it still
  // is). The /auth/login/send-code and /login/verify endpoints are
  // untouched and still serve the mobile app.
  async function onSubmitCredentials(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(phone, password);
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
          {t("login.title")}
        </h1>
        <p className="mt-1.5 text-sm text-text-secondary">{t("login.subtitle")}</p>
      </div>

      <div className="rounded-[1.75rem] border border-border-light bg-surface p-6 shadow-xl shadow-black/[0.05] sm:p-7">
        {error && <div className="mb-4 rounded-xl bg-primary-50 px-4 py-3 text-sm text-primary-dark">{error}</div>}

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

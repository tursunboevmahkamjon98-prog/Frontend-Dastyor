"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { authApi, getToken, setToken, getRefreshToken, setRefreshToken, setDeviceToken, clearToken, TokenResponse, UserOut, ApiError } from "./api";

interface AuthContextValue {
  user: UserOut | null;
  loading: boolean;
  /** Step 1 of signing in. Resolves `true` when the account is now signed
   * in outright (trusted browser / bypass account), or `false` when the
   * server texted a code and the caller must collect it and hand it to
   * [loginVerify]. */
  loginSendCode: (phone: string, password: string) => Promise<boolean>;
  /** Step 2 — verifies the texted code, signs in, and remembers this
   * browser so the next login here skips the code. */
  loginVerify: (phone: string, code: string) => Promise<void>;
  /** Direct phone+password, no second factor — kept for completeness; the
   * login page uses the two-step pair above instead. */
  login: (phone: string, password: string) => Promise<void>;
  // Final step of registration only — the page itself calls
  // authApi.sendRegisterCode(phone) directly for the SMS step, since that
  // doesn't touch any session state this context tracks.
  register: (fullName: string, phone: string, code: string, password: string) => Promise<void>;
  loginEmail: (email: string, password: string) => Promise<void>;
  registerEmail: (fullName: string, email: string, password: string) => Promise<void>;
  // Shared by both the /login and /register pages' Google button — Google
  // itself decides register-vs-login server-side (see routers/auth.py's
  // /auth/google), so there's only one flow to expose here.
  loginWithGoogle: (credential: string) => Promise<void>;
  logout: () => void;
  setUser: (user: UserOut) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setLoading(false);
      return;
    }
    // This ran into a real bug on the flaky free-tunnel pilot deployment:
    // a teacher would log in fine, land on /dashboard, and immediately get
    // bounced back to /login — not because their token was bad, but
    // because THIS follow-up /users/me call glitched on the same shaky
    // connection moments later (see request()'s fetch() try/catch —
    // "Не удалось подключиться к серверу" is a network-level failure, no
    // response at all, request() itself never clears the token for that
    // case). Unconditionally clearing the token on *any* rejection here —
    // network hiccup included — threw away a perfectly valid session and
    // forced a full re-login. Now: retry a couple of times first (a
    // dropped mobile-network packet is often gone half a second later),
    // and only actually clear the token when the server itself said the
    // token is invalid (401 → ApiError.status === 401), never for a
    // connectivity error — leaving the token in place lets the next
    // visit/reload succeed once the network recovers, instead of forcing
    // the teacher to type their phone+password again.
    async function loadUser() {
      for (let attempt = 0; attempt < 3; attempt++) {
        try {
          setUser(await authApi.me());
          return;
        } catch (err) {
          const isAuthInvalid = err instanceof ApiError && err.status === 401;
          if (isAuthInvalid) {
            clearToken();
            return;
          }
          if (attempt < 2) await new Promise((r) => setTimeout(r, 800));
          // else: give up for this page load, but keep the token — see
          // comment above.
        }
      }
    }
    loadUser().finally(() => setLoading(false));
  }, []);

  /** Shared tail of every sign-in path — stores the session and, when the
   * response carries one (only login_verify does), the device token that
   * lets this browser skip the SMS step next time. */
  function adoptSession(res: TokenResponse) {
    setToken(res.access_token);
    setRefreshToken(res.refresh_token);
    if (res.device_token) setDeviceToken(res.device_token);
    setUser(res.user);
  }

  async function loginSendCode(phone: string, password: string): Promise<boolean> {
    const res = await authApi.loginSendCode(phone, password);
    // The two possible shapes are told apart by access_token — see
    // authApi.loginSendCode. Anything without one means "code texted".
    if (!("access_token" in res)) return false;
    adoptSession(res);
    return true;
  }

  async function loginVerify(phone: string, code: string) {
    adoptSession(await authApi.loginVerify(phone, code));
  }

  async function login(phone: string, password: string) {
    adoptSession(await authApi.login(phone, password));
  }

  async function register(fullName: string, phone: string, code: string, password: string) {
    const res = await authApi.register(fullName, phone, code, password);
    setToken(res.access_token);
    setRefreshToken(res.refresh_token);
    setUser(res.user);
  }

  async function loginEmail(email: string, password: string) {
    const res = await authApi.loginEmail(email, password);
    setToken(res.access_token);
    setRefreshToken(res.refresh_token);
    setUser(res.user);
  }

  async function registerEmail(fullName: string, email: string, password: string) {
    const res = await authApi.registerEmail(fullName, email, password);
    setToken(res.access_token);
    setRefreshToken(res.refresh_token);
    setUser(res.user);
  }

  async function loginWithGoogle(credential: string) {
    const res = await authApi.google(credential);
    setToken(res.access_token);
    setRefreshToken(res.refresh_token);
    setUser(res.user);
  }

  function logout() {
    // Revoke the refresh token server-side before wiping it locally —
    // fire-and-forget, since we want to clear the session immediately
    // either way (see authApi.logout's doc comment for why this can't
    // block on it).
    const rt = getRefreshToken();
    if (rt) authApi.logout(rt).catch(() => {});
    clearToken();
    setUser(null);
  }

  return (
    <AuthContext.Provider
      value={{ user, loading, loginSendCode, loginVerify, login, register, loginEmail, registerEmail, loginWithGoogle, logout, setUser }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export { ApiError };

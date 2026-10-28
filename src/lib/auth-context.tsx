"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { authApi, getToken, setToken, getRefreshToken, setRefreshToken, setDeviceToken, clearToken, ensureAccessToken, TokenResponse, UserOut, ApiError } from "./api";

interface AuthContextValue {
  user: UserOut | null;
  loading: boolean;
  
  loginSendCode: (phone: string, password: string) => Promise<boolean>;
  
  loginVerify: (phone: string, code: string) => Promise<void>;
  
  login: (phone: string, password: string) => Promise<void>;
  
  
  
  register: (fullName: string, phone: string, code: string, password: string) => Promise<void>;
  loginEmail: (email: string, password: string) => Promise<void>;
  registerEmail: (fullName: string, email: string, password: string) => Promise<void>;
  
  
  
  loginWithGoogle: (credential: string) => Promise<void>;
  logout: () => void;
  setUser: (user: UserOut) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getToken() && !getRefreshToken()) {
      setLoading(false);
      return;
    }
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    async function loadUser() {
      const outcome = await ensureAccessToken();
      if (outcome !== "ok") {
        if (outcome === "rejected") clearToken();
        return;
      }
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
          
          
        }
      }
    }
    loadUser().finally(() => setLoading(false));
  }, []);

  
  function adoptSession(res: TokenResponse) {
    setToken(res.access_token);
    setRefreshToken(res.refresh_token);
    if (res.device_token) setDeviceToken(res.device_token);
    setUser(res.user);
  }

  async function loginSendCode(phone: string, password: string): Promise<boolean> {
    const res = await authApi.loginSendCode(phone, password);
    
    
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
    adoptSession(await authApi.register(fullName, phone, code, password));
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

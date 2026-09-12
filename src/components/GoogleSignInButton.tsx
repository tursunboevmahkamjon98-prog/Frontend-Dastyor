"use client";

import { useEffect, useRef, useState } from "react";

const CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ?? "";
const SCRIPT_SRC = "https://accounts.google.com/gsi/client";

// Minimal typing for the slice of the Google Identity Services global API
// this component actually calls — the real script attaches this to
// `window.google` at runtime; there's no @types package worth pulling in
// for three methods.
interface GoogleIdApi {
  accounts: {
    id: {
      initialize: (config: {
        client_id: string;
        callback: (response: { credential: string }) => void;
      }) => void;
      renderButton: (
        parent: HTMLElement,
        options: {
          type?: string;
          theme?: string;
          size?: string;
          text?: string;
          shape?: string;
          width?: number;
          locale?: string;
        }
      ) => void;
    };
  };
}

declare global {
  interface Window {
    google?: GoogleIdApi;
  }
}

let scriptLoadPromise: Promise<void> | null = null;

function loadGoogleScript(): Promise<void> {
  if (scriptLoadPromise) return scriptLoadPromise;
  scriptLoadPromise = new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${SCRIPT_SRC}"]`);
    if (existing) {
      resolve();
      return;
    }
    const script = document.createElement("script");
    script.src = SCRIPT_SRC;
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Google Identity script"));
    document.head.appendChild(script);
  });
  return scriptLoadPromise;
}

/** Renders Google's own "Sign in with Google" button and, once a teacher
 * completes that flow, hands the resulting ID token off to `onCredential`
 * (both /login and /register wire this straight to
 * useAuth().loginWithGoogle — see its doc comment for why one flow covers
 * both pages). Silently renders nothing if NEXT_PUBLIC_GOOGLE_CLIENT_ID
 * isn't configured, rather than showing a button that can only ever fail. */
export default function GoogleSignInButton({
  onCredential,
  onError,
}: {
  onCredential: (credential: string) => void;
  onError?: (message: string) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!CLIENT_ID) return;
    let cancelled = false;

    loadGoogleScript()
      .then(() => {
        if (cancelled || !containerRef.current || !window.google) return;
        window.google.accounts.id.initialize({
          client_id: CLIENT_ID,
          callback: (response) => onCredential(response.credential),
        });
        window.google.accounts.id.renderButton(containerRef.current, {
          type: "standard",
          theme: "outline",
          size: "large",
          text: "continue_with",
          shape: "pill",
          width: 320,
          locale: "ru",
        });
      })
      .catch(() => {
        if (cancelled) return;
        setFailed(true);
        onError?.("Не удалось загрузить Google Sign-In");
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- onCredential/onError are expected to be stable per page
  }, []);

  if (!CLIENT_ID || failed) return null;

  return (
    <>
      <div ref={containerRef} className="flex justify-center" />
      {/* The "or" rule belongs to the button, not to the page: when it used
          to sit in login/register directly, an unconfigured (or failed)
          Google button left a divider stranded above the form separating
          nothing from nothing. Rendering it here means the two always
          appear and disappear together. */}
      <div className="my-5 flex items-center gap-3">
        <div className="h-px flex-1 bg-border" />
        <span className="text-xs text-text-tertiary">или</span>
        <div className="h-px flex-1 bg-border" />
      </div>
    </>
  );
}

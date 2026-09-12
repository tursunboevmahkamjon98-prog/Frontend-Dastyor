"use client";

import { useEffect, useState } from "react";

/**
 * Tracks browser connectivity (navigator.onLine + online/offline events).
 * Used to show a clear "no internet" indicator instead of letting AI
 * generation requests fail with a generic/confusing network error — the
 * user explicitly asked for a WiFi-style "no internet" signal.
 *
 * Note: navigator.onLine only reflects whether the device has *a* network
 * connection (e.g. is associated with a WiFi router), not necessarily real
 * internet access — a connected-but-no-internet WiFi still reports true.
 * Good enough to catch the common "WiFi/data is fully off" case being
 * asked for here without pinging a server on every render.
 */
export function useOnlineStatus(): boolean {
  const [online, setOnline] = useState(true);

  useEffect(() => {
    setOnline(navigator.onLine);
    const goOnline = () => setOnline(true);
    const goOffline = () => setOnline(false);
    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);
    return () => {
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
    };
  }, []);

  return online;
}

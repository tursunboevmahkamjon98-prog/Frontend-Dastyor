"use client";

import { useAuth } from "@/lib/auth-context";

/** Whether this account may use the game section.
 *
 * This is presentation only. The decision that matters is
 * `require_game_access` in backend/app/routers/materials.py, which runs
 * on every endpoint that creates, edits, rerolls or records a game — a
 * hidden button is one devtools inspection away from being clicked, and
 * the endpoints are reachable with a bearer token and curl regardless of
 * what this returns. Its job is to keep a locked feature out of the way,
 * not to enforce the lock.
 *
 * Kept as one helper rather than repeated `user?.role === "admin"` checks
 * so that when the backend's allow-list (GAME_ACCESS_USER_IDS) is
 * eventually surfaced on the user object, every entry point starts
 * honouring it at once instead of four of five.
 */
export function useGameAccess(): boolean {
  const { user } = useAuth();
  return user?.role === "admin";
}

"use client";

import { useAuth } from "@/lib/auth-context";


export function useGameAccess(): boolean {
  const { user } = useAuth();
  return user?.role === "admin";
}

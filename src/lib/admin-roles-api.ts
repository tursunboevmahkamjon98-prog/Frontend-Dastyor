import { ApiError, getToken } from "./api";
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/api";
export type AdminTier = "super" | "finance" | "support" | "readonly";
export interface AdminRosterEntry { user_id: string; full_name: string; short_id: string | null; admin_tier: AdminTier | null; }
export interface UnreviewedTelegramAdminOut { grant_id: string; telegram_user_id: number | null; user_id: string | null; full_name: string | null; short_id: string | null; added_at: string; }
export interface AdminRosterOut { admins: AdminRosterEntry[]; unreviewed: UnreviewedTelegramAdminOut[]; }
async function request<T>(path: string, body?: unknown): Promise<T> {
  const token=getToken(); const response=await fetch(`${API_URL}${path}`,{method:body===undefined?"GET":"POST",headers:{"Content-Type":"application/json",...(token?{Authorization:`Bearer ${token}`}:{})},body:body===undefined?undefined:JSON.stringify(body)});
  const data=await response.json().catch(()=>({})); if(!response.ok)throw new ApiError(typeof data.detail==="string"?data.detail:"Request failed",response.status); return data as T;
}
export const adminRolesApi = {
  roster: () => request<AdminRosterOut>("/admin/admins"),
  promote: (userId:string,admin_tier:AdminTier) => request<AdminRosterEntry>(`/admin/admins/${userId}/promote`,{action:"promote",admin_tier}),
  demote: (userId:string) => request<AdminRosterEntry>(`/admin/admins/${userId}/promote`,{action:"demote"}),
  ignore: (userId:string) => request<AdminRosterEntry>(`/admin/admins/${userId}/promote`,{action:"ignore"}),
};
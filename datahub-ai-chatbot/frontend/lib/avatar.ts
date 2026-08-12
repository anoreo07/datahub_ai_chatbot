import type { User } from "@/lib/types";

const ROLE_AVATARS: Record<string, string> = {
  admin: "/admin_avatar.png",
  finance: "/finance_avatar.png",
  logistics: "/logistic_avatar.png",
  logistic: "/logistic_avatar.png",
};

export function getRoleAvatar(
  user?: Pick<User, "username" | "roles"> & { user_id?: string } | null
): string | undefined {
  if (!user) return undefined;
  const key = user.username?.toLowerCase() || user.user_id?.toLowerCase();
  if (key && ROLE_AVATARS[key]) return ROLE_AVATARS[key];
  const role = user.roles?.find((r) => ROLE_AVATARS[r.toLowerCase()]);
  return role ? ROLE_AVATARS[role.toLowerCase()] : undefined;
}

import { auth } from "./auth";
import type { User } from "./types";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  const token = auth.getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(path, { ...options, headers });
  if (res.status === 401) {
    auth.clear();
    if (typeof window !== "undefined") {
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.href = "/login";
    }
    throw new ApiError("Authentication required", 401);
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(detail, res.status);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export async function login(
  username: string,
  password: string
): Promise<UserResponse> {
  const data = await apiFetch<UserResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  auth.setToken(data.token);
  auth.setUser({
    username: data.username,
    display_name: data.display_name,
    roles: data.roles,
    is_admin: data.is_admin,
  });
  return data;
}

export async function fetchMe(): Promise<MeResponse> {
  const data = await apiFetch<MeResponse>("/api/me");
  auth.setUser(data);
  return data;
}

/* ---- response type aliases ---- */
type UserResponse = {
  token: string;
  username: string;
  display_name?: string;
  roles: string[];
  is_admin: boolean;
};

type MeResponse = User & { username: string };
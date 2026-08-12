import { apiFetch } from "./api";
import { auth } from "./auth";
import type { ImageItem, ImageListResponse, ImageStats } from "./types";

export interface ListImagesParams {
  search?: string;
  status?: string;
  image_type?: string;
  conversation_id?: string;
  sort_by?: string;
  sort_desc?: boolean;
  limit?: number;
  offset?: number;
}

export async function listImages(
  params: ListImagesParams = {}
): Promise<ImageListResponse> {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "" && v !== "all") {
      qs.set(k, String(v));
    }
  });
  return apiFetch<ImageListResponse>(`/api/v1/storage?${qs.toString()}`);
}

export async function fetchImageStats(): Promise<ImageStats> {
  return apiFetch<ImageStats>("/api/v1/storage/stats");
}

export async function deleteImage(
  imageId: string,
  hard = false
): Promise<ImageItem> {
  return apiFetch<ImageItem>(`/api/v1/storage/${imageId}`, {
    method: "DELETE",
    body: JSON.stringify({ hard }),
  });
}

export async function restoreImage(imageId: string): Promise<ImageItem> {
  return apiFetch<ImageItem>(`/api/v1/storage/${imageId}/restore`, {
    method: "POST",
  });
}

export async function reanalyzeImage(imageId: string): Promise<ImageItem> {
  return apiFetch<ImageItem>(`/api/v1/storage/${imageId}/reanalyze`, {
    method: "POST",
  });
}

export async function fetchImageBlob(
  path: string
): Promise<string> {
  const token = auth.getToken();
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(path, { headers });
  if (!res.ok) throw new Error(`Failed to load image: ${res.status}`);
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}
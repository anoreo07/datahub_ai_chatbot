"use client";

import { useCallback, useEffect, useState } from "react";
import { Image as ImageIcon, Loader2, RefreshCcw, Trash2, RotateCcw, HardDrive } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  deleteImage,
  fetchImageBlob,
  fetchImageStats,
  listImages,
  reanalyzeImage,
  restoreImage,
} from "@/lib/storage";
import type { ImageItem, ImageStats } from "@/lib/types";
import { cn } from "@/lib/utils";

const PER_PAGE = 24;

const STATUS_LABEL: Record<string, string> = {
  uploaded: "Đã tải lên",
  analyzing: "Đang phân tích",
  analyzed: "Đã phân tích",
  failed: "Thất bại",
};

function formatSize(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  if (bytes >= 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${bytes} B`;
}

export default function StoragePage() {
  const [images, setImages] = useState<ImageItem[]>([]);
  const [stats, setStats] = useState<ImageStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  const [thumbnailMap, setThumbnailMap] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string>("");
  const [confirmDelete, setConfirmDelete] = useState<ImageItem | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [list, statsData] = await Promise.all([
        listImages({ search, status, limit: PER_PAGE }),
        fetchImageStats(),
      ]);
      setImages(list.items || []);
      setStats(statsData);
      const map: Record<string, string> = {};
      await Promise.all(
        (list.items || []).map(async (img) => {
          try {
            map[img.image_id] = await fetchImageBlob(`/api/v1/storage/${img.image_id}/thumbnail`);
          } catch {
            /* thumb unavailable */
          }
        })
      );
      setThumbnailMap(map);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [search, status]);

  useEffect(() => {
    const t = setTimeout(refresh, 80);
    return () => clearTimeout(t);
  }, [refresh]);

  const onDelete = async (image: ImageItem, hard = false) => {
    setBusy(image.image_id);
    try {
      await deleteImage(image.image_id, hard);
      setConfirmDelete(null);
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  };

  const onRestore = async (image: ImageItem) => {
    setBusy(image.image_id);
    try {
      await restoreImage(image.image_id);
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  };

  const onReanalyze = async (image: ImageItem) => {
    setBusy(image.image_id);
    try {
      await reanalyzeImage(image.image_id);
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-6xl space-y-4 p-6">
        <div className="flex items-center justify-between">
          <h1 className="flex items-center gap-2 text-xl font-semibold">
            <HardDrive className="h-5 w-5" /> Hình ảnh đã lưu
          </h1>
          <Button variant="ghost" size="sm" onClick={refresh} className="gap-2">
            <RefreshCcw className={cn("h-4 w-4", loading && "animate-spin")} />
            Làm mới
          </Button>
        </div>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
            <StatCard label="Tổng số" value={stats.total} />
            <StatCard label="Tổng dung lượng" value={formatSize(stats.total_size)} />
            <StatCard label="Đã phân tích" value={stats.analyzed} accent="text-green-600" />
            <StatCard label="Đang chờ" value={stats.pending} accent="text-amber-600" />
            <StatCard label="Thất bại" value={stats.failed} accent="text-red-600" />
          </div>
        )}

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-2">
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Tìm theo tên / dataset…"
            className="max-w-xs"
          />
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="h-10 rounded-md border border-input bg-background px-3 text-sm"
            aria-label="Lọc theo trạng thái"
          >
            <option value="all">Tất cả trạng thái</option>
            <option value="analyzed">Đã phân tích</option>
            <option value="pending">Đang chờ</option>
            <option value="failed">Thất bại</option>
          </select>
        </div>

        {error && (
          <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
        )}

        {loading && images.length === 0 ? (
          <div className="flex h-40 items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        ) : images.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-16 text-center text-muted-foreground">
            <ImageIcon className="h-8 w-8" />
            <p>Chưa có hình ảnh nào được lưu.</p>
            <p className="text-sm">Hình ảnh bạn gửi trong hội thoại sẽ xuất hiện ở đây.</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
            {images.map((img) => (
              <Card key={img.image_id} className="overflow-hidden">
                <div className="relative aspect-video w-full bg-muted">
                  {thumbnailMap[img.image_id] ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={thumbnailMap[img.image_id]}
                      alt={img.original_filename}
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center">
                      <ImageIcon className="h-6 w-6 text-muted-foreground" />
                    </div>
                  )}
                  <span
                    className={cn(
                      "absolute left-2 top-2 rounded px-1.5 py-0.5 text-[10px] font-medium text-white",
                      statusColor(img.status)
                    )}
                  >
                    {STATUS_LABEL[img.status] || img.status}
                  </span>
                </div>
                <div className="space-y-1 p-3">
                  <p className="truncate text-sm font-medium" title={img.original_filename}>
                    {img.original_filename}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {formatSize(img.size)} · {img.image_type || "—"}
                  </p>
                  {img.dataset_detected && (
                    <p className="truncate text-xs text-primary">{img.dataset_detected}</p>
                  )}
                  <div className="flex items-center gap-1 pt-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 px-2"
                      disabled={busy === img.image_id}
                      onClick={() => onReanalyze(img)}
                      title="Chạy lại phân tích"
                    >
                      <RefreshCcw className="h-3.5 w-3.5" />
                    </Button>
                    {img.is_deleted ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 px-2"
                        onClick={() => onRestore(img)}
                        title="Khôi phục"
                      >
                        <RotateCcw className="h-3.5 w-3.5" />
                      </Button>
                    ) : (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 px-2 text-destructive"
                        onClick={() => setConfirmDelete(img)}
                        title="Xóa"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      <Dialog open={!!confirmDelete} onOpenChange={() => setConfirmDelete(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Xóa hình ảnh?</DialogTitle>
            <DialogDescription>
              “{confirmDelete?.original_filename}” sẽ được chuyển vào thùng rác và có thể khôi phục
              sau này.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setConfirmDelete(null)}>
              Hủy
            </Button>
            <Button
              variant="destructive"
              onClick={() => confirmDelete && onDelete(confirmDelete)}
            >
              Xóa
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function StatCard({ label, value, accent }: { label: string; value: number | string; accent?: string }) {
  return (
    <div className="rounded-lg border bg-card p-3">
      <p className={cn("text-lg font-semibold", accent)}>{value}</p>
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  );
}

function statusColor(status: string): string {
  switch (status) {
    case "analyzed":
      return "bg-green-600";
    case "failed":
      return "bg-red-600";
    case "analyzing":
      return "bg-amber-600";
    default:
      return "bg-slate-600";
  }
}
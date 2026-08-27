"use client";

import { useEffect } from "react";
import { cn } from "@/lib/utils";
import { useNotificationStore } from "@/lib/notification-store";

interface NotificationCenterProps {
  open: boolean;
  onClose: () => void;
}

export function NotificationCenter({ open, onClose }: NotificationCenterProps) {
  const {
    notifications,
    unreadCount,
    hasActiveJobs,
    markRead,
    markAllRead,
  } = useNotificationStore();

  useEffect(() => {
    // When component mounts, fetch fresh notifications
    // The store already polls, so this is just for initial load
  }, []);

  return (
    <div className="fixed right-0 top-14 w-80 max-h-[calc(100vh-40)] bg-background border border-border rounded-lg shadow-lg z-50 p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-foreground">
          Thông báo
        </h3>
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">
            {unreadCount} chưa đọc
          </span>
          {unreadCount > 0 && (
            <button
              onClick={markAllRead}
              className="text-primary hover:text-primary-foreground transition-colors"
              title="Đánh dấu tất cả đã đọc"
            >
              ← Xoá
            </button>
          )}
        </div>
      </div>

      {hasActiveJobs && (
        <div className="px-2 py-2 text-sm text-muted-foreground mb-4">
          🔵 Đang có task đang chạy
        </div>
      )}

      <ul className="space-y-1 max-h-[400px] overflow-y-auto">
        {notifications.length === 0 && (
          <li className="px-2 py-2 text-muted-foreground">
            Không có thông báo
          </li>
        )}
        {notifications.map((notif) => (
          <li
            key={notif.id}
            className={cn(
              "px-2 py-2 rounded hover:bg-muted/50 transition-colors",
              "flex items-start gap-3",
              notif.is_read ? "" : "font-medium text-foreground",
            )}
          >
            <div className="w-8 h-8 rounded flex items-center justify-center">
              {notif.status === "running" && (
                <span className="text-primary">🔵</span>
              )}
              {notif.status === "success" && (
                <span className="text-success">✅</span>
              )}
              {notif.status === "failed" && (
                <span className="text-destructive">❌</span>
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className={cn(
                "font-medium truncate",
                notif.is_read ? "text-foreground" : "text-primary",
              )}>
                {notif.title}
              </p>
              <p className="text-xs text-muted-foreground truncate">
                {notif.message}
              </p>
            </div>
            <button
              onClick={() => markRead(notif.id)}
              className="ml-2 text-primary hover:text-primary-foreground text-sm transition-colors"
              title="Đánh dấu đã đọc"
            >
              Đã đọc
            </button>
          </li>
        ))}
      </ul>

      <div className="pt-2 border-t border-border mt-4">
        {unreadCount > 0 && (
          <button
            onClick={markAllRead}
            className="w-full flex items-center justify-center py-2 text-sm text-primary hover:text-primary-foreground"
            title="Đánh dấu tất cả đã đọc"
          >
            Mark all as read
          </button>
        )}
      </div>
    </div>
  );
}
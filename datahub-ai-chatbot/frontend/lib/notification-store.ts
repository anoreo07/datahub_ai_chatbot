"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "./api";

interface Notification {
  id: number;
  type: string;
  title: string;
  message: string;
  status: "pending" | "running" | "success" | "failed";
  is_read: boolean;
  created_at: string;
  read_at: string | null;
  metadata: any;
}

interface NotificationState {
  notifications: Notification[];
  unreadCount: number;
  hasActiveJobs: boolean;
  activeJobs: Notification[];
  isPolling: boolean;
  pollInterval: NodeJS.Timeout | null;
}

const STORAGE_KEY = "v-data-atlas-notifications";
const POLL_INTERVAL_MS = 10000; // 10 seconds

function loadNotificationsFromStorage(): Notification[] {
  try {
    const stored = typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null;
    if (stored) {
      return JSON.parse(stored);
    }
  } catch {
    /* ignore */
  }
  return [];
}

function saveNotificationsToStorage(notifications: Notification[]): void {
  try {
    if (typeof window !== "undefined") {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(notifications));
    }
  } catch {
    /* ignore */
  }
}

export function useNotificationStore() {
  const [state, setState] = useState<NotificationState>({
    notifications: loadNotificationsFromStorage(),
    unreadCount: 0,
    hasActiveJobs: false,
    activeJobs: [],
    isPolling: false,
    pollInterval: null,
  });

  useEffect(() => {
    // Initialize polling if not already running
    if (!state.isPolling) {
      startPolling();
    }

    return () => {
      // Cleanup on unmount
      if (state.pollInterval) {
        clearInterval(state.pollInterval);
      }
    };
  }, [state.isPolling]);

  const setNotifications = (notifications: Notification[]) => {
    setState(prev => {
      const updated = [...notifications];
      saveNotificationsToStorage(updated);
      const unreadCount = updated.filter(n => !n.is_read).length;
      const hasActiveJobs = updated.some(n => n.status === "running" && !n.is_read);
      return {
        ...prev,
        notifications: updated,
        unreadCount,
        hasActiveJobs,
        activeJobs: updated.filter(n => n.status === "running"),
      };
    });
  };

  const markRead = async (notificationId: number) => {
    try {
      await apiFetch(`/api/v1/notifications/${notificationId}/read`, {
        method: "PATCH",
      });
      setState(prev => ({
        ...prev,
        notifications: prev.notifications.map(n =>
          n.id === notificationId ? { ...n, is_read: true, read_at: new Date().toISOString() } : n
        ),
        unreadCount: prev.unreadCount - 1,
      }));
    } catch (error) {
      console.error("Mark read failed:", error);
    }
  };

  const markAllRead = async () => {
    try {
      await apiFetch("/api/v1/notifications/mark-all-read", {
        method: "POST",
      });
      setState(prev => ({
        ...prev,
        notifications: prev.notifications.map(n => ({ ...n, is_read: true, read_at: new Date().toISOString() })),
        unreadCount: 0,
        hasActiveJobs: prev.notifications.some(n => n.status === "running"),
        activeJobs: prev.notifications.filter(n => n.status === "running"),
      }));
    } catch (error) {
      console.error("Mark all read failed:", error);
    }
  };

  const startPolling = () => {
    if (state.pollInterval) {
      clearInterval(state.pollInterval);
    }
    
    const interval = setInterval(async () => {
      try {
        const res = await apiFetch("/api/v1/notifications/unread-count", {
          method: "GET",
        });
        setState(prev => ({
          ...prev,
          unreadCount: res as number,
        }));
      } catch (error) {
        // Ignore polling errors
      }
      
      try {
        const activeRes = await apiFetch("/api/v1/notifications/jobs/active", {
          method: "GET",
        });
        const activeJobs = activeRes as Notification[];
        setState(prev => ({
          ...prev,
          hasActiveJobs: activeJobs.length > 0,
          activeJobs,
        }));
      } catch (error) {
        // Ignore polling errors
      }
    }, POLL_INTERVAL_MS);

    setState(prev => ({ ...prev, isPolling: true, pollInterval: interval }));
  };

  return {
    ...state,
    setNotifications,
    markRead,
    markAllRead,
  };
}
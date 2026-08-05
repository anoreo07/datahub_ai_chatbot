"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import { auth } from "@/lib/auth";
import { fetchMe, login as apiLogin } from "@/lib/api";
import type { LoginResponse, User } from "@/lib/types";

export interface Conversation {
  conversation_id: string;
  turn_count?: number;
  last_question?: string;
  last_accessed?: number;
}

interface AppStore {
  user: User | null;
  loadingUser: boolean;
  login: (username: string, password: string) => Promise<User>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  sidebarCollapsed: boolean;
  mobileSidebarOpen: boolean;
  setSidebarCollapsed: (v: boolean) => void;
  toggleSidebar: () => void;
  setMobileSidebarOpen: (v: boolean) => void;
  conversations: Conversation[];
  activeConversationId: string | null;
  setActiveConversationId: (id: string | null) => void;
  refreshConversations: () => Promise<void>;
  deleteConversation: (id: string) => Promise<void>;
  clearConversations: () => Promise<void>;
  renameConversation: (id: string, title: string) => void;
  pinned: string[];
  titles: Record<string, string>;
  chatReset: number;
  requestNewChat: () => void;
}

const AppContext = createContext<AppStore | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loadingUser, setLoadingUser] = useState<boolean>(true);
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState<boolean>(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [titles, setTitles] = useState<Record<string, string>>({});
  const [pinned] = useState<string[]>([]);
  const [chatReset, setChatReset] = useState<number>(0);

  const refreshUser = useCallback(async () => {
    if (!auth.getToken()) {
      setUser(null);
      setLoadingUser(false);
      return;
    }
    try {
      const me = await fetchMe();
      setUser(me);
    } catch {
      setUser(null);
    } finally {
      setLoadingUser(false);
    }
  }, []);

  useEffect(() => {
    // Restore the locally stored user only after hydration so the server and
    // first client render agree (avoids a hydration mismatch from reading
    // localStorage during the initial render).
    const stored = auth.getUser();
    if (stored) setUser(stored);
    if (auth.getToken()) {
      setLoadingUser(true);
      refreshUser();
    } else {
      setLoadingUser(false);
    }
  }, [refreshUser]);

  const login = useCallback(async (username: string, password: string) => {
    const data: LoginResponse = await apiLogin(username, password);
    const u: User = {
      username: data.username,
      display_name: data.display_name,
      roles: data.roles,
      is_admin: data.is_admin,
    };
    setUser(u);
    return u;
  }, []);

  const logout = useCallback(() => {
    auth.clear();
    setUser(null);
    setConversations([]);
    setActiveConversationId(null);
  }, []);

  const refreshConversations = useCallback(async () => {
    try {
      const res = await fetch("/api/v1/conversations", {
        headers: { Authorization: `Bearer ${auth.getToken()}` },
      });
      if (res.ok) {
        const data = await res.json();
        setConversations((data.conversations || []).sort(
          (a: Conversation, b: Conversation) => (b.last_accessed || 0) - (a.last_accessed || 0)
        ));
      }
    } catch {
      /* ignore */
    }
  }, []);

  const deleteConversation = useCallback(
    async (id: string) => {
      const res = await fetch(`/api/v1/conversations/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${auth.getToken()}` },
      });
      if (res.ok) {
        setConversations((prev) => prev.filter((c) => c.conversation_id !== id));
        if (activeConversationId === id) setActiveConversationId(null);
      }
    },
    [activeConversationId]
  );

  const clearConversations = useCallback(async () => {
    const res = await fetch("/api/v1/conversations", {
      method: "DELETE",
      headers: { Authorization: `Bearer ${auth.getToken()}` },
    });
    if (res.ok) {
      setConversations([]);
      setActiveConversationId(null);
    }
  }, []);

  const toggleSidebar = useCallback(
    () => setSidebarCollapsed((v) => !v),
    []
  );

  const renameConversation = useCallback((id: string, title: string) => {
    setTitles((prev) => ({ ...prev, [id]: title }));
  }, []);

  const requestNewChat = useCallback(() => {
    setChatReset((v) => v + 1);
    setActiveConversationId(null);
  }, []);

  return (
    <AppContext.Provider
      value={{
        user,
        loadingUser,
        login,
        logout,
        refreshUser,
        sidebarCollapsed,
        mobileSidebarOpen,
        setSidebarCollapsed,
        toggleSidebar,
        setMobileSidebarOpen,
        conversations,
        activeConversationId,
        setActiveConversationId,
        refreshConversations,
        deleteConversation,
        clearConversations,
        renameConversation,
        pinned,
        titles,
        chatReset,
        requestNewChat,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}
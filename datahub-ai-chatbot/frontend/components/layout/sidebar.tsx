"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useRouter } from "next/navigation";
import {
  Database,
  Star,
  Pin,
  Plus,
  Search as SearchIcon,
  Trash2,
} from "lucide-react";

import { SidebarHeader } from "@/components/layout/sidebar-header";
import { SidebarFooter } from "@/components/layout/sidebar-footer";
import { NavigationMenu, type NavItem } from "@/components/layout/navigation-menu";
import { ConversationHistory } from "@/components/chat/conversation-history";
import { ConversationSearchDialog } from "@/components/chat/conversation-search-dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useApp } from "@/lib/app-store";
import { cn } from "@/lib/utils";

export function Sidebar() {
  const {
    user,
    sidebarCollapsed,
    mobileSidebarOpen,
    setMobileSidebarOpen,
    toggleSidebar,
    conversations,
    titles,
    activeConversationId,
    setActiveConversationId,
    refreshConversations,
    deleteConversation,
    clearConversations,
    renameConversation,
    requestNewChat,
  } = useApp();

  const router = useRouter();
  const [searchOpen, setSearchOpen] = useState(false);
  const [confirmClearAll, setConfirmClearAll] = useState(false);
  const historyRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (user) refreshConversations();
  }, [user, refreshConversations]);

  const collapsed = sidebarCollapsed;

  const assistantNav: NavItem[] = [
    { label: "Search DataHub", href: "/search", icon: SearchIcon },
    { label: "DataHub", href: "http://localhost:9002", icon: Database, external: true },
    { label: "Favorites", icon: Star, soon: true },
    { label: "Pinned", icon: Pin, soon: true },
  ];

  const displayConvs = conversations.map((c) => ({
    ...c,
    last_question: titles[c.conversation_id] || c.last_question,
  }));

  return (
    <>
      {/* Mobile backdrop */}
      <AnimatePresence>
        {mobileSidebarOpen && (
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-30 bg-black/50 md:hidden"
            onClick={() => setMobileSidebarOpen(false)}
            aria-hidden
          />
        )}
      </AnimatePresence>

      {/* Desktop thin rail placeholder when collapsed (logo/avatar handled below) */}
      <motion.aside
        initial={false}
        animate={{
          width: mobileSidebarOpen ? 300 : collapsed ? 64 : 300,
        }}
        transition={{ type: "tween", duration: 0.25, ease: "easeInOut" }}
        className={cn(
          "relative z-40 flex shrink-0 flex-col border-r bg-sidebar text-sidebar-foreground",
          "md:static md:translate-x-0",
          "fixed inset-y-0 left-0 md:w-auto max-md:transition-none",
          mobileSidebarOpen ? "max-md:translate-x-0" : "max-md:-translate-x-full"
        )}
        style={{ height: "100%" }}
      >
        <SidebarHeader
          collapsed={collapsed && !mobileSidebarOpen}
          onToggle={toggleSidebar}
          onSearch={() => setSearchOpen(true)}
        />

        <ScrollArea className="flex-1">
          {!collapsed && (
            <div className="pb-2 pt-2">
              <NavigationMenu items={assistantNav} collapsed={collapsed} className="mb-2 gap-1" />

              {/* New Chat */}
              <div className="px-2 pb-4">
                <Button
                  variant="ghost"
                  className={cn(
                    "text-primary hover:bg-primary/10 hover:text-primary",
                    collapsed && "h-10 w-10 rounded-lg px-0",
                    "w-full justify-start gap-2"
                  )}
                  onClick={() => {
                    requestNewChat();
                    setMobileSidebarOpen(false);
                    router.push("/chat");
                  }}
                >
                  <Plus className="h-4 w-4" />
                  {!collapsed && <span>New Chat</span>}
                </Button>
              </div>

              {/* Recents */}
              <div ref={historyRef} className="px-2">
                <div className="flex items-center justify-between px-2 pb-1">
                  <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                    Recents
                  </p>
                  {conversations.length > 0 && (
                    <button
                      type="button"
                      onClick={() => setConfirmClearAll(true)}
                      className="flex items-center gap-1 rounded px-1 py-0.5 text-[11px] text-muted-foreground transition-colors hover:bg-accent hover:text-destructive"
                      aria-label="Xóa toàn bộ lịch sử chat"
                      title="Xóa toàn bộ lịch sử chat"
                    >
                      <Trash2 className="h-3 w-3" />
                      Xóa tất cả
                    </button>
                  )}
                </div>
                <ConversationHistory
                  conversations={displayConvs}
                  activeId={activeConversationId}
                  onSelect={(id) => {
                    setActiveConversationId(id);
                    setMobileSidebarOpen(false);
                  }}
                  onDelete={deleteConversation}
                  onRename={renameConversation}
                />
              </div>
            </div>
          )}
        </ScrollArea>

        <SidebarFooter collapsed={collapsed && !mobileSidebarOpen} />
      </motion.aside>

      <ConversationSearchDialog
        open={searchOpen}
        onOpenChange={setSearchOpen}
        conversations={displayConvs}
        onSelect={(id) => {
          setActiveConversationId(id);
          setSearchOpen(false);
        }}
        onDelete={(id) => {
          deleteConversation(id);
          setSearchOpen(false);
        }}
      />

      <Dialog open={confirmClearAll} onOpenChange={setConfirmClearAll}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Xóa toàn bộ lịch sử chat?</DialogTitle>
            <DialogDescription>
              Toàn bộ các cuộc trò chuyện sẽ bị xóa vĩnh viễn và không thể khôi phục.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setConfirmClearAll(false)}>
              Hủy
            </Button>
            <Button
              variant="destructive"
              onClick={async () => {
                setConfirmClearAll(false);
                await clearConversations();
              }}
            >
              Xóa tất cả
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
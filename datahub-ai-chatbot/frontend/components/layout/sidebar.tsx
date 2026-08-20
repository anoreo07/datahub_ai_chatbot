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
  List,
  HardDrive,
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
    togglePin,
    toggleFavorite,
    pinned,
    favorites,
    requestNewChat,
  } = useApp();

  const router = useRouter();
  const [searchOpen, setSearchOpen] = useState(false);
  const [confirmClearAll, setConfirmClearAll] = useState(false);
  const [favoriteView, setFavoriteView] = useState(false);
  const historyRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (user) refreshConversations();
  }, [user, refreshConversations]);

  const collapsed = sidebarCollapsed;

  const assistantNav: NavItem[] = [
    { label: "Search DataHub", href: "/search", icon: SearchIcon },
    { label: "Storage", href: "/storage", icon: HardDrive },
    { label: "DataHub", href: "https://datahub.vinfastauto.com/", icon: Database, external: true },
  ];

  const displayConvs = conversations.map((c) => ({
    ...c,
    title: titles[c.conversation_id] || c.title,
    last_question: titles[c.conversation_id] || c.last_question,
  }));

  const pinnedConvs = displayConvs.filter((c) => pinned.includes(c.conversation_id));

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
          width: mobileSidebarOpen ? 330 : collapsed ? 64 : 330,
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

              {/* Pinned */}
              {pinnedConvs.length > 0 && (
                <div className="pb-2 pr-6">
                  <p className="flex items-center gap-1.5 px-2.5 pb-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                    <Pin className="h-3 w-3" /> Pinned
                  </p>
                  <div className="flex flex-col gap-0.5">
                    {pinnedConvs.map((c) => (
                      <div
                        key={c.conversation_id}
                        className={cn(
                          "group flex items-center gap-1.5 rounded-lg py-1.5 pl-7 pr-1 transition-colors",
                          c.conversation_id === activeConversationId
                            ? "bg-accent"
                            : "hover:bg-accent/60"
                        )}
                      >
                        <button
                          type="button"
                          onClick={() => {
                            setActiveConversationId(c.conversation_id);
                            setMobileSidebarOpen(false);
                          }}
                          className="flex min-w-0 flex-1 items-center gap-2 text-left"
                        >
                          <span className="text-muted-foreground">•</span>
                          <span className="truncate text-sm">
                            {c.title || c.last_question || "Cuộc trò chuyện"}
                          </span>
                        </button>
                        <button
                          type="button"
                          onClick={() => togglePin(c.conversation_id)}
                          aria-label="Bỏ ghim"
                          title="Bỏ ghim"
                          className="shrink-0 rounded p-1 text-muted-foreground opacity-0 transition-opacity hover:bg-muted hover:text-foreground group-hover:opacity-100"
                        >
                          <Pin className="h-3 w-3 fill-current" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Recents / Favorites */}
              <div ref={historyRef} className="px-2.5 pr-6">
                <div className="flex items-center justify-between pb-1 pl-2 pr-2">
                  <div className="flex gap-0.5">
                    <button
                      type="button"
                      onClick={() => setFavoriteView(false)}
                      className={cn(
                        "flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium transition-colors",
                        !favoriteView
                          ? "bg-primary/10 text-primary"
                          : "text-muted-foreground hover:bg-accent"
                      )}
                    >
                      <List className="h-3 w-3" /> Recents
                    </button>
                    <button
                      type="button"
                      onClick={() => setFavoriteView(true)}
                      className={cn(
                        "flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium transition-colors",
                        favoriteView
                          ? "bg-primary/10 text-primary"
                          : "text-muted-foreground hover:bg-accent"
                      )}
                    >
                      <Star className={cn("h-3 w-3", favoriteView && "fill-current")} />
                      Yêu thích
                      {favorites.length > 0 && (
                        <span className="rounded-full bg-muted px-1 text-[10px]">{favorites.length}</span>
                      )}
                    </button>
                  </div>
                  {!favoriteView && conversations.length > 0 && (
                    <button
                      type="button"
                      onClick={() => setConfirmClearAll(true)}
                      className="mr-1 flex items-center gap-1 rounded px-1 py-0.5 text-[11px] text-muted-foreground transition-colors hover:bg-accent hover:text-destructive"
                      aria-label="Xóa toàn bộ lịch sử chat"
                      title="Xóa toàn bộ lịch sử chat"
                    >
                      <Trash2 className="h-3 w-3" /> Xóa tất cả
                    </button>
                  )}
                </div>

                {favoriteView && favorites.length === 0 ? (
                  <div className="flex flex-col items-center gap-2 px-4 py-8 text-center">
                    <Star className="h-6 w-6 text-muted-foreground" />
                    <p className="text-xs text-muted-foreground">Chưa có cuộc trò chuyện yêu thích</p>
                  </div>
                ) : favoriteView ? (
                  <ConversationHistory
                    conversations={displayConvs.filter((c) => favorites.includes(c.conversation_id))}
                    activeId={activeConversationId}
                    pinned={pinned}
                    favorites={favorites}
                    onSelect={(id) => {
                      setActiveConversationId(id);
                      setMobileSidebarOpen(false);
                    }}
                    onDelete={deleteConversation}
                    onRename={renameConversation}
                    onTogglePin={togglePin}
                    onToggleFavorite={toggleFavorite}
                  />
                ) : (
                  <ConversationHistory
                    conversations={displayConvs}
                    activeId={activeConversationId}
                    pinned={pinned}
                    favorites={favorites}
                    onSelect={(id) => {
                      setActiveConversationId(id);
                      setMobileSidebarOpen(false);
                    }}
                    onDelete={deleteConversation}
                    onRename={renameConversation}
                    onTogglePin={togglePin}
                    onToggleFavorite={toggleFavorite}
                  />
                )}
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
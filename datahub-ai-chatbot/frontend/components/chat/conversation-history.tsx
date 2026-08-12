"use client";

import { MessageSquareText } from "lucide-react";

import { ConversationCard } from "@/components/chat/conversation-card";
import type { Conversation } from "@/lib/app-store";

interface ConversationHistoryProps {
  conversations: Conversation[];
  activeId?: string | null;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onRename: (id: string, title: string) => void;
  onTogglePin: (id: string) => void;
  onToggleFavorite: (id: string) => void;
  pinned: string[];
  favorites: string[];
}

export function ConversationHistory({
  conversations,
  activeId,
  onSelect,
  onDelete,
  onRename,
  onTogglePin,
  onToggleFavorite,
  pinned,
  favorites,
}: ConversationHistoryProps) {
  if (!conversations.length) {
    return (
      <div className="flex flex-col items-center gap-2 px-4 py-8 text-center">
        <MessageSquareText className="h-6 w-6 text-muted-foreground" />
        <p className="text-xs text-muted-foreground">Chưa có cuộc trò chuyện nào</p>
      </div>
    );
  }

  const sorted = [...conversations].sort((a, b) => {
    const aPinned = pinned.includes(a.conversation_id) ? 1 : 0;
    const bPinned = pinned.includes(b.conversation_id) ? 1 : 0;
    if (aPinned !== bPinned) return bPinned - aPinned;
    const aFav = favorites.includes(a.conversation_id) ? 1 : 0;
    const bFav = favorites.includes(b.conversation_id) ? 1 : 0;
    if (aFav !== bFav) return bFav - aFav;
    return (b.last_accessed || 0) - (a.last_accessed || 0);
  });

  return (
    <div className="flex flex-col gap-0.5">
      {sorted.map((c) => (
        <ConversationCard
          key={c.conversation_id}
          conversation={c}
          active={c.conversation_id === activeId}
          pinned={pinned.includes(c.conversation_id)}
          favorite={favorites.includes(c.conversation_id)}
          onSelect={() => onSelect(c.conversation_id)}
          onDelete={onDelete}
          onRename={onRename}
          onTogglePin={onTogglePin}
          onToggleFavorite={onToggleFavorite}
        />
      ))}
    </div>
  );
}

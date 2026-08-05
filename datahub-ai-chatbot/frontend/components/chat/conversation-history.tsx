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
}

export function ConversationHistory({
  conversations,
  activeId,
  onSelect,
  onDelete,
  onRename,
}: ConversationHistoryProps) {
  if (!conversations.length) {
    return (
      <div className="flex flex-col items-center gap-2 px-4 py-8 text-center">
        <MessageSquareText className="h-6 w-6 text-muted-foreground" />
        <p className="text-xs text-muted-foreground">Chưa có cuộc trò chuyện nào</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-0.5">
      {conversations.map((c) => (
        <ConversationCard
          key={c.conversation_id}
          conversation={c}
          active={c.conversation_id === activeId}
          onSelect={() => onSelect(c.conversation_id)}
          onDelete={onDelete}
          onRename={onRename}
          onTogglePin={() => {}}
        />
      ))}
    </div>
  );
}

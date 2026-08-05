"use client";

import { useMemo, useState } from "react";
import { MessageSquareText, Search, Trash2 } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import type { Conversation } from "@/lib/app-store";

interface ConversationSearchDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  conversations: Conversation[];
  onSelect: (id: string) => void;
  onDelete?: (id: string) => void;
}

export function ConversationSearchDialog({
  open,
  onOpenChange,
  conversations,
  onSelect,
  onDelete,
}: ConversationSearchDialogProps) {
  const [query, setQuery] = useState("");

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return conversations.slice(0, 20);
    return conversations
      .filter(
        (c) =>
          c.last_question?.toLowerCase().includes(q) || c.conversation_id.toLowerCase().includes(q)
      )
      .slice(0, 20);
  }, [query, conversations]);

  const handleSelect = (id: string) => {
    onSelect(id);
    setQuery("");
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Tìm kiếm cuộc trò chuyện</DialogTitle>
          <DialogDescription>Nhập từ khóa để lọc lịch sử hội thoại.</DialogDescription>
        </DialogHeader>
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Tìm kiếm…"
            className="pl-9"
            onKeyDown={(e) => {
              if (e.key === "Enter" && results[0]) handleSelect(results[0].conversation_id);
            }}
          />
        </div>
        <div className="flex max-h-72 flex-col gap-0.5 overflow-y-auto">
          {results.length === 0 && (
            <p className="py-6 text-center text-sm text-muted-foreground">Không tìm thấy</p>
          )}
          {results.map((c) => (
            <div
              key={c.conversation_id}
              className="group flex items-center gap-1 rounded-lg transition-colors hover:bg-accent"
            >
              <button
                onClick={() => handleSelect(c.conversation_id)}
                className="flex min-w-0 flex-1 items-center gap-3 px-3 py-2 text-left"
              >
                <MessageSquareText className="h-4 w-4 shrink-0 text-muted-foreground" />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium">
                    {c.last_question || "Cuộc trò chuyện"}
                  </span>
                  <span className="block truncate text-xs text-muted-foreground">
                    {c.conversation_id}
                  </span>
                </span>
              </button>
              {onDelete && (
                <button
                  onClick={() => onDelete(c.conversation_id)}
                  aria-label={`Xóa cuộc trò chuyện ${c.last_question || ""}`}
                  className="mr-2 flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-muted-foreground opacity-0 transition-opacity hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
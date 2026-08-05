"use client";

import { useState } from "react";
import {
  MoreHorizontal,
  MessageSquare,
  Pencil,
  Pin,
  Trash2,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import type { Conversation } from "@/lib/app-store";

interface ConversationCardProps {
  conversation: Conversation;
  active?: boolean;
  collapsed?: boolean;
  onSelect?: () => void;
  onDelete?: (id: string) => void;
  onRename?: (id: string, title: string) => void;
  onTogglePin?: (id: string) => void;
}

function shortTitle(c: Conversation) {
  const q = c.last_question?.trim();
  if (q) return q.length > 37 ? q.slice(0, 37) + "…" : q;
  return "Cuộc trò chuyện";
}

export function ConversationCard({
  conversation,
  active,
  collapsed,
  onSelect,
  onDelete,
  onRename,
  onTogglePin,
}: ConversationCardProps) {
  const [editing, setEditing] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [draft, setDraft] = useState(shortTitle(conversation));

  const commitRename = () => {
    onRename?.(conversation.conversation_id, draft.trim() || shortTitle(conversation));
    setEditing(false);
  };

  if (collapsed) {
    return (
      <button
        onClick={onSelect}
        className={cn(
          "mx-2 flex h-8 w-8 items-center justify-center rounded-lg transition-colors",
          active ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-accent"
        )}
        aria-label={shortTitle(conversation)}
      >
        <MessageSquare className="h-4 w-4" />
      </button>
    );
  }

  return (
    <div
      className={cn(
        "group flex items-center gap-2 rounded-lg px-2 py-1.5 transition-colors",
        active ? "bg-accent" : "hover:bg-accent/60"
      )}
    >
      {editing ? (
        <Input
          autoFocus
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") commitRename();
            if (e.key === "Escape") setEditing(false);
          }}
          onBlur={commitRename}
          className="h-7 flex-1 text-sm"
        />
      ) : (
        <button
          onClick={onSelect}
          className="flex min-w-0 flex-1 items-center gap-2 text-left"
        >
          <MessageSquare className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          <span className="truncate text-sm">{shortTitle(conversation)}</span>
        </button>
      )}

      {!editing && (
        <div className="flex shrink-0 items-center">
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100 focus:opacity-100"
            onClick={() => setConfirmingDelete(true)}
            aria-label={`Xóa: ${shortTitle(conversation)}`}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 shrink-0 opacity-0 transition-opacity group-hover:opacity-100 focus:opacity-100"
                aria-label={`Tùy chọn: ${shortTitle(conversation)}`}
              >
                <MoreHorizontal className="h-3.5 w-3.5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-40">
              <DropdownMenuItem onClick={() => setEditing(true)}>
                <Pencil className="h-4 w-4" /> Đổi tên
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onTogglePin?.(conversation.conversation_id)}>
                <Pin className="h-4 w-4" /> Ghim
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="text-destructive focus:text-destructive"
                onClick={() => setConfirmingDelete(true)}
              >
                <Trash2 className="h-4 w-4" /> Xóa
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      )}

      <Dialog open={confirmingDelete} onOpenChange={setConfirmingDelete}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Xóa cuộc trò chuyện?</DialogTitle>
            <DialogDescription>
              &ldquo;{shortTitle(conversation)}&rdquo; sẽ bị xóa vĩnh viễn và không thể khôi phục.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setConfirmingDelete(false)}>
              Hủy
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                setConfirmingDelete(false);
                onDelete?.(conversation.conversation_id);
              }}
            >
              Xóa
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
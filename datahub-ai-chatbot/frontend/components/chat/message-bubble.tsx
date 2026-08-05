"use client";

import Image from "next/image";
import { User, Sparkles } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";

import { Markdown } from "@/components/chat/markdown";
import { LineageGraph } from "@/components/chat/lineage-graph";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { cn, formatTime } from "@/lib/utils";
import type { ChatMessage } from "@/lib/use-chat";

interface MessageBubbleProps {
  message: ChatMessage;
  onApplySuggestion?: (suggested: string) => void;
}

function Citations({ ids, urls }: { ids?: (string | undefined)[]; urls?: (string | undefined)[] }) {
  const list = (ids || []).map((id, i) => ({ id, url: urls?.[i] }));
  if (list.length === 0) return null;
  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {list.map((c, i) => (
        <a
          key={`${c.id}-${i}`}
          href={c.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary transition-colors hover:bg-primary/20"
        >
          {c.id}
        </a>
      ))}
    </div>
  );
}

function Entities({ items }: { items?: ChatMessage["entities"] }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {items.map((e, i) => (
        <span
          key={i}
          className="inline-flex items-center rounded-full bg-muted px-2.5 py-0.5 text-xs text-muted-foreground"
        >
          {e.url ? (
            <a href={e.url} target="_blank" rel="noopener noreferrer" className="hover:text-primary">
              {e.name || e.urn}
            </a>
          ) : (
            e.name || e.urn
          )}
        </span>
      ))}
    </div>
  );
}

export function MessageBubble({ message, onApplySuggestion }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const isError = message.role === "error";
  const time = formatTime(new Date(message.timestamp).toISOString());

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={cn("flex w-full gap-3", isUser ? "justify-end" : "justify-start")}
    >
      {!isUser && (
        <Avatar className="mt-0.5 h-10 w-10 shrink-0 overflow-hidden rounded-full">
          <Image
            src="/logo.png"
            alt="DataAtlas"
            width={40}
            height={40}
            className="h-full w-full object-cover"
          />
        </Avatar>
      )}

      <div className={cn("flex max-w-[85%] flex-col", isUser ? "items-end" : "items-start sm:max-w-[78%]")}>
        <div
          className={cn(
            "rounded-3xl px-5 py-3 text-[15px] shadow-sm",
            isUser
              ? "rounded-br-md bg-user-msg text-user-msg-foreground"
              : isError
                ? "rounded-bl-md bg-destructive/10 text-destructive"
                : "rounded-bl-md bg-bot-msg text-bot-msg-foreground"
          )}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
          ) : (
            <AnimatePresence>
              {message.streaming && message.content === "" ? (
                <StreamingTyping />
              ) : (
                <Markdown content={message.content} />
              )}
            </AnimatePresence>
          )}

          {!isUser && message.lineage && <LineageGraph lg={message.lineage} />}

          {message.suggestion && (
            <SuggestionBox suggested={message.suggestion.suggested} onApply={onApplySuggestion} />
          )}
        </div>

        {!isUser && (
          <div className="mt-1 flex flex-col items-start gap-1 px-1">
            <Citations
              ids={message.citations?.map((c) => c.id)}
              urls={message.citations?.map((c) => c.url)}
            />
            <Entities items={message.entities} />
          </div>
        )}

        <span
          className={cn(
            "mt-1 px-1 text-[10px] text-muted-foreground",
            isUser && "text-right"
          )}
        >
          {time}
          {!isUser && message.confidence && ` · ${message.confidence}`}
          {!isUser && message.ambiguous && " · ambiguous"}
        </span>
      </div>

      {isUser && (
        <Avatar className="mt-0.5 h-10 w-10 shrink-0">
          <AvatarFallback className="bg-user-msg/15 text-user-msg">
            <User className="h-5 w-5" />
          </AvatarFallback>
        </Avatar>
      )}
    </motion.div>
  );
}

function StreamingTyping() {
  return (
    <div className="flex items-center gap-2 py-1 text-sm text-muted-foreground">
      <span className="flex gap-1">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
      </span>
      <Sparkles className="h-4 w-4 text-primary" />
    </div>
  );
}

function SuggestionBox({
  suggested,
  onApply,
}: {
  suggested: string;
  onApply?: (s: string) => void;
}) {
  return (
    <div className="mt-2 rounded-lg border border-warning/40 bg-warning/10 px-3 py-2 text-sm">
      <p className="mb-2">
        Ý bạn là <b className="text-primary">{suggested}</b>?
      </p>
      <div className="flex gap-2">
        <Button size="sm" onClick={() => onApply?.(suggested)}>
          Đồng ý với gợi ý
        </Button>
        <Button size="sm" variant="ghost">
          Để sau
        </Button>
      </div>
    </div>
  );
}

// scoped dot animation styles are declared in globals.css (.dot)
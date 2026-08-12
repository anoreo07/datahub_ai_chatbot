"use client";

import { useState } from "react";
import Image from "next/image";
import { User, Sparkles, ChevronDown, ChevronUp, X } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";

import { Markdown } from "@/components/chat/markdown";
import { LineageGraph } from "@/components/chat/lineage-graph";
import { QualityReportCard } from "@/components/chat/quality-report-card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { cn, formatTime } from "@/lib/utils";
import { getRoleAvatar } from "@/lib/avatar";
import { useApp } from "@/lib/app-store";
import type { ChatMessage } from "@/lib/use-chat";

interface MessageBubbleProps {
  message: ChatMessage;
  onApplySuggestion?: (suggested: string) => void;
}

const MAX_VISIBLE_CITATIONS = 5;

function UserMessageContent({
  message,
  onOpenImage,
}: {
  message: ChatMessage;
  onOpenImage?: (src: string) => void;
}) {
  const text = message.displayContent || message.content;
  const match = /^<tag>(.*?)<\/tag>\s?/.exec(text);
  return (
    <div className="flex flex-col gap-2">
      {(message.images?.length ?? 0) > 0 && (
        <div className="flex flex-wrap gap-2">
          {message.images!.map((src, i) => (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              key={i}
              src={src}
              alt={`Ảnh đính kèm ${i + 1}`}
              onClick={() => onOpenImage?.(src)}
              className="max-h-64 max-w-xs cursor-zoom-in rounded-lg object-cover transition-transform hover:scale-[1.02]"
            />
          ))}
        </div>
      )}
      {match ? (
        <p className="whitespace-pre-wrap leading-relaxed">
          <span className="mr-2 inline-flex max-w-full align-middle items-center gap-1.5 rounded-full bg-user-msg-foreground px-2.5 py-0.5 text-xs font-semibold text-user-msg shadow-sm">
            <Sparkles className="h-3 w-3 shrink-0" />
            {match[1]}
          </span>
          {text.slice(match[0].length)}
        </p>
      ) : (
        <p className="whitespace-pre-wrap leading-relaxed">{text}</p>
      )}
    </div>
  );
}

function Citations({ ids, urls }: { ids?: (string | undefined)[]; urls?: (string | undefined)[] }) {
  const list = (ids || []).map((id, i) => ({ id, url: urls?.[i] }));
  const [expanded, setExpanded] = useState(false);
  if (list.length === 0) return null;

  const hasMore = list.length > MAX_VISIBLE_CITATIONS;
  const visible = expanded ? list : list.slice(0, MAX_VISIBLE_CITATIONS);
  const hiddenCount = list.length - visible.length;

  return (
    <div className="mt-2 flex flex-wrap items-center gap-1.5">
      {visible.map((c, i) => (
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
      {hasMore && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="inline-flex items-center gap-1 rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted/70"
        >
          {expanded ? (
            <>
              Thu gọn <ChevronUp className="h-3 w-3" />
            </>
          ) : (
            <>
              +{hiddenCount} khác <ChevronDown className="h-3 w-3" />
            </>
          )}
        </button>
      )}
    </div>
  );
}

function Entities({ items }: { items?: ChatMessage["entities"] }) {
  const [expanded, setExpanded] = useState(false);
  if (!items || items.length === 0) return null;

  const hasMore = items.length > MAX_VISIBLE_CITATIONS;
  const visible = expanded ? items : items.slice(0, MAX_VISIBLE_CITATIONS);
  const hiddenCount = items.length - visible.length;

  return (
    <div className="mt-2 flex flex-wrap items-center gap-1.5">
      {visible.map((e, i) => (
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
      {hasMore && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary transition-colors hover:bg-primary/20"
        >
          {expanded ? (
            <>
              Thu gọn <ChevronUp className="h-3 w-3" />
            </>
          ) : (
            <>
              +{hiddenCount} khác <ChevronDown className="h-3 w-3" />
            </>
          )}
        </button>
      )}
    </div>
  );
}

export function MessageBubble({ message, onApplySuggestion }: MessageBubbleProps) {
  const { user } = useApp();
  const userAvatar = getRoleAvatar(user);
  const isUser = message.role === "user";
  const isError = message.role === "error";
  const time = formatTime(new Date(message.timestamp).toISOString());
  const [lightbox, setLightbox] = useState<string | null>(null);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={cn(
        "flex w-full gap-3",
        isUser ? "justify-end -mr-4" : "justify-start -ml-4"
      )}
    >
      {!isUser && (
        <Avatar className="mt-0.5 h-14 w-14 shrink-0 overflow-hidden rounded-full">
          <Image
            src="/logo.png"
            alt="DataAtlas"
            width={56}
            height={56}
            className="h-full w-full object-cover"
          />
        </Avatar>
      )}

      <div className={cn("flex max-w-[90%] flex-col", isUser ? "items-end" : "items-start sm:max-w-[84%]")}>
        <div
          className={cn(
            "rounded-3xl px-7 py-4 text-[15px] shadow-sm",
            isUser
              ? "rounded-br-md bg-user-msg text-user-msg-foreground"
              : isError
                ? "rounded-bl-md bg-destructive/10 text-destructive"
                : "rounded-bl-md bg-bot-msg text-bot-msg-foreground"
          )}
        >
          {isUser ? (
            <UserMessageContent message={message} onOpenImage={setLightbox} />
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

          {!isUser && message.quality_report && (
            <QualityReportCard report={message.quality_report} />
          )}

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
        <Avatar className="mt-0.5 h-14 w-14 shrink-0">
          {userAvatar && <AvatarImage src={userAvatar} alt="User" />}
          <AvatarFallback className="bg-user-msg/15 text-user-msg">
            <User className="h-7 w-7" />
          </AvatarFallback>
        </Avatar>
      )}

      <AnimatePresence>
        {lightbox && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[100] flex items-center justify-center bg-black/85 p-4"
            onClick={() => setLightbox(null)}
          >
            <motion.button
              type="button"
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="absolute right-4 top-4 flex h-10 w-10 items-center justify-center rounded-full bg-white/15 text-white transition-colors hover:bg-white/30"
              aria-label="Đóng"
              onClick={() => setLightbox(null)}
            >
              <X className="h-5 w-5" />
            </motion.button>
            <motion.div
              initial={{ scale: 0.95 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.95 }}
              onClick={(e) => e.stopPropagation()}
              className="max-h-full max-w-full"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={lightbox}
                alt="Xem ảnh"
                className="max-h-[92vh] max-w-[92vw] rounded-lg object-contain shadow-2xl"
              />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
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
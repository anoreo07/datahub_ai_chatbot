"use client";

import { useState } from "react";
import { User, Sparkles, ChevronDown, ChevronUp, X, Bot, Copy, Check, AlertTriangle, Clock } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";

import { LineageGraph } from "@/components/chat/lineage-graph";
import { QualityReportCard } from "@/components/chat/quality-report-card";
import { MessageRenderer } from "@/components/chat/message-renderer";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { cn, formatTime } from "@/lib/utils";
import { getRoleAvatar } from "@/lib/avatar";
import { useApp } from "@/lib/app-store";
import type { ChatMessage } from "@/lib/use-chat";
import type { EntityItem, RecoveryAction } from "@/lib/types";

function formatResponseTime(ms: number): string {
  if (ms < 1000) {
    return `${ms}ms`;
  }
  return `${(ms / 1000).toFixed(2)}s`;
}


interface MessageBubbleProps {
  message: ChatMessage;
  onApplySuggestion?: (suggested: string) => void;
  onEntityClick?: (entity: EntityItem) => void;
  onCitationClick?: (citation: { id: string; url?: string; entity_urn?: string }) => void;
  onRecoveryAction?: (action: RecoveryAction) => void;
  onConfirmClarification?: (candidate: { name: string; urn: string; entity_type?: string }) => void;
  onRejectClarification?: () => void;
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
  const hasImages = (message.images?.length ?? 0) > 0;
  const caption = hasImages ? text : text;
  return (
    <div className="flex flex-col">
      {hasImages && (
        <div className="-mx-4 -mt-3 -mb-1 md:-mx-7 md:-mt-4 md:-mb-1 overflow-hidden first:rounded-t-3xl md:first:rounded-t-3xl">
          <div className={cn("flex flex-wrap", message.images!.length > 1 && "gap-1")}>
            {message.images!.map((src, i) => (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                key={i}
                src={src}
                alt={`Ảnh đính kèm ${i + 1}`}
                onClick={() => onOpenImage?.(src)}
                className={cn(
                  "max-h-80 w-full cursor-zoom-in object-contain transition-transform hover:opacity-90",
                  message.images!.length === 1 && "rounded-t-3xl md:first:rounded-t-3xl",
                  message.images!.length > 1 && "flex-1 min-w-0 max-w-[50%]"
                )}
              />
            ))}
          </div>
        </div>
      )}
      {caption && (
        <div className={cn("px-1", hasImages && "pt-2 pb-0")}>
          {match ? (
            <p className="whitespace-pre-wrap leading-relaxed">
              <span className="mr-2 inline-flex max-w-full align-middle items-center gap-1.5 rounded-full bg-white px-3 py-1 text-xs font-bold text-blue-600 shadow-md ring-1 ring-blue-200">
                <Sparkles className="h-3 w-3 shrink-0" />
                {match[1]}
              </span>
              {caption.slice(match[0].length)}
            </p>
          ) : (
            <p className="whitespace-pre-wrap leading-relaxed">{caption}</p>
          )}
        </div>
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

function CopyButton({ text, className }: { text: string; className?: string }) {
  const [copied, setCopied] = useState(false);
  if (!text.trim()) return null;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable */
    }
  };

  return (
    <button
      type="button"
      aria-label="Copy nội dung"
      title="Copy nội dung"
      onClick={copy}
      className={cn(
        "flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground/70 transition-all",
        "hover:bg-muted hover:text-foreground hover:shadow-sm",
        "active:scale-95",
        className
      )}
    >
      {copied ? <Check className="h-4 w-4 text-emerald-500" /> : <Copy className="h-4 w-4" />}
    </button>
  );
}

export function MessageBubble({
  message,
  onApplySuggestion,
  onEntityClick,
  onCitationClick,
  onRecoveryAction,
  onConfirmClarification,
  onRejectClarification,
}: MessageBubbleProps) {
  const { user, showResponseTime } = useApp();
  const userAvatar = getRoleAvatar(user);
  const isUser = message.role === "user";
  const isError = message.role === "error";
  const time = formatTime(new Date(message.timestamp).toISOString());
  const [lightbox, setLightbox] = useState<string | null>(null);
  const copyText = isUser
    ? message.displayContent || message.content || ""
    : message.content || "";

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={cn(
        "group flex w-full gap-3",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      {!isUser && (
        <Avatar className="mt-0.5 h-10 w-10 shrink-0 overflow-hidden rounded-full bg-bot-msg text-bot-msg-foreground md:h-14 md:w-14">
          <AvatarImage src="/logo.png" alt="DataHub AI" />
          <AvatarFallback>
            <Bot className="h-5 w-5 md:h-7 md:w-7" />
          </AvatarFallback>
        </Avatar>
      )}

      <div
        className={cn(
          "relative flex flex-col",
          isUser
            ? "max-w-[90%] items-end md:max-w-[70%]"
            : "max-w-[90%] items-start md:max-w-[85%]"
        )}
      >
        <div
          className={cn(
            "rounded-3xl px-4 py-3 text-[15px] shadow-md md:px-7 md:py-4",
            isUser
              ? "rounded-br-md bg-user-msg text-user-msg-foreground"
              : isError
                ? "rounded-bl-md border border-amber-200/60 bg-amber-50 text-amber-900 dark:border-amber-800/40 dark:bg-amber-950/50 dark:text-amber-200"
                : "rounded-bl-md bg-bot-msg text-bot-msg-foreground"
          )}
        >
          {isError && (
            <div className="mb-2 flex items-center gap-2">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-amber-100 dark:bg-amber-900/60">
                <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
              </span>
              <span className="text-sm font-medium text-amber-700 dark:text-amber-300">Cảnh báo</span>
            </div>
          )}
          {!isUser && !isError && (message.intent === "THINKING_OVERVIEW" || message.intent === "COMPARISON") && (
            <div className="mb-2.5 inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-semibold text-primary ring-1 ring-primary/20">
              <Sparkles className="h-3.5 w-3.5" />
              <span>Thinking Mode</span>
            </div>
          )}
          {isUser ? (
            <UserMessageContent message={message} onOpenImage={setLightbox} />
          ) : (
            <AnimatePresence>
              {message.streaming && message.content === "" ? (
                <StreamingTyping />
              ) : (
                <MessageRenderer
                  message={message}
                  onApplySuggestion={onApplySuggestion}
                  onEntityClick={onEntityClick}
                  onRecoveryAction={onRecoveryAction}
                  onConfirmClarification={onConfirmClarification}
                  onRejectClarification={onRejectClarification}
                />
              )}
            </AnimatePresence>
          )}

          {!isUser && message.selected_action === "lineage" && message.lineage && (
            <LineageGraph lg={message.lineage} />
          )}

          {!isUser && message.quality_report && (
            <QualityReportCard report={message.quality_report} />
          )}

          {message.suggestion && (
            <SuggestionBox suggested={message.suggestion.suggested} onApply={onApplySuggestion} />
          )}
        </div>

        {!isUser && showResponseTime && typeof message.response_time_ms === "number" && !message.streaming && (
          <div className="mt-1.5 flex items-center gap-1.5 text-xs font-medium text-primary bg-primary/10 border border-primary/20 px-2.5 py-0.5 rounded-full w-fit">
            <Clock className="h-3 w-3 shrink-0" />
            <span>Response time: {formatResponseTime(message.response_time_ms)}</span>
          </div>
        )}

        {!isUser && !message.streaming && (
          <div className="mt-1 flex items-center gap-1 px-1">
            <CopyButton text={copyText} />
          </div>
        )}

        <span
          className={cn(
            "mt-1 px-1 text-[11px] font-medium text-muted-foreground/80",
            isUser && "text-right"
          )}
        >
          {time}
          {!isUser && message.confidence && ` · ${message.confidence}`}
          {!isUser && message.ambiguous && " · ambiguous"}
        </span>
      </div>


      {isUser && (
        <Avatar className="mt-0.5 h-10 w-10 shrink-0 md:h-14 md:w-14">
          {userAvatar && <AvatarImage src={userAvatar} alt="User" />}
          <AvatarFallback className="bg-user-msg/15 text-user-msg">
            <User className="h-5 w-5 md:h-7 md:w-7" />
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
"use client";

import { useRef, useState, type KeyboardEvent } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowUp, X } from "lucide-react";

import { ActionMenu, type ActionDef } from "@/components/chat/action-menu";
import { ModelMenu } from "@/components/chat/model-menu";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const DEFAULT_MODEL = "deepseek-v4-flash";

interface ChatInputProps {
  isStreaming: boolean;
  onSend: (question: string, suggestedName?: string, model?: string) => void;
  placeholder?: string;
}

export function ChatInput({ isStreaming, onSend, placeholder }: ChatInputProps) {
  const [value, setValue] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const [modelOpen, setModelOpen] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [activeAction, setActiveAction] = useState<ActionDef | null>(null);
  const [model, setModel] = useState<string>(DEFAULT_MODEL);
  const ref = useRef<HTMLTextAreaElement>(null);

  const canSend = value.trim().length > 0 && !isStreaming;

  const submit = () => {
    const text = value.trim();
    if (!text || isStreaming) return;
    // Compose the final question: keep the user's wording but anchor it to the
    // selected function so the backend routes to the right intent.
    const question = activeAction
      ? `${activeAction.prompt.trim()} ${text}`.trim()
      : text;
    setValue("");
    setActiveAction(null);
    if (ref.current) ref.current.style.height = "auto";
    setMenuOpen(false);
    setModelOpen(false);
    onSend(question, undefined, model);
  };

  const pickAction = (action: ActionDef) => {
    setActiveAction(action);
    setMenuOpen(false);
    setModelOpen(false);
    requestAnimationFrame(() => {
      ref.current?.focus();
    });
  };

  const toggleActionMenu = () => {
    setMenuOpen((v) => {
      const next = !v;
      if (next) setModelOpen(false);
      return next;
    });
  };

  const toggleModelMenu = () => {
    setModelOpen((v) => {
      const next = !v;
      if (next) setMenuOpen(false);
      return next;
    });
  };

  const clearAction = () => {
    setActiveAction(null);
    ref.current?.focus();
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const autoResize = () => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = el.scrollHeight + "px";
    setExpanded(el.scrollHeight > 64);
  };

  return (
    <div className="relative px-4 pb-4 pt-2">
      <div
        className={cn(
          "relative mx-auto flex max-w-3xl items-end gap-2 rounded-3xl border bg-card p-2 shadow-lg transition-shadow focus-within:shadow-xl",
          expanded ? "items-end" : "items-center"
        )}
      >
        <ActionMenu open={menuOpen} onOpenChange={setMenuOpen} onPick={pickAction} />
        <ModelMenu
          open={modelOpen}
          onOpenChange={setModelOpen}
          selectedId={model}
          onSelect={setModel}
        />

        <Button
          type="button"
          variant="ghost"
          size="icon"
          className={cn("h-10 w-10 shrink-0 rounded-full", menuOpen && "bg-accent")}
          onClick={toggleActionMenu}
          aria-label="Menu hành động"
          aria-expanded={menuOpen}
        >
          <PlusIcon />
        </Button>

        <Button
          type="button"
          variant="ghost"
          size="icon"
          className={cn("h-10 w-10 shrink-0 rounded-full", modelOpen && "bg-accent")}
          onClick={toggleModelMenu}
          aria-label="Chọn model"
          aria-expanded={modelOpen}
          title={model}
        >
          <ModelIcon />
        </Button>

        <div className="flex min-w-0 flex-1 flex-col gap-1.5">
          {activeAction && (
            <div className="flex items-center gap-1.5 self-start rounded-full border border-primary/40 bg-primary/10 py-1 pl-3 pr-1.5">
              <span className="text-xs font-medium text-primary">
                <ActiveIcon action={activeAction} />
                {activeAction.title}
              </span>
              <button
                type="button"
                onClick={clearAction}
                aria-label="Bỏ chức năng"
                className="flex h-4 w-4 items-center justify-center rounded-full text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          )}

          <textarea
            ref={ref}
            rows={1}
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              autoResize();
            }}
            onKeyDown={onKeyDown}
            placeholder={
              activeAction?.placeholder ?? placeholder ?? "Hãy hỏi tôi thông tin về DataHub"
            }
            className="max-h-48 min-h-[34px] w-full resize-none bg-transparent py-0.5 text-base leading-relaxed outline-none placeholder:text-muted-foreground"
            aria-label="Tin nhắn"
          />
        </div>

        <AnimatePresence>
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
          >
            <Button
              type="button"
              size="icon"
              onClick={submit}
              disabled={!canSend}
              aria-label="Gửi tin nhắn"
              className="h-10 w-10 shrink-0 rounded-full"
            >
              {isStreaming ? <Dots /> : <ArrowUp className="h-5 w-5" />}
            </Button>
          </motion.div>
        </AnimatePresence>
      </div>
      <p className="mx-auto mt-1.5 max-w-3xl text-center text-[10px] text-muted-foreground">
        Enter để gửi · Shift+Enter để xuống dòng
      </p>
    </div>
  );
}

function ModelIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-5 w-5">
      <rect x="4" y="4" width="16" height="16" rx="4" />
      <path d="M9 2v4M15 2v4M9 18v4M15 18v4" strokeLinecap="round" />
    </svg>
  );
}

function ActiveIcon({ action }: { action: ActionDef }) {
  const Icon = action.icon;
  return <Icon className="mr-1 inline h-3.5 w-3.5 align-[-2px]" />;
}

function PlusIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" className="h-6 w-6">
      <path d="M12 5v14M5 12h14" strokeLinecap="round" />
    </svg>
  );
}

function Dots() {
  return <span className="flex gap-0.5"><span className="dot h-1.5 w-1.5" /><span className="dot h-1.5 w-1.5" /><span className="dot h-1.5 w-1.5" /></span>;
}
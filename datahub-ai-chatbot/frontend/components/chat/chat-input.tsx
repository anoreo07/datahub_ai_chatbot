"use client";

import { useRef, useState, type ChangeEvent, type ClipboardEvent, type KeyboardEvent } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowUp, ImageIcon, X } from "lucide-react";

import { ActionMenu, ACTION_DEFS, type ActionDef } from "@/components/chat/action-menu";
import { ModelMenu } from "@/components/chat/model-menu";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const DEFAULT_MODEL = "deepseek-v4-flash";
const MAX_IMAGES = 4;

interface ChatInputProps {
  isStreaming: boolean;
  onSend: (
    question: string,
    suggestedName?: string,
    model?: string,
    displayContent?: string,
    selectedAction?: string,
    images?: string[]
  ) => void;
  placeholder?: string;
}

export function ChatInput({ isStreaming, onSend, placeholder }: ChatInputProps) {
  const [value, setValue] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const [modelOpen, setModelOpen] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [activeAction, setActiveAction] = useState<ActionDef | null>(null);
  const [model, setModel] = useState<string>(DEFAULT_MODEL);
  const [images, setImages] = useState<string[]>([]);
  const [slashOpen, setSlashOpen] = useState(false);
  const [slashIndex, setSlashIndex] = useState(0);
  const [slashQuery, setSlashQuery] = useState("");
  const [preview, setPreview] = useState<string | null>(null);
  const ref = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const canSend = value.trim().length > 0 && !isStreaming;

  const slashMatches = slashQuery
    ? ACTION_DEFS.filter((a) =>
        `${a.title} ${a.desc}`.toLowerCase().includes(slashQuery.toLowerCase())
      )
    : ACTION_DEFS;

  const submit = () => {
    const text = value.trim();
    if (!text || isStreaming) return;
    if (slashOpen) {
      closeSlash();
      return;
    }
    // Send the RAW user wording plus the selected action as a separate intent hint.
    // The backend merges message + action + conversation context to decide the
    // actual task; the action is never blindly executed (it only frames retrieval
    // when it agrees with the message, and is overridden on a conflict).
    const selectedAction = activeAction?.kind;
    // Show the selected tag itself at the start of the user bubble instead of
    // composing/overwriting the user's wording.
    const displayContent = activeAction
      ? `<tag>${activeAction.title}</tag> ${text}`
      : text;
    const attached = images.length ? images : undefined;
    setValue("");
    setImages([]);
    setActiveAction(null);
    if (ref.current) ref.current.style.height = "auto";
    setMenuOpen(false);
    setModelOpen(false);
    onSend(text, undefined, model, displayContent, selectedAction, attached);
  };

  const closeSlash = () => {
    setSlashOpen(false);
    setSlashQuery("");
    setSlashIndex(0);
  };

  const pickSlash = (action: ActionDef) => {
    setActiveAction(action);
    setValue(value.replace(/\/[^\/]*$/, ""));
    closeSlash();
    requestAnimationFrame(() => ref.current?.focus());
  };

  const onSlashKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (!slashOpen || !slashMatches.length) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSlashIndex((i) => (i + 1) % slashMatches.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSlashIndex((i) => (i - 1 + slashMatches.length) % slashMatches.length);
    } else if (e.key === "Enter") {
      e.preventDefault();
      pickSlash(slashMatches[slashIndex]);
    } else if (e.key === "Escape") {
      e.preventDefault();
      closeSlash();
    }
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

  const onPickFiles = (e: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    const room = MAX_IMAGES - images.length;
    for (const file of files.slice(0, Math.max(room, 0))) addFile(file);
    if (fileRef.current) fileRef.current.value = "";
  };

  const removeImage = (idx: number) => {
    setImages((prev) => prev.filter((_, i) => i !== idx));
  };

  const addFile = (file: File) => {
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result as string;
      setImages((prev) =>
        prev.length < MAX_IMAGES ? [...prev, dataUrl] : prev
      );
    };
    reader.readAsDataURL(file);
  };

  const onPaste = (e: ClipboardEvent<HTMLTextAreaElement>) => {
    const items = e.clipboardData?.items;
    if (!items) return;
    const files: File[] = [];
    for (const item of items) {
      if (item.type.startsWith("image/")) {
        const file = item.getAsFile();
        if (file) files.push(file);
      }
    }
    if (files.length) {
      e.preventDefault();
      for (const f of files) addFile(f);
    }
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (slashOpen) {
      onSlashKeyDown(e);
      return;
    }
    if (e.key === "/") {
      e.preventDefault();
      setValue(value + "/");
      setSlashOpen(true);
      setSlashQuery("");
      setSlashIndex(0);
      requestAnimationFrame(() => ref.current?.focus());
      return;
    }
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
      <AnimatePresence>
        {slashOpen && (
          <motion.div
            initial={{ opacity: 0, y: 8, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.96 }}
            transition={{ duration: 0.15 }}
            className="absolute bottom-full left-1/2 z-40 mb-3 w-full max-w-3xl -translate-x-1/2"
          >
            <div className="overflow-hidden rounded-2xl border bg-popover p-1.5 shadow-lg">
              <p className="px-3 pb-1.5 pt-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                Chức năng (gõ tiếp để lọc, Enter để chọn)
              </p>
              {slashMatches.length === 0 ? (
                <p className="px-3 py-3 text-sm text-muted-foreground">
                  Không có chức năng phù hợp
                </p>
              ) : (
                <div className="max-h-64 overflow-y-auto">
                  {slashMatches.map((item, i) => (
                    <button
                      key={item.kind}
                      type="button"
                      onClick={() => pickSlash(item)}
                      onMouseEnter={() => setSlashIndex(i)}
                      className={cn(
                        "flex w-full items-start gap-3 rounded-xl px-3 py-2.5 text-left transition-colors",
                        i === slashIndex && "bg-accent"
                      )}
                    >
                      <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                        <item.icon className="h-4 w-4" />
                      </span>
                      <span className="min-w-0">
                        <span className="block text-sm font-medium">{item.title}</span>
                        <span className="block truncate text-xs text-muted-foreground">
                          {item.desc}
                        </span>
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
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

          {images.length > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              {images.map((src, i) => (
                <div key={i} className="group relative h-20 w-20 overflow-hidden rounded-lg border">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={src}
                    alt={`Đính kèm ${i + 1}`}
                    onClick={() => setPreview(src)}
                    className="h-full w-full cursor-zoom-in object-cover"
                  />
                  <button
                    type="button"
                    onClick={() => removeImage(i)}
                    aria-label="Xóa ảnh"
                    className="absolute right-0.5 top-0.5 flex h-5 w-5 items-center justify-center rounded-full bg-black/60 text-white opacity-0 transition-opacity group-hover:opacity-100"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              ))}
            </div>
          )}

          <textarea
            ref={ref}
            rows={1}
            value={value}
            onChange={(e) => {
              const next = e.target.value;
              setValue(next);
              autoResize();
              if (slashOpen) {
                const bangMatch = /\/([^\/]*)$/.exec(next);
                const bangText = bangMatch ? bangMatch[1] : "";
                if (!bangMatch) {
                  closeSlash();
                } else {
                  setSlashQuery(bangText);
                  setSlashIndex(0);
                }
              }
            }}
            onKeyDown={onKeyDown}
            onPaste={onPaste}
            placeholder={
              activeAction?.placeholder ?? placeholder ?? "Hãy hỏi tôi thông tin về DataHub"
            }
            className="max-h-48 min-h-[34px] w-full resize-none bg-transparent py-0.5 text-base leading-relaxed outline-none placeholder:text-muted-foreground"
            aria-label="Tin nhắn"
          />
        </div>

        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="h-10 w-10 shrink-0 rounded-full"
          onClick={() => fileRef.current?.click()}
          disabled={isStreaming || images.length >= MAX_IMAGES}
          aria-label="Đính kèm ảnh"
          title="Đính kèm ảnh"
        >
          <ImageIcon className="h-5 w-5" />
        </Button>
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          multiple
          className="hidden"
          onChange={onPickFiles}
          aria-hidden="true"
        />

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

      <AnimatePresence>
        {preview && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[100] flex items-center justify-center bg-black/85 p-4"
            onClick={() => setPreview(null)}
          >
            <motion.button
              type="button"
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="absolute right-4 top-4 flex h-10 w-10 items-center justify-center rounded-full bg-white/15 text-white transition-colors hover:bg-white/30"
              aria-label="Đóng"
              onClick={() => setPreview(null)}
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
                src={preview}
                alt="Xem trước ảnh"
                className="max-h-[92vh] max-w-[92vw] rounded-lg object-contain shadow-2xl"
              />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
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
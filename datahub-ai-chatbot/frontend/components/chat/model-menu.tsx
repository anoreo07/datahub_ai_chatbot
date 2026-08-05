"use client";

import Image from "next/image";
import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Check } from "lucide-react";

import { auth } from "@/lib/auth";

export interface ModelOption {
  id: string;
  name: string;
  provider: string;
  logo?: string;
}

interface ModelMenuProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  selectedId: string;
  onSelect: (id: string) => void;
}

export function ModelMenu({ open, onOpenChange, selectedId, onSelect }: ModelMenuProps) {
  const [models, setModels] = useState<ModelOption[]>([]);

  useEffect(() => {
    if (!open || models.length > 0) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/v1/chat/models", {
          headers: { Authorization: `Bearer ${auth.getToken()}` },
        });
        if (!res.ok || cancelled) return;
        const data = await res.json();
        setModels((data.models || []) as ModelOption[]);
      } catch {
        /* ignore */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [open, models.length]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0, y: 8, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 8, scale: 0.96 }}
          transition={{ duration: 0.15 }}
          className="absolute bottom-full left-12 z-30 mb-3 w-64 overflow-hidden rounded-2xl border bg-popover p-1.5 shadow-lg"
          role="menu"
          aria-label="Chọn model"
        >
          <p className="px-3 pb-1.5 pt-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
            Model
          </p>
          {(models.length === 0 ? DEFAULT_MODELS : models).map((m) => {
            const active = m.id === selectedId;
            const logo = m.logo || modelLogo(m);
            return (
              <button
                key={m.id}
                role="menuitem"
                onClick={() => {
                  onSelect(m.id);
                  onOpenChange(false);
                }}
                className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-colors hover:bg-accent focus:outline-none focus-visible:bg-accent"
              >
                <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-primary/10">
                  {logo ? (
                    <Image
                      src={logo}
                      alt={m.name}
                      width={32}
                      height={32}
                      className="h-full w-full object-contain"
                    />
                  ) : (
                    <ModelGlyph />
                  )}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-medium">{m.name}</span>
                  <span className="block truncate text-xs text-muted-foreground">{m.id}</span>
                </span>
                {active && <Check className="h-4 w-4 shrink-0 text-primary" />}
              </button>
            );
          })}
        </motion.div>
      )}
    </AnimatePresence>
  );
}

const DEFAULT_MODELS: ModelOption[] = [
  {
    id: "deepseek-v4-flash",
    name: "DeepSeek V4 Flash",
    provider: "fireworks",
    logo: "/deepseek_logo.jpeg",
  },
  {
    id: "meta/llama-3.3-70b-instruct",
    name: "Llama 3.3 70B (NVIDIA)",
    provider: "nvidia",
    logo: "/meta_logo.jpeg",
  },
];

function modelLogo(m: ModelOption): string {
  const id = m.id.toLowerCase();
  if (id.includes("llama") || id.includes("meta/") || m.provider === "nvidia") {
    return "/meta_logo.jpeg";
  }
  if (id.includes("deepseek") || m.provider === "fireworks") {
    return "/deepseek_logo.jpeg";
  }
  return "";
}

function ModelGlyph() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      className="h-4 w-4 text-primary"
    >
      <rect x="4" y="4" width="16" height="16" rx="4" />
      <path d="M9 2v4M15 2v4M9 18v4M15 18v4" strokeLinecap="round" />
    </svg>
  );
}

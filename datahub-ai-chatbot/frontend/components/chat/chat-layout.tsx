"use client";

import { useEffect, useRef } from "react";
import Image from "next/image";
import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";

import { MessageBubble } from "@/components/chat/message-bubble";
import { ChatInput } from "@/components/chat/chat-input";
import { useChat } from "@/lib/use-chat";

const SUGGESTIONS = [
  "Liệt kê các dataset",
  "What is the lineage of sales_order?",
  "Ai là owner của dataset customer?",
  "Generate SQL từ dataset sales_order",
];

function WelcomeScreen({ onPick }: { onPick: (q: string) => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col items-center justify-center gap-5 px-6 text-center"
    >
      <Image
        src="/logo.png"
        alt="DataAtlas"
        width={96}
        height={96}
        className="h-20 w-20 shrink-0 rounded-2xl object-contain shadow-md"
      />
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Chào bạn, trợ lý DataAtlas</h1>
        <p className="mx-auto mt-2 max-w-md text-[15px] text-muted-foreground">
          Hỏi tôi về datasets, glossary terms, owners, lineage hoặc yêu cầu tạo SQL dựa trên metadata.
        </p>
      </div>
      <div className="grid w-full max-w-md gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => onPick(s)}
            className="flex items-center gap-2 rounded-xl border bg-card px-4 py-3 text-left text-sm transition-colors hover:bg-accent"
          >
            <Sparkles className="h-4 w-4 shrink-0 text-primary" />
            {s}
          </button>
        ))}
      </div>
    </motion.div>
  );
}

export function ChatLayout() {
  const { messages, isStreaming, step, send, applySuggestion } = useChat();
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex h-full flex-col">
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <div className="mx-auto flex min-h-full w-full max-w-3xl flex-col justify-end gap-5 px-4 py-6">
          {messages.length === 0 ? (
            <div className="flex flex-1 items-center justify-center">
              <WelcomeScreen onPick={send} />
            </div>
          ) : (
            messages.map((m) => (
              <MessageBubble key={m.id} message={m} onApplySuggestion={applySuggestion} />
            ))
          )}
          {isStreaming && step && (
            <div className="flex items-center gap-2 pl-1 text-xs text-muted-foreground">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary" />
              {step}
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>
      <ChatInput isStreaming={isStreaming} onSend={send} />
    </div>
  );
}
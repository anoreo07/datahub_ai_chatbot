"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { MessageBubble } from "@/components/chat/message-bubble";
import { ChatInput } from "@/components/chat/chat-input";
import { ContextBar } from "@/components/chat/context-bar";
import { SuggestionChips } from "@/components/chat/suggestion-chips";
import { EvidencePanel } from "@/components/chat/evidence-panel";
import { useChat } from "@/lib/use-chat";
import { cn } from "@/lib/utils";
import type { EntityItem, RecoveryAction, ClarificationCandidate } from "@/lib/types";

function WelcomeScreen({ onPick }: { onPick: (q: string) => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col items-center justify-center gap-5 px-6 text-center"
    >
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Chào bạn, trợ lý V-DataAtlas</h1>
        <p className="mx-auto mt-2 max-w-md text-[15px] text-muted-foreground">
          Hỏi tôi về datasets, glossary terms, owners, lineage hoặc yêu cầu tạo SQL dựa trên metadata.
        </p>
      </div>
      <SuggestionChips onPick={onPick} />
    </motion.div>
  );
}

export function ChatLayout() {
  const { messages, isStreaming, step, activeContext, send, applySuggestion, cancel } = useChat();
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [panelEntity, setPanelEntity] = useState<EntityItem | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleEntityClick = useCallback((entity: EntityItem) => {
    setPanelEntity(entity);
    setPanelOpen(true);
  }, []);

  const handleCitationClick = useCallback((citation: { id: string; url?: string; entity_urn?: string; entity_name?: string; entity_type?: string }) => {
    if (citation.entity_urn) {
      setPanelEntity({
        urn: citation.entity_urn,
        name: citation.entity_name || citation.id,
        url: citation.url,
        entity_type: citation.entity_type,
      });
      setPanelOpen(true);
    } else if (citation.url) {
      window.open(citation.url, "_blank");
    }
  }, []);

  const handleRecoveryAction = useCallback((action: RecoveryAction) => {
    if (action.action === "retry") {
      // Re-send last question
      const lastUserMsg = [...messages].reverse().find((m) => m.role === "user");
      if (lastUserMsg) send(lastUserMsg.content);
    } else if (action.target) {
      send(action.target);
    }
  }, [messages, send]);

  const handleConfirmClarification = useCallback((candidate: ClarificationCandidate) => {
    send(candidate.name);
  }, [send]);

  const handleRejectClarification = useCallback(() => {
    // User wants to search for something else - just focus input
  }, []);

  const handleRemoveContextItem = useCallback(() => {
    // Context removal would need backend support
  }, []);

  return (
    <div className="flex h-full flex-col">
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <div className="flex min-h-full w-full flex-col justify-end px-4 py-6 sm:px-6 md:px-16 lg:px-32 xl:px-64 2xl:px-80">
          {messages.length === 0 ? (
            <div className="flex flex-1 items-center justify-center">
              <WelcomeScreen onPick={send} />
            </div>
          ) : (
            messages.map((m, i) => {
              const prev = i > 0 ? messages[i - 1] : null;
              const sameSender = prev && prev.role === m.role;
              return (
                <div
                  key={m.id}
                  className={cn(
                    sameSender ? "mt-1" : "mt-4"
                  )}
                >
                  <MessageBubble
                    message={m}
                    onApplySuggestion={applySuggestion}
                    onEntityClick={handleEntityClick}
                    onCitationClick={handleCitationClick}
                    onRecoveryAction={handleRecoveryAction}
                    onConfirmClarification={handleConfirmClarification}
                    onRejectClarification={handleRejectClarification}
                  />
                </div>
              );
            })
          )}
          {isStreaming && step && (
            <div className="my-2 inline-flex items-center gap-2 rounded-2xl border border-primary/25 bg-primary/10 px-3.5 py-1.5 text-xs font-semibold text-primary shadow-sm backdrop-blur">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
              </span>
              <span>{step}</span>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Context Bar */}
      <ContextBar context={activeContext} onRemoveItem={handleRemoveContextItem} />

      <ChatInput isStreaming={isStreaming} onSend={send} onCancel={cancel} />

      {/* Evidence Panel */}
      <EvidencePanel
        entity={panelEntity}
        isOpen={panelOpen}
        onClose={() => setPanelOpen(false)}
        onEntityClick={handleEntityClick}
      />
    </div>
  );
}
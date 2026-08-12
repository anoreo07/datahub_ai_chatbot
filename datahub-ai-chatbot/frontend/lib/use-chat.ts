"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { streamChat } from "@/lib/stream";
import { auth } from "@/lib/auth";
import { useApp } from "@/lib/app-store";
import type {
  ChatResponse,
  CitationItem,
  EntityItem,
  LineageData,
  QualityReport,
  Suggestion,
} from "@/lib/types";

export type MessageRole = "user" | "assistant" | "error";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  displayContent?: string;
  images?: string[];
  timestamp: number;
  citations?: CitationItem[];
  entities?: EntityItem[];
  lineage?: LineageData;
  quality_report?: QualityReport;
  suggestion?: Suggestion;
  confidence?: string;
  ambiguous?: boolean;
  intent?: string;
  conversation_id?: string;
  streaming?: boolean;
}

const STEPS: Record<string, string> = {
  classify: "Đang phân tích câu hỏi…",
  thinking: "Đang tư duy & lập kế hoạch…",
  thinking_done: "Đang sinh câu trả lời…",
  retrieve: "Đang tìm kiếm metadata…",
  rerank: "Đang sắp xếp kết quả…",
  generate: "Đang sinh câu trả lời…",
};

function uid() {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

export function useChat() {
  const { chatReset, activeConversationId } = useApp();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [step, setStep] = useState("");
  const conversationIdRef = useRef<string | null>(null);
  const lastQuestionRef = useRef<string>("");
  const streamingRef = useRef(false);

  // Reset on "New Chat"
  useEffect(() => {
    if (chatReset === 0) return;
    setMessages([]);
    setIsStreaming(false);
    setStep("");
    conversationIdRef.current = null;
    streamingRef.current = false;
  }, [chatReset]);

  // Load conversation turns when a saved conversation is selected
  useEffect(() => {
    if (!activeConversationId) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`/api/v1/conversations/${activeConversationId}`, {
          headers: { Authorization: `Bearer ${auth.getToken()}` },
        });
        if (!res.ok || cancelled) return;
        const data = await res.json();
        const turns: { question: string; answer: string }[] = data.turns || [];
        const loaded: ChatMessage[] = [];
        for (const t of turns) {
          loaded.push({
            id: uid(),
            role: "user",
            content: t.question,
            timestamp: Date.now(),
          });
          loaded.push({
            id: uid(),
            role: "assistant",
            content: t.answer,
            timestamp: Date.now(),
          });
        }
        conversationIdRef.current = activeConversationId;
        setMessages(loaded);
      } catch {
        /* ignore */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [activeConversationId]);

  const send = useCallback(
    async (
      question: string,
      suggestedName?: string,
      model?: string,
      displayContent?: string,
      selectedAction?: string,
      images?: string[]
    ) => {
      const q = question.trim();
      if (!q || streamingRef.current) return;
      lastQuestionRef.current = q;

      const userMsg: ChatMessage = {
        id: uid(),
        role: "user",
        content: q,
        displayContent: displayContent || q,
        images: images && images.length ? images : undefined,
        timestamp: Date.now(),
      };
      const botId = uid();
      const botMsg: ChatMessage = {
        id: botId,
        role: "assistant",
        content: "",
        timestamp: Date.now(),
        streaming: true,
      };
      setMessages((prev) => [...prev, userMsg, botMsg]);
      setIsStreaming(true);
      setStep("classify");
      streamingRef.current = true;

      await streamChat(
        {
          question: q,
          conversation_id: conversationIdRef.current || undefined,
          suggested_name: suggestedName,
          model,
          selected_action: selectedAction,
          images: images && images.length ? images : undefined,
        },
        {
          onStatus: (s) => setStep(STEPS[s] || s),
          onToken: (text) => {
            setMessages((prev) =>
              prev.map((m) => (m.id === botId ? { ...m, content: m.content + text } : m))
            );
          },
          onDone: (data: ChatResponse) => {
            conversationIdRef.current = data.conversation_id || conversationIdRef.current;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === botId
                  ? {
                      ...m,
                      streaming: false,
                      content: m.content || data.answer,
                      citations: data.citations,
                      entities: data.entities,
                      lineage: data.lineage,
                      quality_report: data.quality_report,
                      suggestion: data.suggestion,
                      confidence: data.confidence,
                      ambiguous: data.ambiguous,
                      intent: data.intent,
                      conversation_id: data.conversation_id,
                    }
                  : m
              )
            );
            setIsStreaming(false);
            setStep("");
            streamingRef.current = false;
          },
          onError: (message: string) => {
            setMessages((prev) =>
              prev.map((m) => (m.id === botId ? { ...m, streaming: false, content: `⚠️ ${message}` } : m))
            );
            setIsStreaming(false);
            setStep("");
            streamingRef.current = false;
          },
        }
      );
    },
    []
  );

  const applySuggestion = useCallback(
    (suggested: string) => {
      const q = lastQuestionRef.current;
      if (!q || streamingRef.current) return;
      const botId = uid();
      const botMsg: ChatMessage = {
        id: botId,
        role: "assistant",
        content: "",
        timestamp: Date.now(),
        streaming: true,
      };
      // Do NOT re-add a user bubble — answer directly with the corrected term.
      setMessages((prev) => [...prev, botMsg]);
      setIsStreaming(true);
      setStep("classify");
      streamingRef.current = true;

      void streamChat(
        {
          question: q,
          conversation_id: conversationIdRef.current || undefined,
          suggested_name: suggested,
        },
        {
          onStatus: (s) => setStep(STEPS[s] || s),
          onToken: (text) => {
            setMessages((prev) =>
              prev.map((m) => (m.id === botId ? { ...m, content: m.content + text } : m))
            );
          },
          onDone: (data: ChatResponse) => {
            conversationIdRef.current = data.conversation_id || conversationIdRef.current;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === botId
                  ? {
                      ...m,
                      streaming: false,
                      content: m.content || data.answer,
                      citations: data.citations,
                      entities: data.entities,
                      lineage: data.lineage,
                      quality_report: data.quality_report,
                      suggestion: data.suggestion,
                      confidence: data.confidence,
                      ambiguous: data.ambiguous,
                      intent: data.intent,
                      conversation_id: data.conversation_id,
                    }
                  : m
              )
            );
            setIsStreaming(false);
            setStep("");
            streamingRef.current = false;
          },
          onError: (message: string) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === botId ? { ...m, streaming: false, content: `⚠️ ${message}` } : m
              )
            );
            setIsStreaming(false);
            setStep("");
            streamingRef.current = false;
          },
        }
      );
    },
    []
  );

  return { messages, isStreaming, step, send, applySuggestion };
}
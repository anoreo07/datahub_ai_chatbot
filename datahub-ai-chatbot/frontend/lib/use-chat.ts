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
  ErrorInfo,
  ClarificationCandidate,
  ActiveContext,
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
  insufficient_context?: boolean;
  intent?: string;
  conversation_id?: string;
  streaming?: boolean;
  error_info?: ErrorInfo;
  clarification_candidates?: ClarificationCandidate[];
  active_context?: ActiveContext;
  trace_id?: string;
  selected_action?: string;
  response_time_ms?: number;
}


const STEPS: Record<string, string> = {
  thinking: "🧠 Đang ở chế độ Thinking: Phân tích đa chiều & Lập kế hoạch…",
  thinking_done: "🧠 Đã lập kế hoạch xong, đang tổng hợp dữ liệu…",
  retrieve: "Đang tìm kiếm metadata…",
  rerank: "Đang sắp xếp kết quả…",
  generate: "Đang sinh câu trả lời…",
};

function uid() {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

/** Patterns that indicate a raw technical error that should be hidden from the user. */
const TECHNICAL_ERROR_PATTERNS = [
  /\[Errno\s*\d+\]/i,
  /Permission\s+denied/i,
  /Traceback\s*\(most/i,
  /File\s+".*"/i,
  /^\s*at\s+/i,
  /Stack\s+Trace/i,
  /Internal\s+Server\s+Error/i,
  /500\s+Error/i,
  /ENOTFOUND/i,
  /ECONNREFUSED/i,
  /ECONNRESET/i,
  /ETIMEDOUT/i,
  /ENOENT/i,
  /EACCES/i,
  /epipe/i,
  /socket\s+hang\s+up/i,
  /read\s+ECONNRESET/i,
  /connect\s+ECONNREFUSED/i,
  /\/app\//i,
  /\/usr\/local\//i,
  /\/home\//i,
  /\.py:\d+/,
  /raise\s+\w+Error/,
  /ImportError/i,
  /ModuleNotFoundError/i,
  /SyntaxError/i,
  /TypeError/i,
  /ValueError/i,
  /KeyError/i,
  /IndexError/i,
  /RuntimeError/i,
];

/** Sanitize an error message for user-facing display. Returns a friendly message
 *  if the original contains technical details; otherwise returns the original. */
export function sanitizeErrorMessage(raw: string): string {
  if (!raw) return "Đã có lỗi xảy ra. Vui lòng thử lại sau.";
  const isTechnical = TECHNICAL_ERROR_PATTERNS.some((p) => p.test(raw));
  if (isTechnical) {
    console.error("[sanitizeErrorMessage] Hidden technical error:", raw);
    return "Đã có lỗi xảy ra khi xử lý yêu cầu này. Vui lòng thử lại sau.";
  }
  return raw;
}

export function useChat() {
  const { chatReset, activeConversationId } = useApp();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [step, setStep] = useState("");
  const [activeContext, setActiveContext] = useState<ActiveContext>({ items: [] });
  const conversationIdRef = useRef<string | null>(null);
  const lastQuestionRef = useRef<string>("");
  const streamingRef = useRef(false);
  const abortRef = useRef<AbortController | null>(null);

  // Reset on "New Chat"
  useEffect(() => {
    if (chatReset === 0) return;
    setMessages([]);
    setIsStreaming(false);
    setStep("");
    setActiveContext({ items: [] });
    conversationIdRef.current = null;
    streamingRef.current = false;
    abortRef.current?.abort();
    abortRef.current = null;
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
        const turns: { question: string; answer: string; render_state?: Record<string, unknown> }[] = data.turns || [];
        const loaded: ChatMessage[] = [];
        for (const t of turns) {
          const rs = t.render_state || {};
          loaded.push({
            id: uid(),
            role: "user",
            content: t.question,
            displayContent: t.question,
            timestamp: Date.now(),
          });
          loaded.push({
            id: uid(),
            role: "assistant",
            content: t.answer,
            timestamp: Date.now(),
            citations: (rs.citations as ChatMessage["citations"]) || undefined,
            entities: (rs.entities as ChatMessage["entities"]) || undefined,
            lineage: (rs.lineage as ChatMessage["lineage"]) || undefined,
            quality_report: (rs.quality_report as ChatMessage["quality_report"]) || undefined,
            suggestion: (rs.suggestion as ChatMessage["suggestion"]) || undefined,
            confidence: (rs.confidence as string) || undefined,
            ambiguous: (rs.ambiguous as boolean) || undefined,
            insufficient_context: (rs.insufficient_context as boolean) || undefined,
            intent: (rs.intent as string) || undefined,
            trace_id: (rs.trace_id as string) || undefined,
            selected_action: (rs.selected_action as string) || undefined,
            error_info: (rs.error_info as ChatMessage["error_info"]) || undefined,
            clarification_candidates: (rs.clarification_candidates as ChatMessage["clarification_candidates"]) || undefined,
            active_context: (rs.active_context as ChatMessage["active_context"]) || undefined,
            response_time_ms: typeof rs.response_time_ms === "number" ? rs.response_time_ms : undefined,
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

      const controller = new AbortController();
      abortRef.current = controller;

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
      setStep("");
      streamingRef.current = true;

      try {
        await streamChat(
          {
            question: q,
            conversation_id: conversationIdRef.current || undefined,
            suggested_name: suggestedName,
            model,
            selected_action: selectedAction,
            images: images && images.length ? images : undefined,
            ragas_enabled: typeof window !== "undefined"
              ? localStorage.getItem("ragas_enabled") !== "false"
              : true,
          },
          {
            onStatus: (s) => setStep(STEPS[s] || ""),
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
                        error_info: data.error_info,
                        clarification_candidates: data.clarification_candidates,
                        active_context: data.active_context,
                        trace_id: data.trace_id,
                        selected_action: data.selected_action,
                        response_time_ms: data.response_time_ms ?? undefined,
                      }

                    : m
                )
              );
              if (data.active_context) {
                setActiveContext(data.active_context);
              }
            },
            onError: (message: string) => {
              const friendly = sanitizeErrorMessage(message);
              setMessages((prev) =>
                prev.map((m) => (m.id === botId ? { ...m, streaming: false, role: "error" as MessageRole, content: friendly } : m))
              );
            },
          },
          controller.signal,
        );

        if (controller.signal.aborted) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === botId
                ? {
                    ...m,
                    streaming: false,
                    content: m.content
                      ? `${m.content}\n\n_Người dùng đã dừng phản hồi từ chatbot._`
                      : "Người dùng đã dừng phản hồi từ chatbot.",
                  }
                : m
            )
          );
          return;
        }
      } catch (err) {
        if (controller.signal.aborted || (err instanceof Error && err.name === "AbortError")) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === botId
                ? {
                    ...m,
                    streaming: false,
                    content: m.content
                      ? `${m.content}\n\n_Người dùng đã dừng phản hồi từ chatbot._`
                      : "Người dùng đã dừng phản hồi từ chatbot.",
                  }
                : m
            )
          );
          return;
        }
        setMessages((prev) =>
          prev.map((m) =>
            m.id === botId
              ? { ...m, streaming: false, role: "error" as MessageRole, content: "Đã xảy ra lỗi khi tải câu trả lời. Vui lòng thử lại sau." }
              : m
          )
        );
      } finally {
        abortRef.current = null;
        setIsStreaming(false);
        setStep("");
        streamingRef.current = false;
      }
    },
    []
  );

  const applySuggestion = useCallback(
    async (
      suggested: string,
    ) => {
      const q = lastQuestionRef.current;
      if (!q || streamingRef.current) return;

      const controller = new AbortController();
      abortRef.current = controller;

      const botId = uid();
      const botMsg: ChatMessage = {
        id: botId,
        role: "assistant",
        content: "",
        timestamp: Date.now(),
        streaming: true,
      };
      setMessages((prev) => [...prev, botMsg]);
      setIsStreaming(true);
      setStep("");
      streamingRef.current = true;

      try {
        await streamChat(
          {
            question: q,
            conversation_id: conversationIdRef.current || undefined,
            suggested_name: suggested,
            ragas_enabled: typeof window !== "undefined"
              ? localStorage.getItem("ragas_enabled") !== "false"
              : true,
          },
          {
            onStatus: (s) => setStep(STEPS[s] || ""),
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
                        error_info: data.error_info,
                        clarification_candidates: data.clarification_candidates,
                        active_context: data.active_context,
                        trace_id: data.trace_id,
                        response_time_ms: data.response_time_ms ?? undefined,
                      }

                    : m
                )
              );
            },
            onError: (message: string) => {
              const friendly = sanitizeErrorMessage(message);
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === botId ? { ...m, streaming: false, role: "error" as MessageRole, content: friendly } : m
                )
              );
            },
          },
          controller.signal,
        );

        if (controller.signal.aborted) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === botId
                ? {
                    ...m,
                    streaming: false,
                    content: m.content
                      ? `${m.content}\n\n_Người dùng đã dừng phản hồi từ chatbot._`
                      : "Người dùng đã dừng phản hồi từ chatbot.",
                  }
                : m
            )
          );
          return;
        }
      } catch (err) {
        if (controller.signal.aborted || (err instanceof Error && err.name === "AbortError")) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === botId
                ? {
                    ...m,
                    streaming: false,
                    content: m.content
                      ? `${m.content}\n\n_Người dùng đã dừng phản hồi từ chatbot._`
                      : "Người dùng đã dừng phản hồi từ chatbot.",
                  }
                : m
            )
          );
          return;
        }
        setMessages((prev) =>
          prev.map((m) =>
            m.id === botId
              ? { ...m, streaming: false, role: "error" as MessageRole, content: "Đã xảy ra lỗi khi tải câu trả lời. Vui lòng thử lại sau." }
              : m
          )
        );
      } finally {
        abortRef.current = null;
        setIsStreaming(false);
        setStep("");
        streamingRef.current = false;
      }
    },
    []
  );

  const cancel = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setIsStreaming(false);
    setStep("");
    streamingRef.current = false;
    setMessages((prev) =>
      prev.map((m) =>
        m.streaming
          ? {
              ...m,
              streaming: false,
              content: m.content
                ? `${m.content}\n\n_Người dùng đã dừng phản hồi từ chatbot._`
                : "Người dùng đã dừng phản hồi từ chatbot.",
            }
          : m
      )
    );
  }, []);

  return { messages, isStreaming, step, activeContext, setActiveContext, send, applySuggestion, cancel };
}
import { auth } from "./auth";
import type { ChatResponse, StreamEvent } from "./types";

export interface StreamCallbacks {
  onStatus?: (step: string) => void;
  onToken?: (text: string) => void;
  onDone?: (data: ChatResponse) => void;
  onError?: (message: string) => void;
}

export interface ChatPayload {
  question: string;
  conversation_id?: string;
  suggested_name?: string;
  model?: string;
  selected_action?: string;
  images?: string[];
}

function parseBlock(block: string): StreamEvent | null {
  let event = "message";
  let data: string | null = null;
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data = line.slice(5).trim();
  }
  if (data === null) return null;
  try {
    return { event: event as StreamEvent["event"], data: JSON.parse(data) };
  } catch {
    return { event: event as StreamEvent["event"], data: null };
  }
}

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null;
}

/** Stream a chat response from the SSE endpoint. */
export async function streamChat(
  body: ChatPayload,
  callbacks: StreamCallbacks
): Promise<void> {
  const token = auth.getToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetch("/api/v1/chat/stream", {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });
  } catch (e) {
    callbacks.onError?.((e as Error).message || "Network error");
    return;
  }

  if (res.status === 401) {
    auth.clear();
    callbacks.onError?.("Authentication required");
    if (typeof window !== "undefined") {
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.href = "/login";
    }
    return;
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail || detail;
    } catch {
      /* ignore */
    }
    callbacks.onError?.(detail);
    return;
  }
  if (!res.body) {
    callbacks.onError?.("Response body unavailable");
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let idx: number;
      while ((idx = buffer.indexOf("\n\n")) !== -1) {
        const block = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        const ev = parseBlock(block);
        if (!ev) continue;
        if (ev.event === "status" && isRecord(ev.data) && typeof ev.data.step === "string")
          callbacks.onStatus?.(ev.data.step);
        else if (ev.event === "token" && isRecord(ev.data) && typeof ev.data.text === "string")
          callbacks.onToken?.(ev.data.text);
        else if (ev.event === "done" && isRecord(ev.data))
          callbacks.onDone?.(ev.data as unknown as ChatResponse);
        else if (ev.event === "error")
          callbacks.onError?.(
            isRecord(ev.data) && typeof ev.data.detail === "string" ? ev.data.detail : "Streaming error"
          );
      }
    }
  } finally {
    reader.releaseLock();
  }
}
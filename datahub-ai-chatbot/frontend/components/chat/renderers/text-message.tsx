"use client";

import { Markdown } from "@/components/chat/markdown";
import type { ChatMessage } from "@/lib/use-chat";

interface TextMessageProps {
  message: ChatMessage;
}

export function TextMessage({ message }: TextMessageProps) {
  return <Markdown content={message.content} />;
}

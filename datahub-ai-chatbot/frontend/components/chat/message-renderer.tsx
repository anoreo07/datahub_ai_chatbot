"use client";

import type { ChatMessage } from "@/lib/use-chat";
import type { EntityItem, RecoveryAction } from "@/lib/types";
import { TextMessage } from "./renderers/text-message";
import { EntityCard } from "./renderers/entity-card";
import { ClarificationCard } from "./renderers/clarification-card";
import { ErrorCard } from "./renderers/error-card";

interface MessageRendererProps {
  message: ChatMessage;
  onApplySuggestion?: (suggested: string) => void;
  onEntityClick?: (entity: EntityItem) => void;
  onRecoveryAction?: (action: RecoveryAction) => void;
  onConfirmClarification?: (candidate: { name: string; urn: string; entity_type?: string }) => void;
  onRejectClarification?: () => void;
}

export function MessageRenderer({
  message,
  onApplySuggestion,
  onEntityClick,
  onRecoveryAction,
  onConfirmClarification,
  onRejectClarification,
}: MessageRendererProps) {
  const isError = message.role === "error";
  const hasErrorInfo = message.error_info && message.error_info.code !== "UNKNOWN";
  const hasClarification = message.clarification_candidates && message.clarification_candidates.length > 0;

  return (
    <div className="space-y-2">
      {/* Main text content */}
      <TextMessage message={message} />

      {/* Error with recovery actions */}
      {hasErrorInfo && message.error_info && (
        <ErrorCard error={message.error_info} onRecoveryAction={onRecoveryAction} />
      )}

      {/* Clarification candidates */}
      {hasClarification && message.clarification_candidates && onConfirmClarification && onRejectClarification && (
        <ClarificationCard
          candidates={message.clarification_candidates}
          onConfirm={onConfirmClarification}
          onReject={onRejectClarification}
        />
      )}

      {/* Entity cards */}
      {message.entities && message.entities.length > 0 && (
        <div className="space-y-1.5">
          {message.entities.slice(0, 3).map((entity, i) => (
            <EntityCard key={entity.urn || i} entity={entity} onOpenPanel={onEntityClick} />
          ))}
        </div>
      )}
    </div>
  );
}

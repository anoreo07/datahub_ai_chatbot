"use client";

import { Check, X, HelpCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ClarificationCandidate } from "@/lib/types";

interface ClarificationCardProps {
  candidates: ClarificationCandidate[];
  onConfirm: (candidate: ClarificationCandidate) => void;
  onReject: () => void;
}

export function ClarificationCard({ candidates, onConfirm, onReject }: ClarificationCardProps) {
  if (!candidates || candidates.length === 0) return null;

  return (
    <div className="mt-3 rounded-xl border border-primary/30 bg-primary/5 p-4">
      <div className="flex items-center gap-2 mb-3">
        <HelpCircle className="h-4 w-4 text-primary" />
        <p className="text-sm font-medium text-primary">Bạn muốn nói về:</p>
      </div>
      <div className="space-y-2">
        {candidates.map((candidate, i) => (
          <div
            key={candidate.urn || i}
            className="flex items-center justify-between gap-2 rounded-lg border bg-card p-3 transition-colors hover:border-primary/50"
          >
            <div className="min-w-0">
              <p className="text-sm font-medium truncate">{candidate.name}</p>
              <div className="flex items-center gap-2 mt-0.5">
                {candidate.entity_type && (
                  <span className="text-[10px] text-muted-foreground">{candidate.entity_type}</span>
                )}
                {candidate.confidence !== undefined && (
                  <span className="text-[10px] text-muted-foreground">
                    · {Math.round(candidate.confidence * 100)}% match
                  </span>
                )}
              </div>
              {candidate.description && (
                <p className="text-xs text-muted-foreground mt-1 line-clamp-1">{candidate.description}</p>
              )}
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => onConfirm(candidate)}
              className="shrink-0"
            >
              <Check className="h-3.5 w-3.5 mr-1" />
              Chọn
            </Button>
          </div>
        ))}
      </div>
      <div className="mt-3 flex gap-2">
        <Button size="sm" variant="ghost" onClick={onReject}>
          <X className="h-3.5 w-3.5 mr-1" />
          Không, tìm cái khác
        </Button>
      </div>
    </div>
  );
}

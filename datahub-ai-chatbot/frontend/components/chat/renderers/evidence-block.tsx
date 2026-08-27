"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, ExternalLink } from "lucide-react";
import type { CitationItem } from "@/lib/types";

interface EvidenceBlockProps {
  citations: CitationItem[];
  onCitationClick?: (citation: CitationItem) => void;
}

const MAX_VISIBLE = 3;

export function EvidenceBlock({ citations, onCitationClick }: EvidenceBlockProps) {
  const [expanded, setExpanded] = useState(false);
  if (!citations || citations.length === 0) return null;

  const hasMore = citations.length > MAX_VISIBLE;
  const visible = expanded ? citations : citations.slice(0, MAX_VISIBLE);
  const hiddenCount = citations.length - visible.length;

  return (
    <div className="mt-2 space-y-1.5">
      <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
        Nguồn tham khảo ({citations.length})
      </p>
      <div className="flex flex-wrap gap-1.5">
        {visible.map((c, i) => (
          <button
            key={`${c.id}-${i}`}
            type="button"
            onClick={() => onCitationClick?.(c)}
            className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary transition-colors hover:bg-primary/20"
          >
            {c.id}
            {c.entity_name && (
              <span className="max-w-[120px] truncate text-muted-foreground">({c.entity_name})</span>
            )}
            <ExternalLink className="h-3 w-3 shrink-0" />
          </button>
        ))}
        {hasMore && (
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="inline-flex items-center gap-1 rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted/70"
          >
            {expanded ? (
              <>Thu gọn <ChevronUp className="h-3 w-3" /></>
            ) : (
              <>+{hiddenCount} khác <ChevronDown className="h-3 w-3" /></>
            )}
          </button>
        )}
      </div>
    </div>
  );
}

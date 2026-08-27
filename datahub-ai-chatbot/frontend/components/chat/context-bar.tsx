"use client";

import { X, Database, Globe, BookOpen, BarChart3, FileText } from "lucide-react";
import type { ActiveContext, ActiveContextItem } from "@/lib/types";

interface ContextBarProps {
  context: ActiveContext;
  onRemoveItem?: (item: ActiveContextItem) => void;
}

const TYPE_ICONS: Record<string, React.ReactNode> = {
  dataset: <Database className="h-3 w-3" />,
  domain: <Globe className="h-3 w-3" />,
  field: <Database className="h-3 w-3" />,
  term: <BookOpen className="h-3 w-3" />,
  report: <BarChart3 className="h-3 w-3" />,
  dashboard: <BarChart3 className="h-3 w-3" />,
  entity: <FileText className="h-3 w-3" />,
};

export function ContextBar({ context, onRemoveItem }: ContextBarProps) {
  if (!context.items || context.items.length === 0) return null;

  return (
    <div className="flex items-center gap-2 px-4 py-2 text-xs sm:px-6 md:px-16 lg:px-32 xl:px-64 2xl:px-80">
      <span className="text-muted-foreground font-medium">Context:</span>
      <div className="flex flex-wrap items-center gap-1.5">
        {context.items.map((item, i) => (
          <span
            key={`${item.urn || item.name}-${i}`}
            className="inline-flex items-center gap-1 rounded-full border bg-card px-2.5 py-0.5 text-muted-foreground"
          >
            {TYPE_ICONS[item.type] || <Database className="h-3 w-3" />}
            <span className="font-medium">{item.type}:</span>
            <span className="max-w-[150px] truncate">{item.name}</span>
            {onRemoveItem && (
              <button
                type="button"
                onClick={() => onRemoveItem(item)}
                className="ml-0.5 flex h-3.5 w-3.5 items-center justify-center rounded-full text-muted-foreground/60 transition-colors hover:bg-muted hover:text-foreground"
                aria-label={`Xóa ${item.name}`}
              >
                <X className="h-2.5 w-2.5" />
              </button>
            )}
          </span>
        ))}
      </div>
    </div>
  );
}

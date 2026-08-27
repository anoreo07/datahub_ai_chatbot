"use client";

import { Sparkles, Database, BookOpen, GitBranch, Search } from "lucide-react";

interface SuggestionChipsProps {
  onPick: (suggestion: string) => void;
  contextType?: string;
  contextName?: string;
}

interface SuggestionGroup {
  label: string;
  icon: React.ReactNode;
  suggestions: string[];
}

const GENERIC_SUGGESTIONS: SuggestionGroup[] = [
  {
    label: "Tìm kiếm",
    icon: <Search className="h-3.5 w-3.5" />,
    suggestions: [
      "Liệt kê các dataset",
      "Tìm dataset liên quan đến inventory",
      "Ai là owner của dataset customer?",
    ],
  },
  {
    label: "Hiểu dữ liệu",
    icon: <BookOpen className="h-3.5 w-3.5" />,
    suggestions: [
      "Demand trong domain SẢN XUẤT nghĩa là gì?",
      "Schema của dataset sales_order",
    ],
  },
  {
    label: "Truy vết",
    icon: <GitBranch className="h-3.5 w-3.5" />,
    suggestions: [
      "Dataset này lấy dữ liệu từ đâu?",
      "Report này có lineage như thế nào?",
    ],
  },
];

const CONTEXT_SUGGESTIONS: Record<string, SuggestionGroup[]> = {
  dataset: [
    {
      label: "Khám phá",
      icon: <Database className="h-3.5 w-3.5" />,
      suggestions: [
        "Xem schema",
        "Xem owner",
        "Xem lineage",
        "Xem glossary terms liên quan",
        "Tạo SQL từ dataset này",
      ],
    },
  ],
  domain: [
    {
      label: "Khám phá",
      icon: <Database className="h-3.5 w-3.5" />,
      suggestions: [
        "Liệt kê datasets trong domain này",
        "Domain này có bao nhiêu dataset?",
      ],
    },
  ],
};

export function SuggestionChips({ onPick, contextType }: SuggestionChipsProps) {
  const groups = contextType && CONTEXT_SUGGESTIONS[contextType]
    ? CONTEXT_SUGGESTIONS[contextType]
    : GENERIC_SUGGESTIONS;

  // Render a clean grid of cards for the chat welcome page
  if (!contextType) {
    return (
      <div className="mx-auto w-full max-w-3xl mt-4">
        <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
          {groups
            .flatMap((group) =>
              group.suggestions.map((s) => ({
                text: s,
                icon: group.icon,
                groupLabel: group.label,
              }))
            )
            .slice(0, 6)
            .map((item, i) => (
              <button
                key={i}
                type="button"
                onClick={() => onPick(item.text)}
                className="group flex flex-col items-start text-left gap-2 rounded-xl border bg-card p-4 transition-all duration-200 hover:border-primary/40 hover:bg-primary/5 hover:shadow-sm cursor-pointer border-border/80"
              >
                <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10 text-primary group-hover:bg-primary/20 transition-colors shrink-0">
                  {item.icon}
                </span>
                <div className="min-w-0">
                  <span className="block text-[10px] uppercase font-bold tracking-wider text-muted-foreground mb-1">
                    {item.groupLabel}
                  </span>
                  <span className="block text-xs font-semibold text-foreground/80 group-hover:text-foreground line-clamp-2 leading-relaxed">
                    {item.text}
                  </span>
                </div>
              </button>
            ))}
        </div>
      </div>
    );
  }

  // Render compact inline pills for in-chat/context specific suggestions
  return (
    <div className="space-y-3 w-full text-left">
      {groups.map((group) => (
        <div key={group.label} className="w-full">
          <p className="mb-2 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            {group.icon}
            {group.label}
          </p>
          <div className="flex flex-wrap gap-2">
            {group.suggestions.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => onPick(s)}
                className="inline-flex items-center gap-1.5 rounded-full border bg-card px-3 py-1.5 text-xs text-muted-foreground transition-all hover:border-primary/40 hover:bg-primary/5 hover:text-primary hover:shadow-sm font-medium"
              >
                <Sparkles className="h-3 w-3 text-primary shrink-0" />
                <span>{s}</span>
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

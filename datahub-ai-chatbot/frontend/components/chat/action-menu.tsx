"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
  FileUp,
  Search,
  TerminalSquare,
  Activity,
  GitBranch,
  ShieldCheck,
  FileText,
  type LucideIcon,
} from "lucide-react";

export type ActionKind =
  | "upload"
  | "search"
  | "sql"
  | "impact"
  | "lineage"
  | "quality"
  | "report";

export interface ActionDef {
  kind: ActionKind;
  title: string;
  desc: string;
  icon: LucideIcon;
  prompt: string;
  placeholder: string;
}

const ITEMS: ActionDef[] = [
  {
    kind: "upload",
    title: "Upload Document",
    desc: "So sánh schema file với DataHub",
    icon: FileUp,
    prompt: "Upload tài liệu để so sánh schema với DataHub ",
    placeholder: "Chọn file hoặc gõ mô tả dataset cần so sánh…",
  },
  {
    kind: "search",
    title: "Search Dataset",
    desc: "Tìm dataset theo tên, cột, owner, tag",
    icon: Search,
    prompt: "Tìm dataset ",
    placeholder: "vd: sales_order, customer, revenue…",
  },
  {
    kind: "sql",
    title: "Generate SQL",
    desc: "Generate SQL based on retrieved metadata only",
    icon: TerminalSquare,
    prompt: "Generate SQL cho dataset ",
    placeholder: "vd: sales_order",
  },
  {
    kind: "impact",
    title: "Impact Analysis",
    desc: "Đánh giá ảnh hưởng hạ nguồn",
    icon: Activity,
    prompt: "Impact analysis cho dataset ",
    placeholder: "vd: sales_order",
  },
  {
    kind: "lineage",
    title: "Data Lineage",
    desc: "Xem lineage dạng đồ thị tương tác",
    icon: GitBranch,
    prompt: "Data lineage của dataset ",
    placeholder: "vd: dim_warehouse hoặc vẽ cho tôi dim_warehouse",
  },
  {
    kind: "quality",
    title: "Data Quality Check",
    desc: "Đánh giá độ hoàn thiện metadata",
    icon: ShieldCheck,
    prompt: "Data quality check cho dataset ",
    placeholder: "vd: sales_order",
  },
  {
    kind: "report",
    title: "Metadata Report",
    desc: "Báo cáo AI metadata chuyên nghiệp",
    icon: FileText,
    prompt: "Metadata report cho dataset ",
    placeholder: "vd: sales_order",
  },
];

export const ACTION_DEFS = ITEMS;

interface ActionMenuProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onPick: (action: ActionDef) => void;
}

export function ActionMenu({ open, onOpenChange, onPick }: ActionMenuProps) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0, y: 8, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 8, scale: 0.96 }}
          transition={{ duration: 0.15 }}
          className="absolute bottom-full left-0 z-30 mb-3 w-80 overflow-hidden rounded-2xl border bg-popover p-1.5 shadow-lg"
          role="menu"
          aria-label="Menu hành động"
        >
          <p className="px-3 pb-1.5 pt-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
            Actions
          </p>
          {ITEMS.map((item) => (
            <button
              key={item.kind}
              role="menuitem"
              onClick={() => {
                onPick(item);
                onOpenChange(false);
              }}
              className="flex w-full items-start gap-3 rounded-xl px-3 py-2.5 text-left transition-colors hover:bg-accent focus:outline-none focus-visible:bg-accent"
            >
              <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <item.icon className="h-4 w-4" />
              </span>
              <span className="min-w-0">
                <span className="block text-sm font-medium">{item.title}</span>
                <span className="block truncate text-xs text-muted-foreground">{item.desc}</span>
              </span>
            </button>
          ))}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
"use client";

import { motion } from "framer-motion";
import { Brain, Check, Loader2 } from "lucide-react";

interface ThinkingIndicatorProps {
  step: string;
  isComplete?: boolean;
}

const STEP_ICONS: Record<string, React.ReactNode> = {
  classify: <Brain className="h-3.5 w-3.5" />,
  thinking: <Brain className="h-3.5 w-3.5" />,
  retrieve: <Loader2 className="h-3.5 w-3.5 animate-spin" />,
  rerank: <Loader2 className="h-3.5 w-3.5 animate-spin" />,
  generate: <Loader2 className="h-3.5 w-3.5 animate-spin" />,
};

export function ThinkingIndicator({ step, isComplete }: ThinkingIndicatorProps) {
  if (!step && !isComplete) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 4 }}
      className="flex items-center gap-2 pl-1 text-xs text-muted-foreground"
    >
      {isComplete ? (
        <Check className="h-3.5 w-3.5 text-emerald-500" />
      ) : (
        STEP_ICONS[classifyStepKey(step)] || <Loader2 className="h-3.5 w-3.5 animate-spin" />
      )}
      <span>{step}</span>
    </motion.div>
  );
}

function classifyStepKey(step: string): string {
  const lower = step.toLowerCase();
  if (lower.includes("phân tích") || lower.includes("classify")) return "classify";
  if (lower.includes("tư duy") || lower.includes("thinking") || lower.includes("kế hoạch")) return "thinking";
  if (lower.includes("tìm kiếm") || lower.includes("retrieve") || lower.includes("search")) return "retrieve";
  if (lower.includes("sắp xếp") || lower.includes("rerank")) return "rerank";
  if (lower.includes("sinh") || lower.includes("generate") || lower.includes("trả lời")) return "generate";
  return "thinking";
}

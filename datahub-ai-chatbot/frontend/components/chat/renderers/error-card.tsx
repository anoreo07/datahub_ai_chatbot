"use client";

import { AlertTriangle, Search, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ErrorInfo, RecoveryAction } from "@/lib/types";

interface ErrorCardProps {
  error: ErrorInfo;
  onRecoveryAction?: (action: RecoveryAction) => void;
}

const ERROR_LABELS: Record<string, string> = {
  NOT_FOUND: "Không tìm thấy",
  AMBIGUOUS: "Nhiều kết quả",
  OUT_OF_SCOPE: "Ngoài phạm vi",
  INSUFFICIENT_METADATA: "Thiếu thông tin",
  PERMISSION_DENIED: "Không có quyền",
  INTERNAL_ERROR: "Lỗi hệ thống",
  VALIDATION_ERROR: "Dữ liệu không hợp lệ",
  UNKNOWN: "Lỗi không xác định",
};

const RECOVERY_ICONS: Record<string, React.ReactNode> = {
  search_entity: <Search className="h-3.5 w-3.5" />,
  search_dataset: <Search className="h-3.5 w-3.5" />,
  search_glossary: <Search className="h-3.5 w-3.5" />,
  search_report: <Search className="h-3.5 w-3.5" />,
  retry: <RefreshCw className="h-3.5 w-3.5" />,
  open_entity: <RefreshCw className="h-3.5 w-3.5" />,
};

export function ErrorCard({ error, onRecoveryAction }: ErrorCardProps) {
  const label = ERROR_LABELS[error.code] || ERROR_LABELS.UNKNOWN;

  return (
    <div className="mt-2 rounded-xl border border-border/60 bg-destructive/5 p-4">
      <div className="flex items-start gap-2">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-destructive">{label}</p>
          <p className="mt-1 text-sm text-muted-foreground">{error.message}</p>
          {error.recovery_actions && error.recovery_actions.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {error.recovery_actions.map((action, i) => (
                <Button
                  key={i}
                  size="sm"
                  variant="outline"
                  onClick={() => onRecoveryAction?.(action)}
                  className="h-8 text-xs"
                >
                  {RECOVERY_ICONS[action.action] || <Search className="h-3.5 w-3.5" />}
                  <span className="ml-1">{action.label}</span>
                </Button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

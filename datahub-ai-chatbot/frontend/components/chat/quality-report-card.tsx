"use client";

import { useState } from "react";
import {
  Check,
  ChevronDown,
  ChevronUp,
  CircleAlert,
  CircleX,
  Download,
  FileText,
  Minus,
  Sparkles,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { auth } from "@/lib/auth";
import { cn } from "@/lib/utils";
import type { QualityReport, QualityStatusValue } from "@/lib/types";

const STATUS_BADGE: Record<QualityStatusValue, { label: string; cls: string; icon: React.ReactNode }> = {
  passed: { label: "Passed", cls: "bg-emerald-500/15 text-emerald-600", icon: <Check className="h-3.5 w-3.5" /> },
  warning: { label: "Warning", cls: "bg-amber-500/15 text-amber-600", icon: <CircleAlert className="h-3.5 w-3.5" /> },
  failed: { label: "Failed", cls: "bg-red-500/15 text-red-600", icon: <CircleX className="h-3.5 w-3.5" /> },
  not_evaluated: { label: "Not evaluated", cls: "bg-muted text-muted-foreground", icon: <Minus className="h-3.5 w-3.5" /> },
};

const RATING_CLS: Record<QualityReport["rating"], string> = {
  Excellent: "text-emerald-600",
  Good: "text-sky-600",
  Fair: "text-amber-600",
  Poor: "text-red-600",
};

async function exportReport(report: QualityReport, format: "pdf" | "txt") {
  const res = await fetch("/api/v1/actions/quality/export", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(auth.getToken() ? { Authorization: `Bearer ${auth.getToken()}` } : {}),
    },
    body: JSON.stringify({ report, format }),
  });
  if (!res.ok) throw new Error("Không thể xuất báo cáo");
  const blob = await res.blob();
  const disposition = res.headers.get("Content-Disposition") || "";
  const match = /filename="?([^"]+)"?/.exec(disposition);
  const filename = match?.[1] || `data-quality-report-${report.dataset}.${format}`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function StatusPill({ status }: { status: QualityStatusValue }) {
  const cfg = STATUS_BADGE[status] || STATUS_BADGE.not_evaluated;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold",
        cfg.cls
      )}
    >
      {cfg.icon}
      {cfg.label}
    </span>
  );
}

const PROFILE_KEYS = new Set([
  "completeness",
  "uniqueness",
  "validity",
  "consistency",
  "freshness",
]);

function categoryGroups(report: QualityReport) {
  const groups: { label: string; sections: QualityReport["sections"] }[] = [];
  (Object.entries({
    Metadata: ["metadata"],
    Schema: ["schema"],
    Profiling: [...PROFILE_KEYS],
    Lineage: ["lineage"],
  }) as [string, string[]][]).forEach(([label, keys]) => {
    const sections = report.sections.filter((s) => keys.includes(s.key));
    if (sections.length) groups.push({ label, sections });
  });
  return groups;
}

function worstStatus(sections: QualityReport["sections"]): QualityStatusValue {
  const order: Record<QualityStatusValue, number> = {
    failed: 4,
    warning: 3,
    not_evaluated: 2,
    passed: 1,
  };
  return sections.reduce<QualityStatusValue>(
    (worst, s) => (order[s.status] > order[worst] ? s.status : worst),
    "passed"
  );
}

function issueCount(sections: QualityReport["sections"]) {
  return sections.reduce(
    (n, s) => n + s.findings.filter((f) => f.status === "failed" || f.status === "warning").length,
    0
  );
}

export function QualityReportCard({ report }: { report: QualityReport }) {
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState<"pdf" | "txt" | null>(null);
  const [expanded, setExpanded] = useState(false);

  const handleExport = async (format: "pdf" | "txt") => {
    setError(null);
    setExporting(format);
    try {
      await exportReport(report, format);
    } catch {
      setError("Không thể xuất báo cáo. Vui lòng thử lại.");
    } finally {
      setExporting(null);
    }
  };

  const groups = categoryGroups(report);
  const allIssues = report.sections.flatMap((s) =>
    s.findings
      .filter((f) => f.status === "failed" || f.status === "warning")
      .map((f) => ({ ...f, section: s.title }))
  );
  allIssues.sort((a, b) =>
    a.status === b.status ? a.name.localeCompare(b.name) : a.status === "failed" ? -1 : 1
  );
  const topIssues = allIssues.slice(0, 5);

  const prio: Record<string, number> = { high: 0, medium: 1, low: 2 };
  const topRecs = [...report.recommendations]
    .sort((a, b) => (prio[a.priority] ?? 1) - (prio[b.priority] ?? 1))
    .slice(0, 5);

  return (
    <div className="mt-3 overflow-hidden rounded-2xl border border-border/70 bg-card text-card-foreground shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 bg-muted/30 px-4 py-3">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-primary" />
          <div>
            <p className="text-sm font-semibold leading-tight">Data Quality Report</p>
            <p className="text-xs text-muted-foreground">
              {report.dataset}
              {report.generated_by && ` · tạo bởi ${report.generated_by}`}
              {report.generated_at && ` · ${new Date(report.generated_at).toLocaleString()}`}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <p className={cn("text-lg font-bold leading-none", RATING_CLS[report.rating])}>
              {report.overall_score}/100
            </p>
            <p className="text-[11px] text-muted-foreground">{report.rating}</p>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button size="sm" variant="outline" disabled={exporting !== null}>
                <Download className="mr-1.5 h-4 w-4" />
                {exporting ? "Đang xuất…" : "Export Report"}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Xuất báo cáo</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem disabled={exporting !== null} onClick={() => handleExport("pdf")}>
                <FileText className="mr-2 h-4 w-4" /> Export as PDF
              </DropdownMenuItem>
              <DropdownMenuItem disabled={exporting !== null} onClick={() => handleExport("txt")}>
                <FileText className="mr-2 h-4 w-4" /> Export as TXT
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {error && (
        <p className="border-b border-border/60 bg-destructive/10 px-4 py-2 text-xs text-destructive">
          {error}
        </p>
      )}

      <div className="px-4 py-3">
        {/* Compact executive summary */}
        <div className="mb-1">
          <div className="space-y-1">
            {groups.map(({ label, sections }) => {
              const status = worstStatus(sections);
              const issues = issueCount(sections);
              const summary =
                status === "not_evaluated"
                  ? "Chưa đánh giá (thiếu dữ liệu)"
                  : issues === 0
                    ? "Đạt"
                    : `${issues} vấn đề`;
              return (
                <div key={label} className="flex items-center justify-between gap-3 text-[13px]">
                  <span className="text-muted-foreground">{label}</span>
                  <span className="flex items-center gap-2">
                    <span className="text-foreground">{summary}</span>
                    <StatusPill status={status} />
                  </span>
                </div>
              );
            })}
            {!report.profiling_available && report.not_evaluated_checks.length > 0 && (
              <p className="text-[11px] italic text-muted-foreground">
                Profiling metrics unavailable
              </p>
            )}
          </div>
        </div>

        {topIssues.length > 0 && (
          <div className="mb-3">
            <p className="mb-1.5 text-xs font-semibold text-muted-foreground">
              Vấn đề quan trọng ({allIssues.length})
            </p>
            <ul className="space-y-1">
              {topIssues.map((f, i) => (
                <li key={i} className="flex items-start gap-1.5 text-[13px]">
                  <StatusPill status={f.status} />
                  <span className="text-muted-foreground">
                    <b className="font-medium text-foreground">{f.name}</b>
                    {f.value && <span className="ml-1">[{f.value}]</span>}
                    {" — "}
                    {f.detail}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {topRecs.length > 0 && (
          <div className="mb-3">
            <p className="mb-1.5 text-xs font-semibold text-muted-foreground">
              Khuyến nghị hàng đầu ({report.recommendations.length})
            </p>
            <ul className="space-y-1">
              {topRecs.map((r, i) => (
                <li key={i} className="flex items-start gap-2 text-[13px]">
                  <span
                    className={cn(
                      "mt-0.5 rounded px-1.5 py-0.5 text-[10px] font-bold uppercase",
                      r.priority === "high" && "bg-red-500/15 text-red-600",
                      r.priority === "medium" && "bg-amber-500/15 text-amber-600",
                      r.priority === "low" && "bg-sky-500/15 text-sky-600"
                    )}
                  >
                    {r.priority}
                  </span>
                  <span className="text-muted-foreground">{r.text}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-between text-xs font-semibold"
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? "Ẩn báo cáo chi tiết" : "View Full Report"}
          {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </Button>

        {expanded && (
          <div className="mt-3 max-h-[420px] space-y-3 overflow-y-auto border-t border-border/60 pt-3">
            {report.sections.map((section) => (
              <div key={section.key} className="rounded-xl border border-border/60 p-3">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <span className="text-sm font-semibold">{section.title}</span>
                  <span className="flex items-center gap-2">
                    <span className="text-xs font-medium text-muted-foreground">
                      {section.score}/100
                    </span>
                    <StatusPill status={section.status} />
                  </span>
                </div>
                <ul className="space-y-1">
                  {section.findings.map((f, i) => (
                    <li key={i} className="flex items-start gap-1.5 text-[13px]">
                      <StatusPill status={f.status} />
                      <span className="text-muted-foreground">
                        <b className="font-medium text-foreground">{f.name}</b>
                        {f.value && <span className="ml-1 text-muted-foreground">[{f.value}]</span>}
                        {" — "}
                        {f.detail}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}

            {report.recommendations.length > 0 && (
              <div className="rounded-xl border border-border/60 p-3">
                <p className="mb-2 text-sm font-semibold">Recommendations</p>
                <ul className="space-y-1">
                  {report.recommendations.map((r, i) => (
                    <li key={i} className="flex items-start gap-2 text-[13px]">
                      <span
                        className={cn(
                          "mt-0.5 rounded px-1.5 py-0.5 text-[10px] font-bold uppercase",
                          r.priority === "high" && "bg-red-500/15 text-red-600",
                          r.priority === "medium" && "bg-amber-500/15 text-amber-600",
                          r.priority === "low" && "bg-sky-500/15 text-sky-600"
                        )}
                      >
                        {r.priority}
                      </span>
                      <span className="text-muted-foreground">{r.text}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {report.not_evaluated_checks.length > 0 && (
              <div className="rounded-xl border border-border/60 p-3">
                <p className="mb-2 text-sm font-semibold">Not evaluated</p>
                <div className="flex flex-wrap gap-1.5">
                  {report.not_evaluated_checks.map((c) => (
                    <span
                      key={c}
                      className="rounded-full bg-muted px-2 py-0.5 text-[11px] text-muted-foreground"
                    >
                      {c}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

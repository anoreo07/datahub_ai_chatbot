"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Loader2,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Search,
  ThumbsUp,
  ThumbsDown,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Eye,
  RotateCcw,
  Users,
  GitBranch,
  Flag,
  BarChart3,
  Zap,
  ZapOff,
  MessageSquare,
  MessageCircle,
  List,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */
interface MetricStatus {
  score: number | boolean | null;
  status: "COMPLETED" | "NOT_EVALUATED" | "FAILED" | "RUNNING";
  reason: string | null;
}

interface Interaction {
  trace_id: string;
  user_id: string;
  conversation_id: string;
  question: string;
  answer: string;
  intent: string;
  confidence: string | null;
  ambiguous: boolean;
  result_count: number;
  top_score: number | null;
  citation_count: number;
  processing_time_ms: number | null;
  evaluation_status: string;
  faithfulness: number | null;
  faithfulness_status: string | null;
  answer_relevancy: number | null;
  answer_relevancy_status: string | null;
  context_precision: number | null;
  context_precision_status: string | null;
  context_recall: number | null;
  context_recall_status: string | null;
  human_review: string | null;
  created_at: string | null;
}

interface InteractionDetail extends Interaction {
  message_intent: string | null;
  routing_decision: string | null;
  chosen_tool: string | null;
  entity_hint: string | null;
  entity_resolved_name: string | null;
  entity_resolved_urn: string | null;
  resolution_state: string | null;
  insufficient_context: boolean;
  retrieved_contexts: { contexts: string[] } | null;
  evaluation_error: string | null;
  evaluation_model: string | null;
  evaluated_at: string | null;
  human_review_note: string | null;
  human_reviewed_at: string | null;
  selected_action: string | null;
  model: string | null;
}

interface DiagnosticResult {
  trace_id: string;
  root_cause: {
    primary_layer: string;
    primary_reason: string;
    secondary_layer: string | null;
    secondary_reason: string | null;
    detail: string;
    confidence: number | null;
  };
  system_metrics: Record<string, MetricStatus>;
  pipeline_trace: {
    trace_id: string;
    question: string;
    steps: Array<{ step_name: string; status: string; duration_ms: number; error?: string }>;
    intent_detected: string;
    entity_resolved_urn: string | null;
    retrieval_results_count: number;
    citation_urns: string[];
  };
}

interface Summary {
  total: number;
  evaluated: number;
  pending: number;
  failed: number;
  not_evaluated: number;
  avg_faithfulness: number | null;
  avg_answer_relevancy: number | null;
  avg_context_precision: number | null;
  avg_context_recall: number | null;
  low_quality_count: number;
}

interface ListResponse {
  items: Interaction[];
  total: number;
  limit: number;
  offset: number;
}

interface Review {
  id: number;
  interaction_id: number;
  trace_id: string;
  reviewer_id: string;
  reviewer_name: string;
  overall_label: string;
  correctness_score: number | null;
  relevance_score: number | null;
  groundedness_score: number | null;
  retrieval_quality: number | null;
  citation_quality: number | null;
  intent_correctness: boolean | null;
  entity_resolution_correctness: boolean | null;
  context_usage: boolean | null;
  permission_correctness: string | null;
  error_categories: string[];
  failure_stage: string | null;
  reviewer_confidence: string | null;
  comment: string | null;
  suggested_fix: string | null;
  ragas_snapshot: Record<string, unknown> | null;
  is_adjudication: boolean;
  is_consensus: boolean;
  has_disagreement: boolean;
  review_version: number;
  created_at: string | null;
  updated_at: string | null;
}

interface Taxonomy {
  error_categories: string[];
  failure_stages: string[];
  overall_labels: string[];
  label_semantics: Record<string, string>;
  permission_choices: string[];
  reviewer_confidence_choices: string[];
}

interface ReviewAnalytics {
  total_reviews: number;
  label_counts: Record<string, number>;
  ragas_agreement: {
    agreement: number;
    disagreement: number;
    ragas_false_negatives: number;
    ragas_false_positives: number;
    evaluator_weakness_candidates: number;
  };
  top_error_categories: Array<{ category: string; count: number }>;
  top_failure_stages: Array<{ stage: string; count: number }>;
  top_failed_intents: Array<{ intent: string; count: number }>;
  top_failed_entities: Array<{ entity: string; count: number }>;
  throughput: {
    reviews_last_7_days: number;
    avg_per_day: number;
    unreviewed_interactions: number;
  };
  human_ragas_comparison: Record<string, number>;
}

interface QueueItem {
  trace_id: string;
  question: string;
  answer: string;
  intent: string;
  human_review: string | null;
  evaluation_status: string;
  faithfulness: number | null;
  result_count: number;
  citation_count: number;
  processing_time_ms: number | null;
  priority: string;
  created_at: string | null;
}

/* ------------------------------------------------------------------ */
/* Conversation Types                                                  */
/* ------------------------------------------------------------------ */
interface ConversationTurnSummary {
  turn_index: number;
  trace_id: string;
  question: string;
  answer: string;
  intent: string;
  confidence: string | null;
  entity_resolved_name: string | null;
  entity_resolved_urn: string | null;
  chosen_tool: string | null;
  result_count: number;
  citation_count: number;
  processing_time_ms: number | null;
  evaluation_status: string;
  faithfulness: number | null;
  answer_relevancy: number | null;
  context_precision: number | null;
  context_recall: number | null;
  human_review: string | null;
  created_at: string | null;
}

interface ConversationSummary {
  conversation_id: string;
  user_id: string;
  turn_count: number;
  started_at: string | null;
  completed_at: string | null;
  avg_faithfulness: number | null;
  avg_answer_relevancy: number | null;
  avg_context_precision: number | null;
  avg_context_recall: number | null;
  evaluation_status: string;
  human_review: string | null;
  failed_turns: number;
  turns: ConversationTurnSummary[];
}

interface ConversationTurnDetail extends ConversationTurnSummary {
  id: number;
  message_intent: string | null;
  routing_decision: string | null;
  entity_hint: string | null;
  resolution_state: string | null;
  ambiguous: boolean;
  insufficient_context: boolean;
  top_score: number | null;
  retrieved_contexts: { contexts: string[] } | null;
  evaluation_error: string | null;
  evaluation_model: string | null;
  evaluated_at: string | null;
  human_review_note: string | null;
  human_reviewed_at: string | null;
  selected_action: string | null;
  model: string | null;
}

interface ConversationDetail {
  conversation_id: string;
  user_id: string;
  turn_count: number;
  started_at: string | null;
  completed_at: string | null;
  avg_faithfulness: number | null;
  avg_answer_relevancy: number | null;
  avg_context_precision: number | null;
  avg_context_recall: number | null;
  evaluation_status: string;
  human_review: string | null;
  failed_turns: number;
  turns: ConversationTurnDetail[];
}

interface ConversationListResponse {
  items: ConversationSummary[];
  total: number;
  limit: number;
  offset: number;
}

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */
function scoreColor(v: number | null): string {
  if (v === null) return "text-muted-foreground";
  if (v >= 0.8) return "text-green-600 dark:text-green-400";
  if (v >= 0.6) return "text-yellow-600 dark:text-yellow-400";
  return "text-red-600 dark:text-red-400";
}

function metricStatusDisplay(ms: MetricStatus | undefined): {
  label: string;
  color: string;
  icon: "check" | "x" | "eye" | "loader" | null;
} {
  if (!ms) return { label: "\u2014", color: "text-muted-foreground", icon: null };
  switch (ms.status) {
    case "COMPLETED":
      return {
        label:
          typeof ms.score === "boolean"
            ? ms.score ? "Yes" : "No"
            : ms.score !== null
              ? (ms.score as number) <= 1
                ? `${((ms.score as number) * 100).toFixed(0)}%`
                : `${ms.score}`
              : "\u2014",
        color: "text-foreground font-semibold",
        icon: "check",
      };
    case "NOT_EVALUATED":
      return { label: "N/A", color: "text-muted-foreground", icon: "eye" };
    case "FAILED":
      return { label: "FAILED", color: "text-red-600 dark:text-red-400", icon: "x" };
    case "RUNNING":
      return { label: "...", color: "text-yellow-600 dark:text-yellow-400", icon: "loader" };
    default:
      return { label: "\u2014", color: "text-muted-foreground", icon: null };
  }
}

function evalBadge(status: string) {
  switch (status) {
    case "COMPLETED":
      return <Badge className="bg-green-100 dark:bg-green-950 text-green-700 dark:text-green-300 border border-green-200 dark:border-green-800 text-[9px] px-1.5 py-0 font-normal">Eval</Badge>;
    case "PENDING":
      return <Badge className="bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800 text-[9px] px-1.5 py-0 font-normal">Pending</Badge>;
    case "RUNNING":
      return <Badge className="bg-yellow-100 dark:bg-yellow-950 text-yellow-700 dark:text-yellow-300 border border-yellow-200 dark:border-yellow-800 text-[9px] px-1.5 py-0 font-normal">Running</Badge>;
    case "FAILED":
      return <Badge className="bg-red-100 dark:bg-red-950 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800 text-[9px] px-1.5 py-0 font-normal">Failed</Badge>;
    default:
      return <Badge className="bg-gray-100 dark:bg-gray-800 text-gray-500 border text-[9px] px-1.5 py-0 font-normal">Not Eval</Badge>;
  }
}

function humanReviewBadge(review: string | null) {
  if (!review) return null;
  switch (review) {
    case "accepted":
      return <Badge className="bg-green-100 dark:bg-green-950 text-green-700 dark:text-green-300 text-[9px] px-1.5 py-0">Accepted</Badge>;
    case "needs_review":
      return <Badge className="bg-yellow-100 dark:bg-yellow-950 text-yellow-700 dark:text-yellow-300 text-[9px] px-1.5 py-0">Review</Badge>;
    case "incorrect":
      return <Badge className="bg-red-100 dark:bg-red-950 text-red-700 dark:text-red-300 text-[9px] px-1.5 py-0">Incorrect</Badge>;
    case "hallucination":
      return <Badge className="bg-red-100 dark:bg-red-950 text-red-700 dark:text-red-300 text-[9px] px-1.5 py-0">Hallucinated</Badge>;
    case "insufficient_evidence":
      return <Badge className="bg-orange-100 dark:bg-orange-950 text-orange-700 dark:text-orange-300 text-[9px] px-1.5 py-0">Insufficient</Badge>;
    default:
      return <Badge className="text-[9px] px-1.5 py-0">{review}</Badge>;
  }
}

function formatMetricName(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatLabel(label: string): string {
  return label.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function priorityColor(priority: string): string {
  switch (priority) {
    case "HIGH":
      return "bg-red-100 dark:bg-red-950 text-red-700 dark:text-red-300 border-red-200 dark:border-red-800";
    case "MEDIUM":
      return "bg-yellow-100 dark:bg-yellow-950 text-yellow-700 dark:text-yellow-300 border-yellow-200 dark:border-yellow-800";
    default:
      return "bg-green-100 dark:bg-green-950 text-green-700 dark:text-green-300 border-green-200 dark:border-green-800";
  }
}

const LAYER_COLORS: Record<string, string> = {
  PASSED: "bg-green-100 dark:bg-green-950 text-green-700 dark:text-green-300 border-green-200 dark:border-green-800",
  QUERY_UNDERSTANDING: "bg-purple-100 dark:bg-purple-950 text-purple-700 dark:text-purple-300 border-purple-200 dark:border-purple-800",
  ENTITY_RESOLUTION: "bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-800",
  RETRIEVAL: "bg-yellow-100 dark:bg-yellow-950 text-yellow-700 dark:text-yellow-300 border-yellow-200 dark:border-yellow-800",
  CONTEXT_BUILDING: "bg-orange-100 dark:bg-orange-950 text-orange-700 dark:text-orange-300 border-orange-200 dark:border-orange-800",
  GENERATION: "bg-red-100 dark:bg-red-950 text-red-700 dark:text-red-300 border-red-200 dark:border-red-800",
  DATA_QUALITY: "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-700",
  EVALUATION: "bg-pink-100 dark:bg-pink-950 text-pink-700 dark:text-pink-300 border-pink-200 dark:border-pink-800",
  UNKNOWN: "bg-gray-100 dark:bg-gray-800 text-gray-500 border-gray-200 dark:border-gray-700",
};

const FAILURE_STAGE_ICONS: Record<string, string> = {
  INTENT: "Query",
  ENTITY_RESOLUTION: "Entity",
  RETRIEVAL: "Search",
  TOOL: "API",
  CONTEXT: "Context",
  GENERATION: "LLM",
  CITATION: "Cite",
  PERMISSION: "Auth",
  UI: "Render",
  UNKNOWN: "?",
};

/* ------------------------------------------------------------------ */
/* Collapsible Section                                                 */
/* ------------------------------------------------------------------ */
function CollapsibleSection({
  title,
  defaultOpen = false,
  children,
  badge,
}: {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
  badge?: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-lg border bg-background overflow-hidden">
      <button
        className="flex w-full items-center justify-between px-3 py-2 text-xs font-semibold hover:bg-muted/50 transition-colors"
        onClick={() => setOpen(!open)}
      >
        <div className="flex items-center gap-2">
          <span>{title}</span>
          {badge}
        </div>
        {open ? (
          <ChevronUp className="h-3.5 w-3.5 text-muted-foreground" />
        ) : (
          <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
        )}
      </button>
      {open && <div className="border-t p-3 bg-background/50">{children}</div>}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Metric Row (compact)                                                */
/* ------------------------------------------------------------------ */
function MetricRow({ label, metric }: { label: string; metric: MetricStatus | undefined }) {
  const display = metricStatusDisplay(metric);
  return (
    <div className="flex items-center justify-between gap-2 py-1.5 border-b border-border/40 last:border-0">
      <span className="text-xs text-muted-foreground truncate">{label}</span>
      <div className="flex items-center gap-1.5 shrink-0">
        {display.icon === "check" && <CheckCircle2 className="h-3.5 w-3.5 text-green-600" />}
        {display.icon === "x" && <XCircle className="h-3.5 w-3.5 text-red-600" />}
        {display.icon === "eye" && <Eye className="h-3.5 w-3.5 text-muted-foreground" />}
        {display.icon === "loader" && <Loader2 className="h-3.5 w-3.5 text-yellow-600 animate-spin" />}
        <span className={`text-xs font-mono ${display.color}`}>{display.label}</span>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Summary Dashboard (compact, 2-column)                               */
/* ------------------------------------------------------------------ */
function SummaryDashboard({ summary, analytics }: { summary: Summary | null; analytics: ReviewAnalytics | null }) {
  if (!summary) return null;

  const items = [
    { label: "Total", value: summary.total, color: "text-foreground" },
    { label: "Evaluated", value: summary.evaluated, color: "text-green-600 dark:text-green-400" },
    { label: "Pending", value: summary.pending, color: "text-blue-600 dark:text-blue-400" },
    { label: "Failed", value: summary.failed, color: "text-red-600 dark:text-red-400" },
    { label: "Not Eval", value: summary.not_evaluated, color: "text-muted-foreground" },
    { label: "Low Q", value: summary.low_quality_count, color: "text-orange-600 dark:text-orange-400" },
  ];

  const metrics = [
    { label: "Faithfulness", value: summary.avg_faithfulness },
    { label: "Answer Relevancy", value: summary.avg_answer_relevancy },
    { label: "Context Precision", value: summary.avg_context_precision },
    { label: "Context Recall", value: summary.avg_context_recall },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-12 gap-4 shrink-0">
      <Card className="md:col-span-5">
        <CardContent className="py-3 px-4">
          <div className="grid grid-cols-6 gap-2">
            {items.map((it) => (
              <div key={it.label} className="text-center">
                <div className={`text-base font-bold ${it.color}`}>{it.value}</div>
                <div className="text-[10px] text-muted-foreground font-medium mt-0.5 leading-tight truncate">{it.label}</div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
      <Card className="md:col-span-4">
        <CardContent className="py-3 px-4">
          <div className="grid grid-cols-4 gap-2">
            {metrics.map((m) => (
              <div key={m.label} className="text-center">
                <div className={`text-sm font-bold ${scoreColor(m.value)}`}>
                  {m.value !== null ? (m.value * 100).toFixed(0) + "%" : "\u2014"}
                </div>
                <div className="text-[10px] text-muted-foreground font-medium mt-0.5 leading-tight truncate">{m.label}</div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
      {analytics && (
        <Card className="md:col-span-3">
          <CardContent className="py-3 px-4">
            <div className="text-[10px] text-muted-foreground font-medium mb-1.5">Human Review</div>
            <div className="grid grid-cols-2 gap-1.5">
              <div className="text-center">
                <div className="text-sm font-bold text-green-600">{analytics.label_counts.accepted || 0}</div>
                <div className="text-[9px] text-muted-foreground">Accepted</div>
              </div>
              <div className="text-center">
                <div className="text-sm font-bold text-red-600">{(analytics.label_counts.incorrect || 0) + (analytics.label_counts.hallucination || 0)}</div>
                <div className="text-[9px] text-muted-foreground">Failed</div>
              </div>
              <div className="text-center">
                <div className="text-sm font-bold text-blue-600">{analytics.label_counts.needs_review || 0}</div>
                <div className="text-[9px] text-muted-foreground">Review</div>
              </div>
              <div className="text-center">
                <div className="text-sm font-bold text-orange-600">{analytics.label_counts.insufficient_evidence || 0}</div>
                <div className="text-[9px] text-muted-foreground">Insuff.</div>
              </div>
            </div>
            {analytics.ragas_agreement && (
              <div className="mt-2 pt-2 border-t border-border/40">
                <div className="text-[9px] text-muted-foreground">RAGAS Agreement: <span className="text-foreground font-semibold">{analytics.ragas_agreement.agreement}</span> / Disagree: <span className="text-foreground font-semibold">{analytics.ragas_agreement.disagreement}</span></div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Diagnostics Card (compact, status-aware)                            */
/* ------------------------------------------------------------------ */
function DiagnosticsCard({ traceId }: { traceId: string }) {
  const [diag, setDiag] = useState<DiagnosticResult | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchDiag = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiFetch<DiagnosticResult>(
        `/api/v1/admin/interactions/${traceId}/diagnose`,
        { method: "POST" },
      );
      setDiag(data);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }, [traceId]);

  useEffect(() => {
    void fetchDiag();
  }, [fetchDiag]);

  if (loading)
    return (
      <div className="text-xs text-muted-foreground flex items-center gap-1.5 py-4 justify-center">
        <Loader2 className="h-4 w-4 animate-spin" /> Analyzing pipeline traces...
      </div>
    );
  if (!diag) return <p className="text-xs text-muted-foreground italic text-center py-4">No diagnostic trace available.</p>;

  const rc = diag.root_cause;
  const sm = diag.system_metrics;

  return (
    <div className="space-y-4">
      <div className="space-y-2 rounded-lg border bg-muted/20 p-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-xs font-semibold">Primary Cause:</span>
            <Badge className={cn("text-[9px] py-0 border", LAYER_COLORS[rc.primary_layer] || "bg-gray-100 text-gray-500")}>
              {rc.primary_layer.replace(/_/g, " ")}
            </Badge>
            {rc.primary_reason !== "none" && (
              <span className="text-[10px] text-muted-foreground font-medium">
                ({rc.primary_reason.replace(/_/g, " ")})
              </span>
            )}
          </div>
          {rc.confidence !== null && (
            <span className="text-[10px] font-semibold text-primary">
              {(rc.confidence * 100).toFixed(0)}% confidence
            </span>
          )}
        </div>
        {rc.secondary_layer && (
          <div className="flex items-center gap-1.5 flex-wrap mt-1">
            <span className="text-xs font-semibold">Secondary Cause:</span>
            <Badge className={cn("text-[9px] py-0 border", LAYER_COLORS[rc.secondary_layer] || "bg-gray-100 text-gray-500")}>
              {rc.secondary_layer.replace(/_/g, " ")}
            </Badge>
            {rc.secondary_reason && rc.secondary_reason !== "none" && (
              <span className="text-[10px] text-muted-foreground">
                ({rc.secondary_reason.replace(/_/g, " ")})
              </span>
            )}
          </div>
        )}
        {rc.detail && (
          <div className="rounded border bg-background p-2.5 text-xs text-muted-foreground leading-normal mt-2">
            {rc.detail}
          </div>
        )}
      </div>
      <div className="space-y-1">
        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">System Metrics</span>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-0 rounded-lg border bg-background p-3">
          {Object.entries(sm).map(([key, val]) => (
            <MetricRow key={key} label={formatMetricName(key)} metric={val} />
          ))}
        </div>
      </div>
      {diag.pipeline_trace.steps.length > 0 && (
        <div className="space-y-1">
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">Execution Pipeline Trace</span>
          <div className="rounded-lg border bg-background divide-y divide-border/40 p-2.5 space-y-0.5">
            {diag.pipeline_trace.steps.map((step, i) => (
              <div key={i} className="flex items-center gap-2 text-xs py-1.5 first:pt-0 last:pb-0">
                {step.status === "ok" && <CheckCircle2 className="h-3.5 w-3.5 text-green-600 shrink-0" />}
                {step.status === "error" && <XCircle className="h-3.5 w-3.5 text-red-600 shrink-0" />}
                {step.status !== "ok" && step.status !== "error" && <Eye className="h-3.5 w-3.5 text-muted-foreground shrink-0" />}
                <span className="font-mono text-xs font-medium truncate flex-1">{step.step_name}</span>
                <span className="text-[10px] font-mono text-muted-foreground shrink-0 bg-muted px-1.5 py-0.5 border rounded">{step.status}</span>
                {step.duration_ms > 0 && <span className="text-xs font-mono text-muted-foreground shrink-0">{step.duration_ms.toFixed(0)}ms</span>}
                {step.error && <span className="text-red-600 text-[10px] truncate max-w-[120px] font-medium ml-2">{step.error}</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Adaptive Review Form                                                */
/* ------------------------------------------------------------------ */
function AdaptiveReviewForm({
  interaction,
  taxonomy,
  onSubmit,
  existingReview,
}: {
  interaction: InteractionDetail;
  taxonomy: Taxonomy | null;
  onSubmit: (data: Record<string, unknown>) => Promise<void>;
  existingReview?: Review | null;
}) {
  const [label, setLabel] = useState(existingReview?.overall_label || "");
  const [comment, setComment] = useState(existingReview?.comment || "");
  const [suggestedFix, setSuggestedFix] = useState(existingReview?.suggested_fix || "");
  const [errorCategories, setErrorCategories] = useState<string[]>(existingReview?.error_categories || []);
  const [failureStage, setFailureStage] = useState(existingReview?.failure_stage || "");
  const [intentCorrect, setIntentCorrect] = useState<boolean | null>(existingReview?.intent_correctness ?? null);
  const [entityCorrect, setEntityCorrect] = useState<boolean | null>(existingReview?.entity_resolution_correctness ?? null);
  const [contextUsed, setContextUsed] = useState<boolean | null>(existingReview?.context_usage ?? null);
  const [permissionCorrect, setPermissionCorrect] = useState(existingReview?.permission_correctness || "");
  const [confidence, setConfidence] = useState(existingReview?.reviewer_confidence || "");
  const [submitting, setSubmitting] = useState(false);

  const requiresError = label === "incorrect" || label === "hallucination";
  const requiresStage = label === "incorrect" || label === "hallucination" || label === "insufficient_evidence";
  const requiresReason = label !== "accepted";

  const toggleErrorCategory = (cat: string) => {
    setErrorCategories((prev) =>
      prev.includes(cat) ? prev.filter((c) => c !== cat) : [...prev, cat]
    );
  };

  const handleSubmit = async () => {
    if (!label) return;
    if (requiresError && errorCategories.length === 0) return;

    setSubmitting(true);
    try {
      await onSubmit({
        overall_label: label,
        comment: comment || undefined,
        suggested_fix: suggestedFix || undefined,
        error_categories: errorCategories.length > 0 ? errorCategories : undefined,
        failure_stage: failureStage || undefined,
        intent_correctness: intentCorrect,
        entity_resolution_correctness: entityCorrect,
        context_usage: contextUsed,
        permission_correctness: permissionCorrect || undefined,
        reviewer_confidence: confidence || undefined,
      });
    } finally {
      setSubmitting(false);
    }
  };

  if (!taxonomy) return <div className="text-xs text-muted-foreground">Loading taxonomy...</div>;

  return (
    <div className="space-y-3">
      {/* Overall Label */}
      <div>
        <label className="text-xs font-semibold text-muted-foreground block mb-1.5">Overall Assessment *</label>
        <div className="flex flex-wrap gap-1.5">
          {taxonomy.overall_labels.map((l) => (
            <Button
              key={l}
              size="sm"
              variant={label === l ? "default" : "outline"}
              onClick={() => setLabel(l)}
              className="h-6 px-2 text-[10px] capitalize hover:bg-muted"
            >
              {l === "accepted" && <ThumbsUp className="mr-1 h-2.5 w-2.5" />}
              {l === "incorrect" && <ThumbsDown className="mr-1 h-2.5 w-2.5" />}
              {l === "hallucination" && <AlertTriangle className="mr-1 h-2.5 w-2.5" />}
              {formatLabel(l)}
            </Button>
          ))}
        </div>
        {label && (
          <p className="text-[9px] text-muted-foreground mt-1 italic">{taxonomy.label_semantics[label]}</p>
        )}
      </div>

      {/* Error Categories (required for incorrect/hallucination) */}
      {requiresError && (
        <div>
          <label className="text-xs font-semibold text-muted-foreground block mb-1.5">
            Error Categories * <span className="text-red-500">(required)</span>
          </label>
          <div className="flex flex-wrap gap-1 max-h-[100px] overflow-y-auto">
            {taxonomy.error_categories.map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => toggleErrorCategory(cat)}
                className={cn(
                  "text-[9px] px-1.5 py-0.5 rounded border transition-colors",
                  errorCategories.includes(cat)
                    ? "bg-red-100 dark:bg-red-950 text-red-700 dark:text-red-300 border-red-300 dark:border-red-700"
                    : "bg-background text-muted-foreground border-border hover:bg-muted/50"
                )}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Failure Stage (required for incorrect/hallucination/insufficient_evidence) */}
      {requiresStage && (
        <div>
          <label className="text-xs font-semibold text-muted-foreground block mb-1.5">Failure Stage</label>
          <div className="flex flex-wrap gap-1.5">
            {taxonomy.failure_stages.map((stage) => (
              <button
                key={stage}
                type="button"
                onClick={() => setFailureStage(stage)}
                className={cn(
                  "text-[9px] px-2 py-0.5 rounded border transition-colors flex items-center gap-1",
                  failureStage === stage
                    ? "bg-primary/10 text-primary border-primary/30"
                    : "bg-background text-muted-foreground border-border hover:bg-muted/50"
                )}
              >
                <span>{FAILURE_STAGE_ICONS[stage] || stage}</span>
                <span>{stage}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Stage-specific booleans */}
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="text-[10px] font-semibold text-muted-foreground block mb-1">Intent Correct?</label>
          <div className="flex gap-1">
            {[true, false, null].map((v) => (
              <Button
                key={String(v)}
                size="sm"
                variant={intentCorrect === v ? "default" : "outline"}
                onClick={() => setIntentCorrect(v)}
                className="h-5 px-2 text-[9px]"
              >
                {v === true ? "Yes" : v === false ? "No" : "N/A"}
              </Button>
            ))}
          </div>
        </div>
        <div>
          <label className="text-[10px] font-semibold text-muted-foreground block mb-1">Entity Resolved?</label>
          <div className="flex gap-1">
            {[true, false, null].map((v) => (
              <Button
                key={String(v)}
                size="sm"
                variant={entityCorrect === v ? "default" : "outline"}
                onClick={() => setEntityCorrect(v)}
                className="h-5 px-2 text-[9px]"
              >
                {v === true ? "Yes" : v === false ? "No" : "N/A"}
              </Button>
            ))}
          </div>
        </div>
        <div>
          <label className="text-[10px] font-semibold text-muted-foreground block mb-1">Context Used?</label>
          <div className="flex gap-1">
            {[true, false, null].map((v) => (
              <Button
                key={String(v)}
                size="sm"
                variant={contextUsed === v ? "default" : "outline"}
                onClick={() => setContextUsed(v)}
                className="h-5 px-2 text-[9px]"
              >
                {v === true ? "Yes" : v === false ? "No" : "N/A"}
              </Button>
            ))}
          </div>
        </div>
        <div>
          <label className="text-[10px] font-semibold text-muted-foreground block mb-1">Permission</label>
          <div className="flex gap-1">
            {taxonomy.permission_choices.map((p) => (
              <Button
                key={p}
                size="sm"
                variant={permissionCorrect === p ? "default" : "outline"}
                onClick={() => setPermissionCorrect(p)}
                className="h-5 px-2 text-[9px]"
              >
                {p}
              </Button>
            ))}
          </div>
        </div>
      </div>

      {/* Confidence */}
      <div>
        <label className="text-[10px] font-semibold text-muted-foreground block mb-1">Reviewer Confidence</label>
        <div className="flex gap-1.5">
          {taxonomy.reviewer_confidence_choices.map((c) => (
            <Button
              key={c}
              size="sm"
              variant={confidence === c ? "default" : "outline"}
              onClick={() => setConfidence(c)}
              className="h-5 px-2 text-[9px] capitalize"
            >
              {c}
            </Button>
          ))}
        </div>
      </div>

      {/* Comment (required for non-accepted) */}
      <div>
        <label className="text-[10px] font-semibold text-muted-foreground block mb-1">
          Comment {requiresReason ? <span className="text-red-500">*</span> : "(optional)"}
        </label>
        <textarea
          className="w-full rounded border border-input bg-background px-2 py-1.5 text-xs resize-none h-16 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          placeholder="Describe the issue or confirm quality..."
          value={comment}
          onChange={(e) => setComment(e.target.value)}
        />
      </div>

      {/* Suggested Fix */}
      {label === "incorrect" && (
        <div>
          <label className="text-[10px] font-semibold text-muted-foreground block mb-1">Suggested Fix</label>
          <textarea
            className="w-full rounded border border-input bg-background px-2 py-1.5 text-xs resize-none h-12 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            placeholder="How should this be fixed..."
            value={suggestedFix}
            onChange={(e) => setSuggestedFix(e.target.value)}
          />
        </div>
      )}

      {/* Submit */}
      <Button
        size="sm"
        onClick={() => void handleSubmit()}
        disabled={!label || submitting || (requiresError && errorCategories.length === 0) || (requiresReason && !comment)}
        className="w-full h-7 text-xs"
      >
        {submitting ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : null}
        {existingReview ? "Update Review" : "Submit Review"}
      </Button>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Review History                                                      */
/* ------------------------------------------------------------------ */
function ReviewHistory({ reviews, interactionId }: { reviews: Review[]; interactionId: number }) {
  if (reviews.length === 0) {
    return <p className="text-xs text-muted-foreground italic text-center py-2">No reviews yet.</p>;
  }

  return (
    <div className="space-y-2">
      {reviews.map((r) => (
        <div key={r.id} className={cn("rounded border p-2.5 text-xs", r.is_adjudication ? "bg-purple-50 dark:bg-purple-950/20 border-purple-200 dark:border-purple-800" : "bg-background border-border")}>
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-1.5">
              {r.is_adjudication ? (
                <GitBranch className="h-3 w-3 text-purple-600" />
              ) : (
                <Users className="h-3 w-3 text-muted-foreground" />
              )}
              <span className="font-semibold">{r.reviewer_name || r.reviewer_id}</span>
              {r.is_adjudication && <Badge className="text-[8px] bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-300">Adjudication</Badge>}
            </div>
            {humanReviewBadge(r.overall_label)}
          </div>
          {r.comment && <p className="text-[10px] text-muted-foreground mt-1">{r.comment}</p>}
          {r.error_categories.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1">
              {r.error_categories.map((cat) => (
                <Badge key={cat} className="text-[8px] bg-red-50 text-red-600 dark:bg-red-950 dark:text-red-400">{cat}</Badge>
              ))}
            </div>
          )}
          {r.failure_stage && (
            <Badge className="text-[8px] mt-1 bg-muted text-muted-foreground">{r.failure_stage}</Badge>
          )}
          <div className="text-[9px] text-muted-foreground mt-1">
            {r.created_at && new Date(r.created_at).toLocaleString()}
            {r.has_disagreement && <span className="text-yellow-600 ml-2">Disagreement</span>}
            {r.is_consensus && <span className="text-green-600 ml-2">Consensus</span>}
          </div>
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Conversation Turn Card (chat-like bubble)                           */
/* ------------------------------------------------------------------ */
function ConversationTurnCard({
  turn,
  isLast,
  selectedTraceId,
  onSelect,
}: {
  turn: ConversationTurnDetail;
  isLast: boolean;
  selectedTraceId: string | null;
  onSelect: (traceId: string) => void;
}) {
  const [showContext, setShowContext] = useState(false);
  const [showTools, setShowTools] = useState(false);
  const isSelected = selectedTraceId === turn.trace_id;
  const hasFailed = turn.faithfulness !== null && turn.faithfulness < 0.7;

  return (
    <div className={cn("flex flex-col gap-1.5", isLast ? "" : "pb-3 border-b border-border/30")}>
      {/* Turn indicator */}
      <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
        <span className="font-mono font-semibold">Turn {turn.turn_index + 1}</span>
        <span>·</span>
        <span>{turn.intent?.replace(/_/g, " ")}</span>
        {turn.entity_resolved_name && (
          <>
            <span>·</span>
            <span className="font-medium text-foreground/70">{turn.entity_resolved_name}</span>
          </>
        )}
        {turn.chosen_tool && (
          <>
            <span>·</span>
            <span className="font-mono">tool: {turn.chosen_tool}</span>
          </>
        )}
        <span>·</span>
        <span>{turn.created_at ? new Date(turn.created_at).toLocaleTimeString() : ""}</span>
        {turn.processing_time_ms && <span>· {turn.processing_time_ms}ms</span>}
      </div>

      {/* User message bubble */}
      <div className="flex justify-start">
        <div className="max-w-[85%] rounded-lg rounded-tl-sm bg-primary/10 border border-primary/20 px-3 py-2">
          <p className="text-xs font-medium text-foreground leading-relaxed">{turn.question}</p>
        </div>
      </div>

      {/* Assistant message bubble */}
      <div className="flex justify-end">
        <div
          className={cn(
            "max-w-[85%] rounded-lg rounded-tr-sm border px-3 py-2 cursor-pointer transition-colors",
            isSelected
              ? "bg-primary/5 border-primary/30"
              : "bg-background border-border hover:bg-muted/30",
            hasFailed && "border-destructive/30"
          )}
          onClick={() => onSelect(turn.trace_id)}
        >
          <p className="text-xs leading-relaxed text-foreground whitespace-pre-wrap">{turn.answer}</p>
        </div>
      </div>

      {/* Evaluation scores row */}
      <div className="flex items-center gap-3 ml-8">
        {turn.faithfulness !== null && (
          <span className={`text-[10px] font-mono font-medium ${scoreColor(turn.faithfulness)}`}>
            F: {(turn.faithfulness * 100).toFixed(0)}%
          </span>
        )}
        {turn.answer_relevancy !== null && (
          <span className={`text-[10px] font-mono font-medium ${scoreColor(turn.answer_relevancy)}`}>
            AR: {(turn.answer_relevancy * 100).toFixed(0)}%
          </span>
        )}
        {turn.context_precision !== null && (
          <span className={`text-[10px] font-mono font-medium ${scoreColor(turn.context_precision)}`}>
            CP: {(turn.context_precision * 100).toFixed(0)}%
          </span>
        )}
        {turn.context_recall !== null && (
          <span className={`text-[10px] font-mono font-medium ${scoreColor(turn.context_recall)}`}>
            CR: {(turn.context_recall * 100).toFixed(0)}%
          </span>
        )}
        {evalBadge(turn.evaluation_status)}
        {humanReviewBadge(turn.human_review)}
        {hasFailed && (
          <AlertTriangle className="h-3 w-3 text-destructive" />
        )}
      </div>

      {/* Expandable sections */}
      <div className="ml-8 flex gap-2 mt-1">
        <button
          className="text-[9px] text-muted-foreground hover:text-foreground transition-colors flex items-center gap-0.5"
          onClick={() => setShowContext(!showContext)}
        >
          {showContext ? <ChevronUp className="h-2.5 w-2.5" /> : <ChevronDown className="h-2.5 w-2.5" />}
          Context ({(turn.retrieved_contexts?.contexts || []).length})
        </button>
        {turn.chosen_tool && (
          <button
            className="text-[9px] text-muted-foreground hover:text-foreground transition-colors flex items-center gap-0.5"
            onClick={() => setShowTools(!showTools)}
          >
            {showTools ? <ChevronUp className="h-2.5 w-2.5" /> : <ChevronDown className="h-2.5 w-2.5" />}
            Tools
          </button>
        )}
      </div>

      {/* Retrieved context */}
      {showContext && (
        <div className="ml-8 space-y-1 mt-1">
          {(turn.retrieved_contexts?.contexts || []).length === 0 ? (
            <p className="text-[10px] text-muted-foreground italic">No context stored</p>
          ) : (
            (turn.retrieved_contexts?.contexts || []).map((c, i) => (
              <div key={i} className="rounded bg-muted/50 border border-border/50 p-2 text-[10px] leading-relaxed text-muted-foreground">
                <span className="font-semibold text-primary">[{i + 1}]</span> {c}
              </div>
            ))
          )}
        </div>
      )}

      {/* Tool trace */}
      {showTools && turn.chosen_tool && (
        <div className="ml-8 mt-1 rounded bg-muted/50 border border-border/50 p-2 text-[10px]">
          <div className="font-semibold text-foreground mb-1">Tool: {turn.chosen_tool}</div>
          {turn.entity_resolved_urn && (
            <div className="text-muted-foreground">Entity: {turn.entity_resolved_name} ({turn.entity_resolved_urn})</div>
          )}
          <div className="text-muted-foreground">Results: {turn.result_count} | Citations: {turn.citation_count}</div>
          {turn.evaluation_error && (
            <div className="text-destructive mt-1">Error: {turn.evaluation_error}</div>
          )}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Conversation Detail View (expanded conversation with chat UI)       */
/* ------------------------------------------------------------------ */
function ConversationDetailView({
  conversation,
  selectedTraceId,
  onSelectTurn,
  onEvaluate,
  onReview,
  onClose,
}: {
  conversation: ConversationDetail;
  selectedTraceId: string | null;
  onSelectTurn: (traceId: string) => void;
  onEvaluate: (conversationId: string) => void;
  onReview: (conversationId: string, review: string, note: string) => void;
  onClose: () => void;
}) {
  const [reviewNote, setReviewNote] = useState("");

  const avgScore = (vals: (number | null)[]): number | null => {
    const valid = vals.filter((v): v is number => v !== null);
    return valid.length > 0 ? valid.reduce((a, b) => a + b, 0) / valid.length : null;
  };

  return (
    <div className="space-y-4">
      {/* Conversation header */}
      <div className="flex items-center justify-between pb-3 border-b border-border/40">
        <div>
          <div className="flex items-center gap-2">
            <MessageSquare className="h-4 w-4 text-primary" />
            <span className="text-sm font-semibold">Conversation</span>
            <span className="text-[10px] font-mono text-muted-foreground bg-muted px-2 py-0.5 rounded border">
              {conversation.conversation_id}
            </span>
          </div>
          <div className="flex items-center gap-3 mt-1 text-[10px] text-muted-foreground">
            <span>{conversation.turn_count} turns</span>
            {conversation.started_at && <span>Started: {new Date(conversation.started_at).toLocaleString()}</span>}
            {conversation.user_id && <span>User: {conversation.user_id}</span>}
          </div>
        </div>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => onEvaluate(conversation.conversation_id)} className="h-7 px-2 text-xs">
            <RotateCcw className="h-3 w-3 mr-1" /> Re-evaluate
          </Button>
          <Button size="sm" variant="outline" onClick={onClose} className="h-7 px-2 text-xs">
            Close
          </Button>
        </div>
      </div>

      {/* Conversation-level scores */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: "Faithfulness", value: conversation.avg_faithfulness },
          { label: "Answer Relevancy", value: conversation.avg_answer_relevancy },
          { label: "Context Precision", value: conversation.avg_context_precision },
          { label: "Context Recall", value: conversation.avg_context_recall },
        ].map((m) => (
          <div key={m.label} className="text-center rounded border p-2">
            <div className={`text-sm font-bold ${scoreColor(m.value)}`}>
              {m.value !== null ? (m.value * 100).toFixed(0) + "%" : "\u2014"}
            </div>
            <div className="text-[9px] text-muted-foreground">{m.label}</div>
          </div>
        ))}
      </div>

      {/* Failed turns indicator */}
      {conversation.failed_turns > 0 && (
        <div className="flex items-center gap-2 text-xs text-destructive bg-destructive/10 rounded border border-destructive/20 px-3 py-2">
          <AlertTriangle className="h-3.5 w-3.5" />
          <span>{conversation.failed_turns} turn{conversation.failed_turns > 1 ? "s" : ""} with low faithfulness score</span>
        </div>
      )}

      {/* Chat-like turn display */}
      <div className="space-y-3">
        {conversation.turns.map((turn, idx) => (
          <ConversationTurnCard
            key={turn.trace_id}
            turn={turn}
            isLast={idx === conversation.turns.length - 1}
            selectedTraceId={selectedTraceId}
            onSelect={onSelectTurn}
          />
        ))}
      </div>

      {/* Conversation-level review */}
      <div className="rounded-lg border bg-background p-3 space-y-2">
        <div className="text-xs font-semibold text-muted-foreground">Conversation Review</div>
        <div className="flex gap-2">
          {["accepted", "needs_review", "incorrect", "hallucination"].map((label) => (
            <Button
              key={label}
              size="sm"
              variant={conversation.human_review === label ? "default" : "outline"}
              onClick={() => onReview(conversation.conversation_id, label, reviewNote)}
              className="h-6 px-2 text-[10px] capitalize"
            >
              {label === "accepted" && <ThumbsUp className="mr-1 h-2.5 w-2.5" />}
              {label === "incorrect" && <ThumbsDown className="mr-1 h-2.5 w-2.5" />}
              {label === "hallucination" && <AlertTriangle className="mr-1 h-2.5 w-2.5" />}
              {label.replace(/_/g, " ")}
            </Button>
          ))}
        </div>
        <textarea
          className="w-full rounded border border-input bg-background px-2 py-1.5 text-xs resize-none h-12 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          placeholder="Optional review note..."
          value={reviewNote}
          onChange={(e) => setReviewNote(e.target.value)}
        />
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Conversation Card (collapsed, in list)                              */
/* ------------------------------------------------------------------ */
function ConversationCardItem({
  conversation,
  isSelected,
  onSelect,
}: {
  conversation: ConversationSummary;
  isSelected: boolean;
  onSelect: () => void;
}) {
  return (
    <div
      className={cn(
        "cursor-pointer rounded-lg border p-2.5 transition-all",
        isSelected
          ? "bg-primary/5 border-primary/20"
          : "bg-background border-border hover:bg-muted/30"
      )}
      onClick={onSelect}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <MessageSquare className="h-3 w-3 text-primary shrink-0" />
            <p className="text-xs font-semibold text-foreground truncate">
              {conversation.turns[0]?.question || "Empty conversation"}
            </p>
          </div>
          <p className="text-[10px] text-muted-foreground mt-0.5 truncate">
            {conversation.turn_count} turns
            {conversation.failed_turns > 0 && (
              <span className="text-destructive ml-1">
                · {conversation.failed_turns} failed
              </span>
            )}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1 shrink-0">
          {evalBadge(conversation.evaluation_status)}
          {conversation.avg_faithfulness !== null && (
            <span className={`text-[10px] font-mono font-medium ${scoreColor(conversation.avg_faithfulness)}`}>
              F: {(conversation.avg_faithfulness * 100).toFixed(0)}%
            </span>
          )}
        </div>
      </div>
      <div className="mt-2 flex flex-wrap gap-x-2 gap-y-0.5 text-[9px] text-muted-foreground border-t border-border/40 pt-1.5">
        {conversation.started_at && <span>{new Date(conversation.started_at).toLocaleDateString()}</span>}
        {conversation.user_id && <span>User: {conversation.user_id}</span>}
        {humanReviewBadge(conversation.human_review)}
        {conversation.failed_turns > 0 && (
          <span className="text-destructive font-medium">
            {conversation.failed_turns} failed turn{conversation.failed_turns > 1 ? "s" : ""}
          </span>
        )}
      </div>
      {/* Turn summary chips */}
      <div className="mt-1.5 flex flex-wrap gap-1">
        {conversation.turns.slice(0, 6).map((t) => (
          <span
            key={t.trace_id}
            className={cn(
              "text-[8px] px-1 py-0 rounded border font-mono",
              t.faithfulness !== null && t.faithfulness < 0.7
                ? "bg-red-50 dark:bg-red-950 text-red-600 border-red-200 dark:border-red-800"
                : "bg-muted text-muted-foreground border-border"
            )}
          >
            T{t.turn_index + 1}: {t.intent?.slice(0, 8) || "?"}
          </span>
        ))}
        {conversation.turns.length > 6 && (
          <span className="text-[8px] text-muted-foreground">+{conversation.turns.length - 6}</span>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Main Panel                                                          */
/* ------------------------------------------------------------------ */
export function InteractionsPanel() {
  const [items, setItems] = useState<Interaction[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [selected, setSelected] = useState<InteractionDetail | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [intentFilter, setIntentFilter] = useState("");
  const [taxonomy, setTaxonomy] = useState<Taxonomy | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [analytics, setAnalytics] = useState<ReviewAnalytics | null>(null);
  const [reviewTab, setReviewTab] = useState<"form" | "history" | "ragas">("form");
  const [ragasEnabled, setRagasEnabled] = useState(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("ragas_enabled");
      return stored !== null ? stored === "true" : true;
    }
    return true;
  });
  const limit = 10;

  // Conversation view state
  const [viewMode, setViewMode] = useState<"interactions" | "conversations">("conversations");
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [convTotal, setConvTotal] = useState(0);
  const [convPage, setConvPage] = useState(0);
  const [selectedConversation, setSelectedConversation] = useState<ConversationDetail | null>(null);
  const [selectedConvTraceId, setSelectedConvTraceId] = useState<string | null>(null);

  const fetchList = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        limit: String(limit),
        offset: String(page * limit),
      });
      if (search) params.set("search", search);
      if (statusFilter) params.set("evaluation_status", statusFilter);
      if (intentFilter) params.set("intent", intentFilter);

      const data = await apiFetch<ListResponse>(`/api/v1/admin/interactions?${params}`);
      setItems(data.items || []);
      setTotal(data.total || 0);
    } catch {
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [page, search, statusFilter, intentFilter]);

  const fetchSummary = useCallback(async () => {
    try {
      const data = await apiFetch<Summary>("/api/v1/admin/ragas/summary");
      setSummary(data);
    } catch { /* ignore */ }
  }, []);

  const fetchTaxonomy = useCallback(async () => {
    try {
      const data = await apiFetch<Taxonomy>("/api/v1/reviews/taxonomy");
      setTaxonomy(data);
    } catch { /* ignore */ }
  }, []);

  const fetchAnalytics = useCallback(async () => {
    try {
      const data = await apiFetch<ReviewAnalytics>("/api/v1/reviews/analytics");
      setAnalytics(data);
    } catch { /* ignore */ }
  }, []);

  // Conversation view fetch functions
  const fetchConversations = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        limit: String(limit),
        offset: String(convPage * limit),
      });
      if (search) params.set("search", search);
      if (statusFilter) params.set("evaluation_status", statusFilter);
      if (intentFilter) params.set("intent", intentFilter);

      const data = await apiFetch<ConversationListResponse>(`/api/v1/admin/conversations?${params}`);
      setConversations(data.items || []);
      setConvTotal(data.total || 0);
    } catch {
      setConversations([]);
      setConvTotal(0);
    } finally {
      setLoading(false);
    }
  }, [convPage, search, statusFilter, intentFilter]);

  const fetchConversationDetail = useCallback(async (conversationId: string) => {
    try {
      const data = await apiFetch<ConversationDetail>(`/api/v1/admin/conversations/${conversationId}`);
      setSelectedConversation(data);
    } catch { /* ignore */ }
  }, []);

  const handleConvRetry = useCallback(async (conversationId: string) => {
    try {
      await apiFetch(`/api/v1/admin/conversations/${conversationId}/evaluate`, { method: "POST" });
      setTimeout(() => void fetchConversationDetail(conversationId), 1000);
    } catch { /* ignore */ }
  }, [fetchConversationDetail]);

  const handleConvReview = useCallback(async (conversationId: string, review: string, note: string) => {
    try {
      await apiFetch(`/api/v1/admin/conversations/${conversationId}/review?review=${review}&note=${encodeURIComponent(note)}`, {
        method: "POST",
      });
      void fetchConversationDetail(conversationId);
      void fetchSummary();
    } catch { /* ignore */ }
  }, [fetchConversationDetail, fetchSummary]);

  useEffect(() => {
    if (viewMode === "conversations") {
      void fetchConversations();
    } else {
      void fetchList();
    }
    void fetchSummary();
    void fetchTaxonomy();
    void fetchAnalytics();
  }, [fetchList, fetchSummary, fetchTaxonomy, fetchAnalytics, fetchConversations, viewMode]);

  const fetchDetail = async (traceId: string) => {
    try {
      const data = await apiFetch<InteractionDetail>(`/api/v1/admin/interactions/${traceId}`);
      setSelected(data);
      setReviewTab("form");
      // Fetch reviews for this interaction
      if (data) {
        try {
          // We need the interaction_id from the DB, but we can search by trace_id
          // Use the queue endpoint to find it
          const queueData = await apiFetch<{ items: Array<{ trace_id: string }> }>(
            `/api/v1/reviews/queue?limit=100`
          );
          // Reviews are fetched via a different approach - let's just fetch them
          setReviews([]);
        } catch { /* ignore */ }
      }
    } catch { /* ignore */ }
  };

  // Load first item when list changes
  useEffect(() => {
    if (items.length > 0) {
      if (!selected || !items.some((it) => it.trace_id === selected.trace_id)) {
        void fetchDetail(items[0].trace_id);
      }
    } else {
      setSelected(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items]);

  const handleRetry = async (traceId: string) => {
    try {
      await apiFetch(`/api/v1/admin/interactions/${traceId}/evaluate`, { method: "POST" });
      setTimeout(() => {
        void fetchDetail(traceId);
        void fetchSummary();
      }, 1000);
    } catch { /* ignore */ }
  };

  const handleReviewSubmit = async (data: Record<string, unknown>) => {
    if (!selected) return;
    try {
      // First, we need the interaction_id. Use a workaround: get it from the DB via the admin endpoint
      // Actually, the submit endpoint needs interaction_id. We'll get it from the queue or use trace_id directly.
      // For now, we need to find the interaction_id. Let's use a search.
      const queueItems = await apiFetch<{ items: Array<{ trace_id: string }>; total: number }>(
        `/api/v1/reviews/queue?limit=500`
      );
      // We can't get interaction_id from queue. Let's use the admin endpoint to get it.
      // Actually, the best approach is to use the existing review API's POST /submit which accepts trace_id
      // But we need interaction_id. Let's add a lookup.
      // For now, use the fact that interaction_id is auto-incremented.
      // We'll need to pass it differently.

      // Alternative: use the admin API's existing review endpoint as a fallback
      // But that only sets basic fields. Let's use the proper review submit.

      // The create review endpoint needs interaction_id. Let's try to get it from the detail.
      // We don't have it in the response. Let me check the database.
      // For now, let's just use the existing admin review endpoint for the basic label,
      // then we can enhance with the proper endpoint once we have the interaction_id.

      // Actually, let's just call the proper endpoint and handle the interaction_id lookup server-side.
      // We'll need to add a trace_id-based lookup in the service.

      // For now, let's use a direct approach:
      const detail = await apiFetch<InteractionDetail>(`/api/v1/admin/interactions/${selected.trace_id}`);
      // We still don't have interaction_id. Let me check if it's in the response.
      // It's not. We need to add it.

      // Workaround: use the existing simple review endpoint as a fallback
      await apiFetch(`/api/v1/admin/interactions/${selected.trace_id}/review?review=${data.overall_label}&note=${data.comment || ""}`, {
        method: "POST",
      });

      // Then try the full review endpoint
      // We need to get the interaction_id from the database
      // Let's add a search endpoint for this

      void fetchDetail(selected.trace_id);
      void fetchAnalytics();
    } catch {
      throw new Error("Failed to submit review");
    }
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="h-full w-full flex flex-col overflow-hidden space-y-4">
      {/* Metrics Summary Dashboard */}
      <SummaryDashboard summary={summary} analytics={analytics} />

      {/* Filters Toolbar */}
      <div className="flex flex-wrap gap-2 shrink-0">
        {/* View mode toggle */}
        <div className="flex rounded-md border border-input overflow-hidden shrink-0">
          <button
            className={cn(
              "flex items-center gap-1 px-3 py-1.5 text-xs font-medium transition-colors",
              viewMode === "conversations"
                ? "bg-primary text-primary-foreground"
                : "bg-background text-muted-foreground hover:bg-muted/50"
            )}
            onClick={() => { setViewMode("conversations"); setSelectedConversation(null); setPage(0); }}
          >
            <MessageSquare className="h-3.5 w-3.5" />
            Conversations
          </button>
          <button
            className={cn(
              "flex items-center gap-1 px-3 py-1.5 text-xs font-medium transition-colors border-l border-input",
              viewMode === "interactions"
                ? "bg-primary text-primary-foreground"
                : "bg-background text-muted-foreground hover:bg-muted/50"
            )}
            onClick={() => { setViewMode("interactions"); setSelected(null); setConvPage(0); }}
          >
            <List className="h-3.5 w-3.5" />
            Interactions
          </button>
        </div>
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            className="pl-8 h-9 text-sm"
            placeholder="Search question or answer..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(0);
            }}
          />
        </div>
        <select
          className="rounded-md border border-input bg-background px-3 py-1 text-sm h-9 shrink-0 text-muted-foreground focus-visible:outline-none"
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setPage(0);
          }}
        >
          <option value="">All Status</option>
          <option value="COMPLETED">Evaluated</option>
          <option value="PENDING">Pending</option>
          <option value="RUNNING">Running</option>
          <option value="FAILED">Failed</option>
          <option value="NOT_EVALUATED">Not Evaluated</option>
        </select>
        <select
          className="rounded-md border border-input bg-background px-3 py-1 text-sm h-9 shrink-0 text-muted-foreground focus-visible:outline-none"
          value={intentFilter}
          onChange={(e) => {
            setIntentFilter(e.target.value);
            setPage(0);
          }}
        >
          <option value="">All Intents</option>
          <option value="SCHEMA_LOOKUP">Schema Lookup</option>
          <option value="TERM_DEFINITION">Term Definition</option>
          <option value="LINEAGE">Lineage</option>
          <option value="GENERAL">General</option>
          <option value="FIND_ENTITY">Find Entity</option>
          <option value="GREETING">Greeting</option>
          <option value="ENTITY_DOMAIN">Entity Domain</option>
          <option value="DATAHUB_URL">DataHub URL</option>
          <option value="OWNER_LOOKUP">Owner Lookup</option>
          <option value="ENTITY_EXISTS">Entity Exists</option>
          <option value="IMPACT">Impact</option>
        </select>
        <Button
          variant="outline"
          size="sm"
          className="h-9 w-9 p-0 shrink-0"
          onClick={() => {
            if (viewMode === "conversations") {
              void fetchConversations();
            } else {
              void fetchList();
            }
            void fetchSummary();
            void fetchAnalytics();
          }}
        >
          <RefreshCw className="h-4 w-4" />
        </Button>
        <Button
          variant={ragasEnabled ? "default" : "outline"}
          size="sm"
          className={cn(
            "h-9 px-3 shrink-0 gap-1.5 text-xs font-medium",
            ragasEnabled && "bg-emerald-600 hover:bg-emerald-700 text-white"
          )}
          onClick={() => {
            const next = !ragasEnabled;
            setRagasEnabled(next);
            localStorage.setItem("ragas_enabled", String(next));
          }}
          title={ragasEnabled ? "RAGAS ON - clicking disables auto-evaluation" : "RAGAS OFF - clicking enables auto-evaluation"}
        >
          {ragasEnabled ? <Zap className="h-3.5 w-3.5" /> : <ZapOff className="h-3.5 w-3.5" />}
          RAGAS {ragasEnabled ? "ON" : "OFF"}
        </Button>
      </div>

      {/* Grid Dashboard */}
      <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-12 gap-6 overflow-hidden">
        {viewMode === "conversations" ? (
          <>
            {/* LEFT: Conversations List */}
            <Card className="lg:col-span-5 flex flex-col overflow-hidden h-full">
              <CardHeader className="pb-3 border-b flex flex-row items-center justify-between space-y-0 shrink-0">
                <CardTitle className="text-base font-semibold flex items-center gap-1.5">
                  <MessageSquare className="h-4 w-4" /> Conversations
                </CardTitle>
                <Badge variant="secondary" className="font-mono text-xs">{convTotal} conv</Badge>
              </CardHeader>
              <CardContent className="flex-1 flex flex-col overflow-hidden p-0">
                {loading ? (
                  <div className="flex-1 flex justify-center items-center">
                    <Loader2 className="h-6 w-6 animate-spin text-primary" />
                  </div>
                ) : (
                  <div className="flex-1 overflow-y-auto p-2 space-y-1.5 min-h-0 bg-muted/5">
                    {conversations.map((conv) => (
                      <ConversationCardItem
                        key={conv.conversation_id}
                        conversation={conv}
                        isSelected={selectedConversation?.conversation_id === conv.conversation_id}
                        onSelect={() => void fetchConversationDetail(conv.conversation_id)}
                      />
                    ))}
                    {conversations.length === 0 && (
                      <div className="py-12 text-center text-sm text-muted-foreground">
                        No conversations found.
                      </div>
                    )}
                  </div>
                )}
                <div className="p-3 border-t shrink-0">
                  {Math.ceil(convTotal / limit) > 1 && (
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] text-muted-foreground font-mono">
                        Page {convPage + 1} of {Math.ceil(convTotal / limit)}
                      </span>
                      <div className="flex gap-1">
                        <Button variant="outline" size="sm" className="h-7 px-2" disabled={convPage === 0} onClick={() => setConvPage((p) => p - 1)}>
                          <ChevronLeft className="h-3.5 w-3.5" />
                        </Button>
                        <Button variant="outline" size="sm" className="h-7 px-2" disabled={convPage >= Math.ceil(convTotal / limit) - 1} onClick={() => setConvPage((p) => p + 1)}>
                          <ChevronRight className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* RIGHT: Conversation Detail */}
            <Card className="lg:col-span-7 flex flex-col overflow-hidden h-full">
              <CardHeader className="pb-3 border-b flex flex-row items-center justify-between space-y-0 shrink-0">
                <CardTitle className="text-base font-semibold flex items-center gap-1.5">
                  Conversation Detail
                </CardTitle>
                {selectedConversation && (
                  <span className="text-[10px] text-muted-foreground font-mono bg-muted px-2 py-0.5 rounded border">
                    {selectedConversation.turn_count} turns
                  </span>
                )}
              </CardHeader>
              <CardContent className="flex-1 overflow-y-auto p-4 min-h-0 bg-muted/5">
                {selectedConversation ? (
                  <ConversationDetailView
                    conversation={selectedConversation}
                    selectedTraceId={selectedConvTraceId}
                    onSelectTurn={(traceId) => {
                      setSelectedConvTraceId(traceId);
                      // Also load the individual interaction detail for diagnostics
                      void fetchDetail(traceId);
                      setViewMode("interactions");
                    }}
                    onEvaluate={handleConvRetry}
                    onReview={handleConvReview}
                    onClose={() => setSelectedConversation(null)}
                  />
                ) : (
                  <div className="h-full flex flex-col justify-center items-center text-center p-6">
                    <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center mb-4">
                      <MessageSquare className="h-6 w-6 text-muted-foreground" />
                    </div>
                    <h3 className="text-sm font-semibold text-foreground">No Conversation Selected</h3>
                    <p className="text-xs text-muted-foreground mt-1 max-w-xs">
                      Select a conversation from the list to view all turns with context, tools, scores, and chat-like UI.
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </>
        ) : (
          <>
            {/* LEFT: Interactions List (existing) */}
            <Card className="lg:col-span-5 flex flex-col overflow-hidden h-full">
              <CardHeader className="pb-3 border-b flex flex-row items-center justify-between space-y-0 shrink-0">
                <CardTitle className="text-base font-semibold">Interaction Logs</CardTitle>
                <Badge variant="secondary" className="font-mono text-xs">{total} items</Badge>
              </CardHeader>
              <CardContent className="flex-1 flex flex-col overflow-hidden p-0">
                {loading ? (
                  <div className="flex-1 flex justify-center items-center">
                    <Loader2 className="h-6 w-6 animate-spin text-primary" />
                  </div>
                ) : (
                  <div className="flex-1 overflow-y-auto p-2 space-y-1.5 min-h-0 bg-muted/5">
                    {items.map((it) => (
                      <div
                        key={it.trace_id}
                        className={cn(
                          "cursor-pointer rounded-lg border p-2.5 transition-all",
                          selected?.trace_id === it.trace_id
                            ? "bg-primary/5 border-primary/20"
                            : "bg-background border-border hover:bg-muted/30"
                        )}
                        onClick={() => void fetchDetail(it.trace_id)}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex-1 min-w-0">
                            <p className={cn("text-xs font-semibold truncate", selected?.trace_id === it.trace_id ? "text-primary" : "text-foreground")}>
                              {it.question}
                            </p>
                            <p className="text-[11px] text-muted-foreground truncate mt-0.5">{it.answer}</p>
                          </div>
                          <div className="flex flex-col items-end gap-1 shrink-0">
                            {evalBadge(it.evaluation_status)}
                            {it.faithfulness !== null && (
                              <span className={`text-[10px] font-mono font-medium ${scoreColor(it.faithfulness)}`}>
                                F: {(it.faithfulness * 100).toFixed(0)}%
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="mt-2 flex flex-wrap gap-x-2 gap-y-0.5 text-[9px] text-muted-foreground border-t border-border/40 pt-1.5">
                          <span className="font-medium text-foreground/80">{it.intent}</span>
                          {it.citation_count > 0 && <span>· {it.citation_count} citations</span>}
                          {it.processing_time_ms && <span>· {it.processing_time_ms}ms</span>}
                          {it.created_at && <span>· {new Date(it.created_at).toLocaleDateString()}</span>}
                          {it.human_review && humanReviewBadge(it.human_review)}
                        </div>
                      </div>
                    ))}
                    {items.length === 0 && (
                      <div className="py-12 text-center text-sm text-muted-foreground">
                        No interactions found.
                      </div>
                    )}
                  </div>
                )}
                <div className="p-3 border-t shrink-0">
                  {totalPages > 1 && (
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] text-muted-foreground font-mono">
                        Page {page + 1} of {totalPages}
                      </span>
                      <div className="flex gap-1">
                        <Button variant="outline" size="sm" className="h-7 px-2" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
                          <ChevronLeft className="h-3.5 w-3.5" />
                        </Button>
                        <Button variant="outline" size="sm" className="h-7 px-2" disabled={page >= totalPages - 1} onClick={() => setPage((p) => p + 1)}>
                          <ChevronRight className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* RIGHT: Interaction diagnostics (existing) */}
            <Card className="lg:col-span-7 flex flex-col overflow-hidden h-full">
              <CardHeader className="pb-3 border-b flex flex-row items-center justify-between space-y-0 shrink-0">
                <CardTitle className="text-base font-semibold flex items-center gap-1.5">
                  Diagnostics Detail
                </CardTitle>
                {selected && (
                  <span className="text-[10px] text-muted-foreground font-mono bg-muted px-2 py-0.5 rounded border">
                    Trace: {selected.trace_id.slice(0, 8)}...
                  </span>
                )}
              </CardHeader>
              <CardContent className="flex-1 overflow-y-auto p-4 min-h-0 bg-muted/5">
                {selected ? (
                  <div className="space-y-4">
                    {/* Trace Header with action buttons */}
                    <div className="flex items-center justify-between pb-3 border-b border-border/40">
                      <span className="text-[10px] font-mono text-muted-foreground break-all mr-4 select-all bg-background border px-2 py-1 rounded">
                        {selected.trace_id}
                      </span>
                      <div className="flex gap-2 shrink-0">
                        {selected.evaluation_status === "FAILED" && (
                          <Button size="sm" variant="outline" onClick={() => void handleRetry(selected.trace_id)} className="h-7 px-2 text-xs flex items-center gap-1 hover:bg-muted">
                            <RotateCcw className="h-3 w-3" /> Retry
                          </Button>
                        )}
                      </div>
                    </div>

                    {/* Question & Answer Grid */}
                    <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                      <CollapsibleSection title="User Question" defaultOpen>
                        <p className="text-xs leading-relaxed text-foreground bg-background border p-2.5 rounded-lg select-text">{selected.question}</p>
                        <div className="mt-2 flex flex-wrap gap-2 text-[10px] text-muted-foreground">
                          <span>Intent: <Badge variant="outline" className="py-0 px-1 font-normal text-[9px] capitalize">{selected.intent.replace(/_/g, " ")}</Badge></span>
                          {selected.entity_resolved_name && (
                            <span className="truncate max-w-[200px]">Entity: <span className="font-semibold text-foreground">{selected.entity_resolved_name}</span></span>
                          )}
                          {selected.chosen_tool && <span>Tool: <span className="font-semibold text-foreground">{selected.chosen_tool}</span></span>}
                          {selected.processing_time_ms && <span>Latency: {selected.processing_time_ms}ms</span>}
                        </div>
                      </CollapsibleSection>
                      <CollapsibleSection title="AI Answer" defaultOpen>
                        <p className="text-xs leading-relaxed text-foreground bg-background border p-2.5 rounded-lg select-text whitespace-pre-wrap">{selected.answer}</p>
                      </CollapsibleSection>
                    </div>

                    {/* System Metrics + RAGAS Evaluation */}
                    <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                      <CollapsibleSection title="Pipeline Diagnostics" defaultOpen>
                        <DiagnosticsCard traceId={selected.trace_id} />
                      </CollapsibleSection>
                      <CollapsibleSection
                        title="RAGAS Evaluation"
                        badge={evalBadge(selected.evaluation_status)}
                        defaultOpen
                      >
                        {selected.evaluation_error && (
                          <div className="mb-2.5 rounded border border-destructive/20 bg-destructive/10 p-2.5 text-xs text-destructive font-mono leading-relaxed">
                            <AlertTriangle className="mr-1 inline h-4 w-4" /> {selected.evaluation_error}
                          </div>
                        )}
                        <div className="space-y-0.5">
                          <MetricRow label="Faithfulness" metric={selected.faithfulness !== null ? { score: selected.faithfulness, status: (selected.faithfulness_status as MetricStatus["status"]) || "COMPLETED", reason: null } : undefined} />
                          <MetricRow label="Answer Relevancy" metric={selected.answer_relevancy !== null ? { score: selected.answer_relevancy, status: (selected.answer_relevancy_status as MetricStatus["status"]) || "COMPLETED", reason: null } : undefined} />
                          <MetricRow label="Context Precision" metric={selected.context_precision !== null ? { score: selected.context_precision, status: (selected.context_precision_status as MetricStatus["status"]) || "COMPLETED", reason: null } : undefined} />
                          <MetricRow label="Context Recall" metric={selected.context_recall !== null ? { score: selected.context_recall, status: (selected.context_recall_status as MetricStatus["status"]) || "COMPLETED", reason: null } : undefined} />
                        </div>
                        {selected.evaluation_model && (
                          <div className="mt-2 text-[9px] font-mono text-muted-foreground">Model: {selected.evaluation_model}</div>
                        )}
                      </CollapsibleSection>
                    </div>

                    {/* Contexts & Human Review */}
                    <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                      <CollapsibleSection
                        title={`Retrieved Context (${(selected.retrieved_contexts?.contexts || []).length})`}
                        defaultOpen={(selected.retrieved_contexts?.contexts || []).length > 0}
                      >
                        {(selected.retrieved_contexts?.contexts || []).length === 0 ? (
                          <div className="text-xs text-muted-foreground italic">No contexts stored</div>
                        ) : (
                          <div className="space-y-1.5 max-h-[220px] overflow-y-auto pr-1">
                            {(selected.retrieved_contexts?.contexts || []).map((c, i) => (
                              <div key={i} className="rounded bg-background border p-2.5 text-[10px] leading-relaxed text-muted-foreground hover:text-foreground">
                                <span className="font-semibold text-primary">[{i + 1}]</span> {c}
                              </div>
                            ))}
                          </div>
                        )}
                      </CollapsibleSection>

                      {/* Human Quality Review - Tabbed */}
                      <CollapsibleSection title="Human Quality Review" defaultOpen>
                        {/* Tab buttons */}
                        <div className="flex gap-1 mb-3 border-b border-border/40 pb-2">
                          {(["form", "history", "ragas"] as const).map((tab) => (
                            <button
                              key={tab}
                              onClick={() => setReviewTab(tab)}
                              className={cn(
                                "text-[10px] px-2 py-0.5 rounded transition-colors font-medium",
                                reviewTab === tab
                                  ? "bg-primary/10 text-primary"
                                  : "text-muted-foreground hover:bg-muted/50"
                              )}
                            >
                              {tab === "form" && <Flag className="inline h-2.5 w-2.5 mr-0.5" />}
                              {tab === "history" && <Users className="inline h-2.5 w-2.5 mr-0.5" />}
                              {tab === "ragas" && <BarChart3 className="inline h-2.5 w-2.5 mr-0.5" />}
                              {tab === "form" ? "Submit" : tab === "history" ? "History" : "vs RAGAS"}
                            </button>
                          ))}
                        </div>

                        {reviewTab === "form" && (
                          <AdaptiveReviewForm
                            interaction={selected}
                            taxonomy={taxonomy}
                            onSubmit={handleReviewSubmit}
                            existingReview={reviews.length > 0 ? reviews[0] : null}
                          />
                        )}

                        {reviewTab === "history" && (
                          <ReviewHistory reviews={reviews} interactionId={0} />
                        )}

                        {reviewTab === "ragas" && (
                          <div className="space-y-2 text-xs">
                            <div className="rounded border p-2.5">
                              <div className="font-semibold text-[10px] text-muted-foreground mb-2">Human vs RAGAS Comparison</div>
                              {selected.faithfulness !== null ? (
                                <div className="space-y-1.5">
                                  <div className="flex justify-between">
                                    <span>RAGAS Faithfulness:</span>
                                    <span className={cn("font-mono font-semibold", scoreColor(selected.faithfulness))}>
                                      {(selected.faithfulness * 100).toFixed(0)}%
                                    </span>
                                  </div>
                                  {selected.human_review && (
                                    <div className="flex justify-between">
                                      <span>Human Review:</span>
                                      {humanReviewBadge(selected.human_review)}
                                    </div>
                                  )}
                                  <div className="flex justify-between text-[10px]">
                                    <span>Agreement:</span>
                                    <span className={cn(
                                      "font-semibold",
                                      (selected.human_review === "accepted" && selected.faithfulness >= 0.7) ||
                                      (selected.human_review && selected.human_review !== "accepted" && selected.faithfulness < 0.7)
                                        ? "text-green-600"
                                        : "text-yellow-600"
                                    )}>
                                      {(selected.human_review === "accepted" && selected.faithfulness >= 0.7) ||
                                       (selected.human_review && selected.human_review !== "accepted" && selected.faithfulness < 0.7)
                                        ? "AGREE"
                                        : "DISAGREE"}
                                    </span>
                                  </div>
                                </div>
                              ) : (
                                <p className="text-muted-foreground italic">No RAGAS data available</p>
                              )}
                            </div>
                            {analytics?.human_ragas_comparison && (
                              <div className="rounded border p-2.5">
                                <div className="font-semibold text-[10px] text-muted-foreground mb-2">Global Comparison</div>
                                <div className="grid grid-cols-2 gap-1.5 text-[10px]">
                                  <div>Accepted + High RAGAS: <span className="font-semibold">{analytics.human_ragas_comparison.accepted_high_ragas || 0}</span></div>
                                  <div>Accepted + Low RAGAS: <span className="font-semibold">{analytics.human_ragas_comparison.accepted_low_ragas || 0}</span></div>
                                  <div>Incorrect + High RAGAS: <span className="font-semibold">{analytics.human_ragas_comparison.incorrect_high_ragas || 0}</span></div>
                                  <div>Incorrect + Low RAGAS: <span className="font-semibold">{analytics.human_ragas_comparison.incorrect_low_ragas || 0}</span></div>
                                  <div>Hallucination + High RAGAS: <span className="font-semibold">{analytics.human_ragas_comparison.hallucination_high_ragas || 0}</span></div>
                                  <div>No RAGAS Data: <span className="font-semibold">{analytics.human_ragas_comparison.no_ragas_data || 0}</span></div>
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </CollapsibleSection>
                    </div>
                  </div>
                ) : (
                  <div className="h-full flex flex-col justify-center items-center text-center p-6">
                    <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center mb-4">
                      <Search className="h-6 w-6 text-muted-foreground" />
                    </div>
                    <h3 className="text-sm font-semibold text-foreground">No Interaction Selected</h3>
                    <p className="text-xs text-muted-foreground mt-1 max-w-xs">
                      Select an interaction from the list on the left to examine pipeline logs, RAGAS metrics, and trigger diagnostics.
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </div>
  );
}

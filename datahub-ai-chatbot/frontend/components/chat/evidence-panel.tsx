"use client";
import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Image from "next/image";
import {
  X,
  ExternalLink,
  Globe,
  Table,
  GitBranch,
  Tag,
  FileText,
  Layers,
  Loader2,
  Database,
  Key as KeyIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";
import type { EntityItem } from "@/lib/types";

interface SchemaField {
  field_path: string;
  name: string;
  type: string;
  description: string | null;
  nullable: boolean;
  is_primary_key: boolean;
}

interface LineageNode {
  urn: string;
  name: string;
  entity_type?: string;
  platform?: string;
}

interface EntityDetail {
  urn: string;
  entity_type: string;
  name: string;
  display_name: string | null;
  description: string | null;
  platform: string | null;
  environment: string | null;
  domain: string | null;
  datahub_url: string | null;
  schema_fields: SchemaField[];
  upstreams: LineageNode[];
  downstreams: LineageNode[];
}

interface EvidencePanelProps {
  entity: EntityItem | null;
  isOpen: boolean;
  onClose: () => void;
  onEntityClick?: (entity: EntityItem) => void;
}

function parseEntityType(urn: string): string {
  const match = urn.match(/^urn:li:([^:(]+)/i);
  if (match) {
    const t = match[1].toLowerCase();
    if (t === "dataset") return "dataset";
    if (t === "dashboard") return "dashboard";
    if (t === "glossaryterm") return "glossary_term";
    if (t === "chart") return "chart";
    if (t === "dataflow") return "dataflow";
    if (t === "datajob") return "datajob";
    if (t === "container") return "container";
    if (t === "tag") return "tag";
    if (t === "mlmodel") return "mlmodel";
    if (t === "corpuser") return "corpuser";
    if (t === "dataplatform") return "dataplatform";
    return t;
  }
  return "entity";
}

const TYPE_LABELS: Record<string, string> = {
  dataset: "Dataset",
  dashboard: "Dashboard",
  glossary_term: "Glossary Term",
  chart: "Chart",
  dataflow: "Data Flow",
  datajob: "Data Job",
  container: "Container",
  tag: "Tag",
  mlmodel: "ML Model",
  entity: "Entity",
};

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
      {children}
    </p>
  );
}

function MetaRow({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="shrink-0 text-muted-foreground">{label}:</span>
      {value ? (
        <span className="font-medium">{value}</span>
      ) : (
        <span className="italic text-muted-foreground/60">Chưa có metadata</span>
      )}
    </div>
  );
}

export function EvidencePanel({ entity, isOpen, onClose, onEntityClick }: EvidencePanelProps) {
  const [detail, setDetail] = useState<EntityDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !entity?.urn) {
      setDetail(null);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    apiFetch<EntityDetail>(`/api/v1/search/entity?urn=${encodeURIComponent(entity.urn)}`)
      .then((data) => {
        setDetail(data);
      })
      .catch((err) => {
        console.error("Failed to fetch entity details:", err);
        setError((err as Error).message || "Không thể tải chi tiết metadata");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [entity?.urn, isOpen]);

  if (!entity) return null;

  const entityType = entity.entity_type || parseEntityType(entity.urn);
  const typeLabel = TYPE_LABELS[entityType] || "Entity";
  const datahubUrl =
    entity.url ||
    `https://datahub.vinfastauto.com/api/v2/entities/${encodeURIComponent(entity.urn)}`;

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop — both mobile & desktop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40 bg-black/30"
            onClick={onClose}
          />
          {/* Panel */}
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 28, stiffness: 220 }}
            className="fixed inset-y-0 right-0 z-50 flex w-full flex-col border-l bg-card shadow-xl md:w-[420px]"
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b px-5 py-4">
              <div className="flex items-center gap-3 min-w-0">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-muted">
                  <Image
                    src="/datahub_logo_no_text.svg"
                    alt="DataHub"
                    width={28}
                    height={28}
                    className="object-contain"
                  />
                </span>
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold">{detail?.display_name || detail?.name || entity.name}</p>
                  <p className="text-[11px] text-muted-foreground">{typeLabel}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                aria-label="Đóng"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto px-5 py-4">
              <div className="space-y-6">
                {/* Overview */}
                <section>
                  <SectionLabel>Tổng quan</SectionLabel>
                  <div className="space-y-2.5">
                    {(detail?.description || entity.description) ? (
                      <div>
                        <p className="mb-0.5 text-xs font-medium text-muted-foreground">Mô tả</p>
                        <p className="text-sm leading-relaxed">{detail?.description || entity.description}</p>
                      </div>
                    ) : (
                      <MetaRow label="Mô tả" />
                    )}
                    <MetaRow label="Platform" value={detail?.platform || entity.platform} />
                    <MetaRow label="Environment" value={detail?.environment || entity.environment} />
                    <MetaRow label="Domain" value={detail?.domain || entity.domain} />
                  </div>
                </section>

                {/* Schema */}
                <section>
                  <SectionLabel>Schema {detail?.schema_fields && detail.schema_fields.length > 0 && `(${detail.schema_fields.length})`}</SectionLabel>
                  {loading ? (
                    <div className="flex items-center gap-2 rounded-lg border p-3 bg-muted/10 text-sm text-muted-foreground">
                      <Loader2 className="h-4 w-4 animate-spin shrink-0" />
                      <span>Đang tải schema...</span>
                    </div>
                  ) : error ? (
                    <div className="flex items-center gap-2 rounded-lg border border-destructive/20 p-3 bg-destructive/5 text-sm text-destructive">
                      <Table className="h-4 w-4 shrink-0 text-destructive" />
                      <span>{error}</span>
                    </div>
                  ) : detail?.schema_fields && detail.schema_fields.length > 0 ? (
                    <div className="rounded-lg border bg-muted/10 p-1 divide-y divide-border/50 max-h-[300px] overflow-y-auto">
                      {detail.schema_fields.map((f, i) => (
                        <div key={i} className="p-2.5 flex flex-col gap-0.5 hover:bg-muted/30">
                          <div className="flex items-start justify-between gap-2">
                            <span className="font-mono text-xs font-semibold text-foreground break-all flex items-center gap-1">
                              {f.is_primary_key && <KeyIcon className="h-3.5 w-3.5 text-yellow-500 shrink-0" />}
                              {f.name}
                            </span>
                            <span className="inline-flex shrink-0 items-center rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-mono font-medium text-primary">
                              {f.type}
                            </span>
                          </div>
                          {f.description && (
                            <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{f.description}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="rounded-lg border bg-muted/30 p-3">
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Table className="h-4 w-4 shrink-0" />
                        <span className="italic">Chưa có thông tin schema</span>
                      </div>
                    </div>
                  )}
                </section>

                {/* Lineage */}
                <section>
                  <SectionLabel>Dòng dữ liệu (Lineage)</SectionLabel>
                  {loading ? (
                    <div className="flex items-center gap-2 rounded-lg border p-3 bg-muted/10 text-sm text-muted-foreground">
                      <Loader2 className="h-4 w-4 animate-spin shrink-0" />
                      <span>Đang tải lineage...</span>
                    </div>
                  ) : error ? (
                    <div className="flex items-center gap-2 rounded-lg border border-destructive/20 p-3 bg-destructive/5 text-sm text-destructive">
                      <GitBranch className="h-4 w-4 shrink-0 text-destructive" />
                      <span>{error}</span>
                    </div>
                  ) : detail && (detail.upstreams.length > 0 || detail.downstreams.length > 0) ? (
                    <div className="space-y-4">
                      {/* Upstreams */}
                      {detail.upstreams.length > 0 && (
                        <div className="space-y-1.5">
                          <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                            Upstream ({detail.upstreams.length})
                          </p>
                          <div className="rounded-lg border bg-muted/10 p-1.5 space-y-1">
                            {detail.upstreams.map((node) => (
                              <button
                                key={node.urn}
                                onClick={() => onEntityClick?.({ urn: node.urn, name: node.name, entity_type: node.entity_type || "dataset", platform: node.platform })}
                                className="w-full flex items-center justify-between gap-2 p-2 rounded hover:bg-muted text-left transition-colors"
                              >
                                <span className="text-xs font-medium text-foreground truncate block max-w-[220px]">
                                  {node.name}
                                </span>
                                <div className="flex items-center gap-1 shrink-0">
                                  {node.platform && (
                                    <span className="inline-flex rounded px-1.5 py-0.5 text-[9px] font-mono font-medium bg-muted/80 text-muted-foreground capitalize">
                                      {node.platform}
                                    </span>
                                  )}
                                  <span className="inline-flex rounded px-1.5 py-0.5 text-[9px] font-mono font-medium bg-primary/10 text-primary capitalize">
                                    {node.entity_type || "dataset"}
                                  </span>
                                </div>
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Downstreams */}
                      {detail.downstreams.length > 0 && (
                        <div className="space-y-1.5">
                          <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                            Downstream ({detail.downstreams.length})
                          </p>
                          <div className="rounded-lg border bg-muted/10 p-1.5 space-y-1">
                            {detail.downstreams.map((node) => (
                              <button
                                key={node.urn}
                                onClick={() => onEntityClick?.({ urn: node.urn, name: node.name, entity_type: node.entity_type || "dataset", platform: node.platform })}
                                className="w-full flex items-center justify-between gap-2 p-2 rounded hover:bg-muted text-left transition-colors"
                              >
                                <span className="text-xs font-medium text-foreground truncate block max-w-[220px]">
                                  {node.name}
                                </span>
                                <div className="flex items-center gap-1 shrink-0">
                                  {node.platform && (
                                    <span className="inline-flex rounded px-1.5 py-0.5 text-[9px] font-mono font-medium bg-muted/80 text-muted-foreground capitalize">
                                      {node.platform}
                                    </span>
                                  )}
                                  <span className="inline-flex rounded px-1.5 py-0.5 text-[9px] font-mono font-medium bg-primary/10 text-primary capitalize">
                                    {node.entity_type || "dataset"}
                                  </span>
                                </div>
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="rounded-lg border bg-muted/30 p-3">
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <GitBranch className="h-4 w-4 shrink-0" />
                        <span className="italic">Chưa có lineage metadata</span>
                      </div>
                    </div>
                  )}
                </section>

                {/* Identifier */}
                <section>
                  <SectionLabel>Identifier</SectionLabel>
                  <div className="rounded-lg border bg-muted/30 p-3">
                    <p className="mb-1 text-xs font-medium text-muted-foreground">URN</p>
                    <p className="break-all font-mono text-xs text-foreground">{entity.urn}</p>
                  </div>
                </section>
              </div>
            </div>

            {/* Footer */}
            <div className="border-t px-5 py-3">
              <Button
                variant="outline"
                className="w-full"
                onClick={() => window.open(datahubUrl, "_blank")}
              >
                <ExternalLink className="mr-2 h-4 w-4" />
                Mở trong DataHub
              </Button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

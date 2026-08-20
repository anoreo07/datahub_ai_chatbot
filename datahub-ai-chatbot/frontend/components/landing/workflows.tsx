"use client";

import {
  ArrowRight,
  BarChart,
  BookOpen,
  Code2,
  Database,
  FileText,
  GitBranch,
  Image as ImageIcon,
  Search,
  Table,
} from "lucide-react";

import { LandingContainer, Reveal, SectionHeading } from "@/components/landing/shared";

/* Lightweight mock UIs (pure markup, no images/video). */

function MockFindDataset() {
  return (
    <div className="flex w-full flex-col gap-3 rounded-lg border border-border bg-card p-3">
      <div className="flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-2">
        <Search className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
        <span className="text-xs text-muted-foreground">sales dataset in logistics…</span>
      </div>
      <div className="flex items-center gap-2 text-xs">
        <span className="rounded-full bg-accent px-2 py-0.5 font-medium">fact_sales_order</span>
        <span className="text-muted-foreground">· 2 more</span>
      </div>
    </div>
  );
}

function MockSchema() {
  return (
    <div className="w-full rounded-lg border border-border bg-card p-3">
      <div className="grid grid-cols-2 gap-1.5">
        {["warehouse_id", "warehouse_name", "city", "capacity"].map((f) => (
          <div key={f} className="flex items-center gap-1.5 rounded-md border border-border bg-background px-2 py-1.5">
            <Table className="h-3 w-3 text-primary" aria-hidden="true" />
            <span className="truncate text-[11px] font-medium">{f}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function MockLineage() {
  return (
    <div className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-border bg-card p-4">
      <span className="rounded-md border border-border bg-background px-2 py-1 text-[10px] font-medium">staging.raw</span>
      <ArrowRight className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
      <span className="rounded-md border border-primary/40 bg-accent px-2 py-1 text-[10px] font-semibold text-foreground">dim_warehouse</span>
      <ArrowRight className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
      <span className="rounded-md border border-border bg-background px-2 py-1 text-[10px] font-medium">fact_sales</span>
    </div>
  );
}

function MockQuality() {
  return (
    <div className="w-full rounded-lg border border-border bg-card p-3">
      <div className="mb-2 flex items-center justify-between text-[11px]">
        <span className="font-medium">Quality score</span>
        <span className="font-semibold text-success">86 / 100</span>
      </div>
      <div className="flex h-2 w-full overflow-hidden rounded-full bg-border" aria-hidden="true">
        <div className="h-full w-[55%] rounded-full bg-success" />
        <div className="h-full w-[30%] rounded-full bg-warning" />
      </div>
    </div>
  );
}

function MockSql() {
  return (
    <div className="w-full rounded-lg border border-border bg-card p-3">
      <div className="flex items-center gap-1.5 border-b border-border pb-2 text-[11px] font-medium">
        <Code2 className="h-3 w-3 text-primary" aria-hidden="true" />
        SQL
      </div>
      <pre className="mt-2 overflow-x-auto text-[11px] leading-relaxed text-foreground">
        {`SELECT warehouse_id,\n  SUM(quantity)\nFROM fact_sales_order\n…`}
      </pre>
    </div>
  );
}

function MockGlossary() {
  return (
    <div className="w-full rounded-lg border border-border bg-card p-3">
      <div className="mb-2 flex items-center gap-1.5">
        <BookOpen className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
        <span className="text-[11px] font-medium">Glossary</span>
      </div>
      <div className="rounded-md border border-border bg-background px-2 py-1.5 text-[11px]">
        <span className="font-semibold">Warehouse ID</span>
        <span className="text-muted-foreground"> — unique identifier of a warehouse</span>
      </div>
    </div>
  );
}

function MockDocument() {
  return (
    <div className="w-full rounded-lg border border-border bg-card p-3">
      <div className="flex items-start gap-2">
        <FileText className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
        <div className="flex flex-col gap-1.5">
          <span className="text-[11px] font-medium">sales_etl docs</span>
          <span className="h-1.5 w-24 rounded-full bg-border" />
          <span className="h-1.5 w-16 rounded-full bg-border" />
        </div>
      </div>
    </div>
  );
}

function MockImage() {
  return (
    <div className="flex w-full flex-col gap-2 rounded-lg border border-border bg-card p-3">
      <div className="flex h-14 w-full items-center justify-center rounded-md border border-dashed border-border bg-muted text-muted-foreground">
        <ImageIcon className="h-5 w-5" aria-hidden="true" />
      </div>
      <span className="text-[11px] text-muted-foreground">Diagram uploaded</span>
    </div>
  );
}

const WORKFLOWS = [
  { icon: Database, title: "Find a dataset", mock: <MockFindDataset /> },
  { icon: Table, title: "Understand a field", mock: <MockSchema /> },
  { icon: GitBranch, title: "Explore lineage", mock: <MockLineage /> },
  { icon: BarChart, title: "Check data quality", mock: <MockQuality /> },
  { icon: Code2, title: "Generate SQL", mock: <MockSql /> },
  { icon: BookOpen, title: "Understand glossary terms", mock: <MockGlossary /> },
  { icon: FileText, title: "Analyze documents", mock: <MockDocument /> },
  { icon: ImageIcon, title: "Ask about screenshots", mock: <MockImage /> },
];

export function Workflows() {
  return (
    <section id="workflows" className="scroll-mt-20 border-y border-border bg-[#f7f7f8] py-20 sm:py-28">
      <LandingContainer>
        <Reveal>
          <SectionHeading
            eyebrow="Workflows"
            title="One platform, many data workflows"
            description="Instead of opening six different tools, your team can ask about any of these — and V-DataAtlas pulls the DataHub metadata to answer."
          />
        </Reveal>

        <div className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {WORKFLOWS.map((w, i) => (
            <Reveal key={w.title} delay={(i % 4) * 0.06}>
              <div className="group flex h-full flex-col gap-4 rounded-xl border border-border bg-card p-4 shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-md">
                <div className="flex aspect-[3/2] w-full items-center justify-center rounded-lg bg-[#fafafa] p-3">
                  {w.mock}
                </div>
                <div className="flex items-center gap-2">
                  <w.icon className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
                  <h3 className="text-sm font-semibold tracking-tight text-foreground">{w.title}</h3>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </LandingContainer>
    </section>
  );
}
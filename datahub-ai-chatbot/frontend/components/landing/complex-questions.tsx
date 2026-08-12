"use client";

import { cn } from "@/lib/utils";
import {
  ArrowRight,
  BookOpen,
  Database,
  GitBranch,
  Link2,
  MessageSquareText,
  Bot,
  Layers,
  User,
} from "lucide-react";

import { LandingContainer, Reveal, SectionHeading } from "@/components/landing/shared";

const REASON_STEPS = [
  { icon: MessageSquareText, label: "Understand intent" },
  { icon: Link2, label: "Find relevant entities" },
  { icon: GitBranch, label: "Connect metadata" },
  { icon: Bot, label: "Answer" },
];

const TYPE_CHIPS = [
  { label: "Dataset", icon: Database },
  { label: "Schema", icon: Layers },
  { label: "Glossary", icon: BookOpen },
  { label: "Ownership", icon: User },
  { label: "Lineage", icon: GitBranch },
  { label: "Domain", icon: Layers },
];

export function ComplexQuestions() {
  return (
    <section id="complex" className="scroll-mt-20 py-20 sm:py-28">
      <LandingContainer>
        <Reveal>
          <SectionHeading
            eyebrow="Reasoning"
            title="Built for complex questions"
            description="A single question can span a dataset, its schema, glossary terms, owner, domain, and lineage. DataAtlas resolves them all and answers in one coherent response."
          />
        </Reveal>

        {/* Question */}
        <Reveal delay={0.1} className="mt-14">
          <div className="mx-auto max-w-3xl rounded-xl border border-border bg-card p-5 shadow-sm sm:p-6">
            <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
              <MessageSquareText className="h-4 w-4 text-primary" aria-hidden="true" />
              Example question
            </div>
            <p className="mt-3 text-base leading-relaxed text-foreground sm:text-lg">
              “Hãy phân tích dataset <span className="font-semibold text-primary">fact_sales_order</span>:
              thống kê schema, cho biết owner và domain, glossary term của các field chính,
              upstream/downstream lineage — và dataset có liên quan không?”
            </p>
          </div>
        </Reveal>

        {/* High-level reasoning, NOT chain-of-thought */}
        <Reveal delay={0.18} className="mt-10">
          <div className="mx-auto max-w-3xl">
            <p className="mb-3 text-center text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              High-level reasoning steps
            </p>
            <ol className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {REASON_STEPS.map((s, i) => (
                <li key={s.label} className="relative flex flex-col items-center gap-2 rounded-lg border border-border bg-card p-4 text-center shadow-sm">
                  <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent text-foreground">
                    <s.icon className="h-4 w-4" aria-hidden="true" />
                  </span>
                  <span className="text-xs font-semibold text-foreground">{s.label}</span>
                  {!((i + 1) % 2 === 0 || i === REASON_STEPS.length - 1) && (
                    <ArrowRight
                      className="absolute -right-3 top-1/2 hidden h-4 w-4 -translate-y-1/2 text-primary sm:block"
                      aria-hidden="true"
                    />
                  )}
                </li>
              ))}
            </ol>
          </div>
        </Reveal>

        {/* Metadata types all connected in one answer */}
        <Reveal delay={0.26} className="mt-12">
          <div className="mx-auto flex max-w-3xl flex-col items-center gap-4">
            <p className="text-xs font-medium text-muted-foreground">One answer connects</p>
            <div className="flex flex-wrap items-center justify-center gap-2">
              {TYPE_CHIPS.map((c) => (
                <span
                  key={c.label}
                  className={cn(
                    "inline-flex items-center gap-1.5 rounded-lg border bg-card px-2.5 py-1.5 text-xs font-medium text-foreground shadow-sm",
                    "border-primary/25"
                  )}
                >
                  <c.icon className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                  {c.label}
                </span>
              ))}
            </div>
            <ArrowRight className="h-5 w-5 rotate-90 text-primary" aria-hidden="true" />
            <div className="w-full rounded-xl border border-primary/30 bg-accent p-5 text-sm leading-relaxed text-foreground shadow-sm">
              <p>
                <span className="font-semibold">Answer:</span> fact_sales_order thuộc domain{" "}
                <span className="font-medium text-primary">Sales</span>, do team{" "}
                <span className="font-medium text-primary">Data Platform</span> sở hữu. Schema gồm 12 fields,
                trong đó warehouse_id (glossary: Warehouse ID) join với dim_warehouse. Dataset nằm giữa
                lineage từ staging.ebs_orders → fact_sales_order → mart_sales_daily.
              </p>
            </div>
          </div>
        </Reveal>
      </LandingContainer>
    </section>
  );
}
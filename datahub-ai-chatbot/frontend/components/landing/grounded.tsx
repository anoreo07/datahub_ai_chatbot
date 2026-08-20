"use client";

import { BookOpen, Database, GitBranch, Link2, Table, Layers } from "lucide-react";

import { LandingContainer, Reveal, SectionHeading } from "@/components/landing/shared";

const REFERENCES = [
  { urn: "urn:li:dataset:…fact_sales_order", label: "fact_sales_order", icon: Database },
  { urn: "urn:li:schemaField:…warehouse_id", label: "warehouse_id (schema)", icon: Table },
  { urn: "urn:li:glossaryTerm:…Warehouse ID", label: "Warehouse ID (glossary)", icon: BookOpen },
  { urn: "urn:li:relationship:…upstream", label: "staging.ebs_orders (upstream)", icon: GitBranch },
  { urn: "urn:li:domain:…Sales", label: "Sales (domain)", icon: Layers },
];

export function Grounded() {
  return (
    <section id="grounded" className="scroll-mt-20 border-y border-border bg-[#f7f7f8] py-20 sm:py-28">
      <LandingContainer>
        <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-16">
          <Reveal>
            <SectionHeading
              align="left"
              eyebrow="Grounded answers"
              title="Grounded in your metadata"
              description="V-DataAtlas doesn't guess. Answers are built from the actual metadata in your DataHub — with source entities cited right in the response, so you can verify every claim."
            />
            <div className="mt-6 flex flex-col gap-3">
              {[
                "Every answer references the real DataHub entities it came from",
                "Citations link back to datasets, fields, glossary terms, owners, and lineage",
                "No fabricated URNs, no invented field names — only that grounded metadata",
              ].map((t) => (
                <p key={t} className="flex items-start gap-2.5 text-sm leading-relaxed text-muted-foreground">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" aria-hidden="true" />
                  {t}
                </p>
              ))}
            </div>
          </Reveal>

          <Reveal delay={0.15}>
            <div className="rounded-xl border border-border bg-card p-5 shadow-sm sm:p-6">
              <div className="mb-4 flex items-center justify-between">
                <span className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  <Link2 className="h-4 w-4 text-primary" aria-hidden="true" />
                  Source entities
                </span>
                <span className="rounded-full bg-success/10 px-2 py-0.5 text-[11px] font-medium text-success">
                  Verified · DataHub
                </span>
              </div>
              <ul className="flex flex-col gap-2">
                {REFERENCES.map((r) => (
                  <li
                    key={r.urn}
                    className="group flex items-center gap-3 rounded-lg border border-border bg-background px-3 py-2.5 transition-colors hover:border-primary/40"
                  >
                    <r.icon className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
                    <span className="min-w-0 flex-1 truncate text-sm font-medium text-foreground">
                      {r.label}
                    </span>
                    <code className="hidden shrink-0 truncate rounded-md bg-muted px-2 py-0.5 text-[10px] text-muted-foreground sm:block">
                      {r.urn}
                    </code>
                  </li>
                ))}
              </ul>
              <p className="mt-4 text-center text-xs text-muted-foreground">
                Click a citation to jump to the entity in your DataHub.
              </p>
            </div>
          </Reveal>
        </div>
      </LandingContainer>
    </section>
  );
}
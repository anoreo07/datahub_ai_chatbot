"use client";

import {
  ArrowDown,
  ArrowRight,
  Database,
  Lightbulb,
  Link2,
  MessageSquareText,
  Bot,
} from "lucide-react";

import { LandingContainer, Reveal, SectionHeading } from "@/components/landing/shared";

const STEPS = [
  {
    icon: MessageSquareText,
    title: "User question",
    description: "You ask in natural language, with follow-ups and context from the whole thread.",
  },
  {
    icon: Lightbulb,
    title: "Understand intent",
    description: "DataAtlas classifies what you need — find, describe, explain, generate SQL, or analyze.",
  },
  {
    icon: Link2,
    title: "Resolve entities & context",
    description: "Dataset, fields, owners, glossary terms, domains are resolved from your question.",
  },
  {
    icon: Database,
    title: "Retrieve DataHub metadata",
    description: "Grounded metadata is fetched from your DataHub catalog — schema, lineage, quality.",
  },
  {
    icon: Bot,
    title: "Generate grounded answer",
    description: "An answer is assembled with citations back to the real DataHub entities.",
  },
];

export function QuestionFlow() {
  return (
    <section id="how-it-works" className="scroll-mt-20 py-20 sm:py-28">
      <LandingContainer>
        <Reveal>
          <SectionHeading
            eyebrow="How it works"
            title="From question to data context"
            description="DataAtlas connects your question to DataHub metadata, step by step — then answers with the context it found."
          />
        </Reveal>

        <div className="mt-14 flex flex-col gap-6 lg:flex-row lg:items-stretch">
          {STEPS.map((s, i) => {
            const isLast = i === STEPS.length - 1;
            return (
              <Reveal key={s.title} delay={i * 0.08} className="flex-1">
                <div className="relative flex h-full flex-col gap-3 rounded-xl border border-border bg-card p-5 shadow-sm">
                  <div className="flex items-center justify-between">
                    <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent text-foreground">
                      <s.icon className="h-5 w-5" aria-hidden="true" />
                    </span>
                    <span className="font-display text-2xl text-primary/20">0{i + 1}</span>
                  </div>
                  <h3 className="text-base font-semibold tracking-tight text-foreground">{s.title}</h3>
                  <p className="text-sm leading-relaxed text-muted-foreground">{s.description}</p>

                  {!isLast && (
                    <span className="pointer-events-none absolute -bottom-7 left-1/2 z-10 hidden -translate-x-1/2 text-primary lg:block" aria-hidden="true">
                      <ArrowRight className="h-5 w-5" />
                    </span>
                  )}
                </div>
                {!isLast && (
                  <span className="mt-4 flex justify-center text-primary lg:hidden" aria-hidden="true">
                    <ArrowDown className="h-5 w-5" />
                  </span>
                )}
              </Reveal>
            );
          })}
        </div>
      </LandingContainer>
    </section>
  );
}
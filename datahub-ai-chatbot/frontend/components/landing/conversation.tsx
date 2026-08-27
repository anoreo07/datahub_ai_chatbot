"use client";

import { cn } from "@/lib/utils";
import { Bot, BookOpen, GitBranch, Table, User } from "lucide-react";

import { LandingContainer, Reveal, SectionHeading } from "@/components/landing/shared";

interface Turn {
  question: string;
  answer: string;
  chips: { label: string; icon: React.ElementType }[];
}

const TURNS: Turn[] = [
  {
    question: "dim_warehouse có những trường nào?",
    answer: "dim_warehouse có 8 trường: warehouse_id, warehouse_name, city, region, capacity, opened_date, manager, updated_at.",
    chips: [
      { label: "Dataset", icon: Table },
      { label: "Field", icon: Table },
    ],
  },
  {
    question: "warehouse_id dùng để làm gì?",
    answer: "warehouse_id là khóa chính của dim_warehouse, được dùng để join với fact_sales_order.warehouse_id.",
    chips: [{ label: "Schema", icon: Table }],
  },
  {
    question: "field này có glossary term nào không?",
    answer: "Có — warehouse_id tương ứng với glossary term 'Warehouse ID' trong business glossary.",
    chips: [{ label: "Glossary", icon: BookOpen }],
  },
  {
    question: "dataset này liên kết với những dataset nào?",
    answer: "dim_warehouse có 3 upstreams (staging.warehouse_raw) và 2 downstreams (fact_sales_order, fact_inventory).",
    chips: [
      { label: "Lineage", icon: GitBranch },
      { label: "Ownership", icon: User },
    ],
  },
];

function QuestionBubble({ text }: { text: string }) {
  return (
    <div className="flex flex-col items-end gap-2">
      <span className="text-xs font-medium text-muted-foreground">You</span>
      <div className="max-w-[85%] rounded-2xl rounded-br-sm border border-border bg-card px-4 py-3 text-sm text-foreground shadow-sm sm:max-w-[70%]">
        {text}
      </div>
    </div>
  );
}

function AnswerBubble({ turn }: { turn: Turn }) {
  return (
    <div className="flex flex-col items-start gap-2">
      <div className="flex items-center gap-1.5 text-xs font-medium text-primary">
        <Bot className="h-3.5 w-3.5" aria-hidden="true" />
        V-DataAtlas
      </div>
      <div className="max-w-[85%] rounded-2xl rounded-bl-sm border border-border bg-accent/60 px-4 py-3 text-sm leading-relaxed text-foreground sm:max-w-[78%]">
        <p>{turn.answer}</p>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {turn.chips.map((c) => (
            <span
              key={`${turn.question}-${c.label}`}
              className="inline-flex items-center gap-1 rounded-full border border-border bg-card px-2 py-0.5 text-[11px] font-medium text-muted-foreground"
            >
              <c.icon className="h-3 w-3 text-primary" aria-hidden="true" />
              {c.label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

export function Conversation() {
  return (
    <section id="conversation" className="scroll-mt-20 border-y border-border bg-[#f7f7f8] py-20 sm:py-28">
      <LandingContainer>
        <div className="mt-14 flex flex-col items-center gap-12 lg:flex-row lg:items-start lg:gap-16">
          <Reveal className="w-full lg:w-1/3 lg:sticky lg:top-28">
            <SectionHeading
              eyebrow="Conversational"
              title="Ask naturally. Get connected answers."
              description="Follow-up questions stay in the same conversation — V-DataAtlas keeps the context and connects each answer back to the entities it referenced before."
              align="left"
            />
          </Reveal>

          <Reveal delay={0.15} className="w-full lg:w-2/3">
            <div className="relative flex flex-col gap-8 rounded-2xl border border-border bg-card p-5 shadow-sm sm:p-8">
              <div
                className="absolute bottom-10 left-[1.15rem] top-16 w-px bg-border sm:left-[1.4rem]"
                aria-hidden="true"
              />
              <div className="mx-auto inline-flex items-center gap-2 rounded-full border border-primary/30 bg-accent px-3 py-1 text-xs font-medium text-primary">
                <span className="h-2 w-2 rounded-full bg-primary" />
                One context — dim_warehouse
              </div>

              <div className="flex flex-col gap-8">
                {TURNS.map((t, i) => (
                  <Reveal key={t.question} delay={0.1 + i * 0.08} className="relative flex flex-col gap-4">
                    <QuestionBubble text={t.question} />
                    <AnswerBubble turn={t} />
                  </Reveal>
                ))}
              </div>

              <Reveal delay={0.4}>
                <p
                  className={cn(
                    "flex items-center justify-center gap-2 border-t border-border pt-5 text-xs text-muted-foreground",
                    "text-center"
                  )}
                >
                  <Bot className="h-3.5 w-3.5" aria-hidden="true" />
                  Every turn builds on the previous one — no repeated context needed.
                </p>
              </Reveal>
            </div>
          </Reveal>
        </div>
      </LandingContainer>
    </section>
  );
}
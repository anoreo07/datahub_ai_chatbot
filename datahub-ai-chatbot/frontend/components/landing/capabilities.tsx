"use client";

import {
  BookOpen,
  FileText,
  GitBranch,
  BarChart,
  Code,
  Image,
  MessageCircle,
  Search,
  ShieldCheck,
  Table,
  Users,
} from "lucide-react";

import { LandingContainer, Reveal, SectionHeading } from "@/components/landing/shared";

const CAPABILITIES = [
  {
    icon: Search,
    title: "Dataset discovery",
    description: "Find datasets by describing what you need — no URNs or search syntax required.",
  },
  {
    icon: Table,
    title: "Schema & fields",
    description: "Understand a dataset's columns, types, and how fields relate to each other.",
  },
  {
    icon: Users,
    title: "Ownership",
    description: "See who owns and maintains each dataset, dashboard, and field.",
  },
  {
    icon: ShieldCheck,
    title: "Domains & permissions",
    description: "Answers respect your roles, domains, and the permissions of your account.",
  },
  {
    icon: BookOpen,
    title: "Glossary & terms",
    description: "Map business terms to their definitions and glossaries across your catalog.",
  },
  {
    icon: FileText,
    title: "Documentation & documents",
    description: "Search entity docs, descriptions, and uploaded documents for context.",
  },
  {
    icon: GitBranch,
    title: "Lineage & impact analysis",
    description: "Trace upstream and downstream dependencies before you change anything.",
  },
  {
    icon: BarChart,
    title: "Data quality",
    description: "Check quality scores, checks, and findings directly from your metadata.",
  },
  {
    icon: Code,
    title: "SQL generation",
    description: "Ask for a query and get SQL generated from the real schema metadata.",
  },
  {
    icon: Image,
    title: "Image understanding",
    description: "Upload screenshots or diagrams and ask questions about them.",
  },
  {
    icon: MessageCircle,
    title: "Contextual reasoning",
    description: "Complex, multi-turn questions keep context across the whole conversation.",
  },
];

export function Capabilities() {
  return (
    <section id="capabilities" className="scroll-mt-20 py-20 sm:py-28">
      <LandingContainer>
        <Reveal>
          <SectionHeading
            eyebrow="Capabilities"
            title="What can DataAtlas understand?"
            description="Everything your DataHub knows — from datasets and schemas to glossary terms, ownership, lineage, and quality — in one conversational assistant."
          />
        </Reveal>

        <div className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {CAPABILITIES.map((c, i) => (
            <Reveal key={c.title} delay={(i % 3) * 0.06}>
              <div className="group flex h-full flex-col gap-3 rounded-xl border border-border bg-card p-5 shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-md">
                <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent text-foreground transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
                  <c.icon className="h-5 w-5" aria-hidden="true" />
                </span>
                <h3 className="text-base font-semibold tracking-tight text-foreground">{c.title}</h3>
                <p className="text-sm leading-relaxed text-muted-foreground">{c.description}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </LandingContainer>
    </section>
  );
}
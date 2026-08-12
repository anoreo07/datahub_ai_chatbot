"use client";

import {
  Info,
  Layers,
  Link2,
  MessageSquare,
  ShieldCheck,
} from "lucide-react";

import { LandingContainer, Reveal, SectionHeading } from "@/components/landing/shared";

const PILLARS = [
  {
    icon: ShieldCheck,
    title: "Permission-aware",
    description: "Answers respect your roles, domains, and access controls on DataHub.",
  },
  {
    icon: Link2,
    title: "Metadata-grounded",
    description: "Always built from the real metadata in your catalog — verified and cited.",
  },
  {
    icon: MessageSquare,
    title: "Context-aware",
    description: "Multi-turn conversations keep context and intent across follow-ups.",
  },
  {
    icon: Info,
    title: "Explainable",
    description: "Every answer shows the entities and reasoning steps behind it.",
  },
  {
    icon: Layers,
    title: "Extensible",
    description: "Plugs into your existing DataHub, so new datasets and domains just work.",
  },
];

export function Enterprise() {
  return (
    <section id="enterprise" className="scroll-mt-20 py-20 sm:py-28">
      <LandingContainer>
        <Reveal>
          <SectionHeading
            eyebrow="Enterprise-ready"
            title="Designed for enterprise data discovery"
            description="Purpose-built for teams that treat metadata as infrastructure — safe, grounded, and introspectable."
          />
        </Reveal>

        <div className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {PILLARS.map((p, i) => (
            <Reveal key={p.title} delay={(i % 5) * 0.06}>
              <div className="flex h-full flex-col gap-3 rounded-xl border border-border bg-card p-5 shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-md">
                <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent text-foreground">
                  <p.icon className="h-5 w-5" aria-hidden="true" />
                </span>
                <h3 className="text-sm font-semibold tracking-tight text-foreground">{p.title}</h3>
                <p className="text-[13px] leading-relaxed text-muted-foreground">{p.description}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </LandingContainer>
    </section>
  );
}
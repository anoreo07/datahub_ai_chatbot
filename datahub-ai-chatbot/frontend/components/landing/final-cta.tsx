"use client";

import { ArrowRight, Sparkles } from "lucide-react";

import { LandingContainer, Reveal, PrimaryLink, GhostLink } from "@/components/landing/shared";

export function FinalCta() {
  return (
    <section className="border-t border-border py-20 sm:py-28">
      <LandingContainer>
        <Reveal>
          <div className="relative overflow-hidden rounded-3xl border border-border bg-card px-6 py-16 text-center shadow-sm sm:px-12 sm:py-24">
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_-10%,color-mix(in_srgb,var(--primary)_10%,transparent),transparent_55%)]" aria-hidden="true" />

            <div className="relative mx-auto flex max-w-2xl flex-col items-center gap-6">
              <span className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-accent px-3.5 py-1.5 text-xs font-medium text-primary">
                <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
                Your metadata, made conversational
              </span>
              <h2 className="text-balance text-3xl font-semibold leading-[1.1] tracking-tight text-foreground sm:text-5xl">
                Your DataHub already has the knowledge.
                <br />
                V-DataAtlas makes it{" "}
                <span className="text-primary">conversational</span>.
              </h2>
              <p className="max-w-xl text-balance text-base leading-relaxed text-muted-foreground sm:text-lg">
                Ask in natural language. Get grounded, connected answers from the
                metadata you already trust.
              </p>
              <div className="flex flex-col items-center gap-3 sm:flex-row">
                <PrimaryLink href="/chat">
                  Try V-DataAtlas
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
                </PrimaryLink>
                <GhostLink href="#datahub">Revisit V-DataAtlas × DataHub</GhostLink>
              </div>
            </div>
          </div>
        </Reveal>
      </LandingContainer>
    </section>
  );
}
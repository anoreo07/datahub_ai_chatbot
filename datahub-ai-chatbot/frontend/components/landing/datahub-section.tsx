"use client";

import { ArrowDownRight, ArrowUpRight, Sparkles, ShieldCheck, FileSearch } from "lucide-react";
import Image from "next/image";

import styles from "@/components/landing/landing.module.css";
import { LandingContainer, Reveal, SectionHeading } from "@/components/landing/shared";
import { cn } from "@/lib/utils";

export function DataHubSection() {
  return (
    <section id="datahub" className="scroll-mt-20 border-y border-border bg-[#f7f7f8] py-20 sm:py-28">
      <LandingContainer>
        <div className="grid gap-14 lg:grid-cols-[1fr_1.1fr] lg:gap-20">
          {/* Left copy */}
          <div className="flex flex-col gap-6">
            <Reveal>
              <SectionHeading
                align="left"
                eyebrow="V-DataAtlas × DataHub"
                title={
                  <>
                    AI intelligence for your <span className="text-primary">DataHub</span>.
                  </>
                }
                description={
                  <>
                    DataHub is the metadata layer for your data platform — the catalog,
                    schema, glossary, ownership, lineage, and governance. V-DataAtlas is the
                    AI layer on top of it, giving everyone a conversational way to explore
                    and understand that metadata.
                  </>
                }
              />
            </Reveal>

            <Reveal delay={0.1}>
              <ul className="flex flex-col gap-4">
                <li className="flex gap-3">
                  <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-border bg-card text-primary">
                    <ShieldCheck className="h-4 w-4" aria-hidden="true" />
                  </span>
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    <span className="font-semibold text-foreground">DataHub stays the source of truth.</span>{" "}
                    Your catalog and governance are untouched — V-DataAtlas reads from and
                    builds on that metadata.
                  </p>
                </li>
                <li className="flex gap-3">
                  <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-border bg-card text-primary">
                    <FileSearch className="h-4 w-4" aria-hidden="true" />
                  </span>
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    <span className="font-semibold text-foreground">V-DataAtlas doesn&apos;t replace DataHub.</span>{" "}
                    It sits above it as an AI interaction layer, so asking questions in
                    natural language becomes part of your data workflow.
                  </p>
                </li>
                <li className="flex gap-3">
                  <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-border bg-card text-primary">
                    <Sparkles className="h-4 w-4" aria-hidden="true" />
                  </span>
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    <span className="font-semibold text-foreground">Built on DataHub&apos;s metadata.</span>{" "}
                    Datasets, fields, glossary terms, ownership, domains, lineage — V-DataAtlas
                    connects them all into grounded answers.
                  </p>
                </li>
              </ul>
            </Reveal>
          </div>

          {/* Right visual: V-DataAtlas ⇄ DataHub */}
          <Reveal delay={0.15} className="flex items-center justify-center">
            <figure className="w-full max-w-lg">
              <div className="flex items-center justify-between gap-3 rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-10">
                <div className="flex flex-col items-center gap-2 text-center">
                  <Image
                    src="/dataatlas_logo_transparent.png"
                    alt="V-DataAtlas logo"
                    width={72}
                    height={72}
                    className="h-16 w-16 object-contain sm:h-20 sm:w-20"
                  />
                  <figcaption className="flex flex-col">
                    <span className="font-display text-base tracking-tight text-foreground">V-DataAtlas</span>
                    <span className="text-xs text-muted-foreground">AI interaction layer</span>
                  </figcaption>
                </div>

                <div className="relative w-16 shrink-0 sm:w-24" aria-hidden="true">
                  <div className="h-px w-full bg-border" />
                  {/* animated flow dots */}
                  <span className={cn("absolute top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary", styles["lp-flow"])} />
                  <span className={cn("absolute top-1/2 h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-cyan-400", styles["lp-flow-reverse"])} />
                </div>

                <div className="flex flex-col items-center gap-2 text-center">
                  <Image
                    src="/datahub_logo.png"
                    alt="DataHub logo"
                    width={72}
                    height={72}
                    className="h-16 w-16 object-contain sm:h-20 sm:w-20"
                  />
                  <figcaption className="flex flex-col">
                    <span className="text-base font-semibold tracking-tight text-foreground">DataHub</span>
                    <span className="text-xs text-muted-foreground">Metadata source of truth</span>
                  </figcaption>
                </div>
              </div>

              <p className="mt-4 flex items-center justify-center gap-1.5 text-center text-xs text-muted-foreground">
                <ArrowUpRight className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                You ask V-DataAtlas&nbsp;
                <ArrowDownRight className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                V-DataAtlas reads DataHub metadata
              </p>
            </figure>
          </Reveal>
        </div>
      </LandingContainer>
    </section>
  );
}
"use client";

import { ArrowRight, Database } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";

import { HeroVisual } from "@/components/landing/hero-visual";
import { LandingContainer, PrimaryLink, GhostLink, Reveal } from "@/components/landing/shared";

export function Hero() {
  const reduce = useReducedMotion();

  return (
    <section id="top" className="relative overflow-hidden">
      <LandingContainer className="pb-20 pt-16 sm:pb-24 sm:pt-24">
        <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-16">
          <div className="flex flex-col items-start gap-8 text-left">
            <Reveal>
              <span className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3.5 py-1.5 text-xs font-medium text-muted-foreground">
                <Database className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                AI Metadata Assistant for DataHub
              </span>
            </Reveal>

            <motion.h1
              initial={{ opacity: 0, y: reduce ? 0 : 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
              className="text-balance text-5xl font-semibold leading-[1.05] tracking-tight text-foreground sm:text-6xl md:text-7xl"
            >
              Talk to your data.
              <br />
              Understand your <span className="text-primary">metadata</span>.
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: reduce ? 0 : 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.15, ease: [0.22, 1, 0.36, 1] }}
              className="max-w-xl text-balance text-base leading-relaxed text-muted-foreground sm:text-lg"
            >
              V-DataAtlas is an AI metadata assistant that helps your team search,
              understand, analyze, and get more out of the metadata inside DataHub —
              with plain, natural language conversations.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: reduce ? 0 : 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.28, ease: [0.22, 1, 0.36, 1] }}
              className="flex flex-col items-start gap-3 sm:flex-row"
            >
              <PrimaryLink href="/chat">
                Try V-DataAtlas
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
              </PrimaryLink>
              <GhostLink href="#datahub">Explore DataHub</GhostLink>
            </motion.div>
          </div>

          <Reveal delay={0.2} className="w-full">
            <HeroVisual />
          </Reveal>
        </div>
      </LandingContainer>
    </section>
  );
}
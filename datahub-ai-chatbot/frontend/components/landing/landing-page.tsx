"use client";

import { MotionConfig } from "framer-motion";

import { Capabilities } from "@/components/landing/capabilities";
import { ComplexQuestions } from "@/components/landing/complex-questions";
import { Conversation } from "@/components/landing/conversation";
import { DataHubSection } from "@/components/landing/datahub-section";
import { LandingFooter } from "@/components/landing/landing-footer";
import { LandingNav } from "@/components/landing/landing-nav";
import { Enterprise } from "@/components/landing/enterprise";
import { FinalCta } from "@/components/landing/final-cta";
import { Grounded } from "@/components/landing/grounded";
import { Hero } from "@/components/landing/hero";
import { QuestionFlow } from "@/components/landing/question-flow";
import { Workflows } from "@/components/landing/workflows";

export function LandingPage() {
  return (
    <MotionConfig reducedMotion="user">
      {/* Force the light palette for the marketing page regardless of the
          user's saved app theme, so the landing always reads consistent. */}
      <div data-theme="light" className="min-h-screen bg-background font-sans text-foreground">
        <LandingNav />
        <main>
          <Hero />
          <DataHubSection />
          <Capabilities />
          <Conversation />
          <QuestionFlow />
          <Workflows />
          <ComplexQuestions />
          <Grounded />
          <Enterprise />
          <FinalCta />
        </main>
        <LandingFooter />
      </div>
    </MotionConfig>
  );
}
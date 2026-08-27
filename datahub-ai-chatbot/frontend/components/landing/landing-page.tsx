"use client";

import { MotionConfig } from "framer-motion";

import { Capabilities } from "@/components/landing/capabilities";
import { DataHubSection } from "@/components/landing/datahub-section";
import { LandingFooter } from "@/components/landing/landing-footer";
import { LandingNav } from "@/components/landing/landing-nav";
import { FinalCta } from "@/components/landing/final-cta";
import { Grounded } from "@/components/landing/grounded";
import { Hero } from "@/components/landing/hero";

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
          <Grounded />
          <FinalCta />
        </main>
        <LandingFooter />
      </div>
    </MotionConfig>
  );
}
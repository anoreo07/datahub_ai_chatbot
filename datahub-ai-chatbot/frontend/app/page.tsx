import type { Metadata } from "next";

import { LandingPage } from "@/components/landing/landing-page";

export const metadata: Metadata = {
  title: "V-DataAtlas — AI Metadata Assistant for DataHub",
  description:
    "V-DataAtlas is an AI metadata assistant that helps your team search, understand, analyze, and get more out of the metadata inside DataHub — with plain, natural language conversations.",
};

export default function LandingRoute() {
  return <LandingPage />;
}
"use client";

import { ArrowUpRight, Database } from "lucide-react";
import Image from "next/image";
import Link from "next/link";

import { LandingContainer } from "@/components/landing/shared";

const GROUPS = [
  {
    title: "Product",
    links: [
      { href: "/chat", label: "Chat" },
      { href: "/search", label: "Search metadata" },
      { href: "/glossary", label: "Glossary" },
    ],
  },
  {
    title: "Platform",
    links: [
      { href: "https://www.datahubproject.io", label: "DataHub", external: true },
      { href: "/status", label: "System status" },
      { href: "/login", label: "Sign in" },
    ],
  },
];

export function LandingFooter() {
  return (
    <footer className="border-t border-border bg-[#f7f7f8]">
      <LandingContainer className="py-14">
        <div className="grid gap-10 md:grid-cols-[1.4fr_1fr_1fr]">
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-2.5">
              <Image
                src="/dataatlas_logo_transparent.png"
                alt=""
                width={30}
                height={30}
                className="h-8 w-8 object-contain"
              />
              <span className="font-display text-lg tracking-tight text-foreground">V-DataAtlas</span>
            </div>
            <p className="max-w-sm text-sm leading-relaxed text-muted-foreground">
              An AI metadata assistant that makes your DataHub collection searchable,
              understandable, and conversational — in natural language.
            </p>
            <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Database className="h-3.5 w-3.5" aria-hidden="true" />
              Built on DataHub metadata
            </p>
          </div>

          {GROUPS.map((g) => (
            <nav key={g.title} aria-label={g.title}>
              <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-foreground">
                {g.title}
              </h3>
              <ul className="flex flex-col gap-2">
                {g.links.map((l) => (
                  <li key={l.label}>
                    <Link
                      href={l.href}
                      target={l.external ? "_blank" : undefined}
                      rel={l.external ? "noopener noreferrer" : undefined}
                      className="group inline-flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm"
                    >
                      {l.label}
                      {l.external && (
                        <ArrowUpRight className="h-3.5 w-3.5 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" aria-hidden="true" />
                      )}
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>
          ))}
        </div>

        <div className="mt-12 flex flex-col items-center justify-between gap-3 border-t border-border pt-6 sm:flex-row">
          <p className="text-xs text-muted-foreground">
            © {new Date().getFullYear()} V-DataAtlas. All rights reserved.
          </p>
          <p className="text-xs text-muted-foreground">
            AI Metadata Assistant for DataHub
          </p>
        </div>
      </LandingContainer>
    </footer>
  );
}
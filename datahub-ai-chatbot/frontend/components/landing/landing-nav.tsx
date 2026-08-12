"use client";

import { cn } from "@/lib/utils";
import { Menu, X } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";

import { LandingContainer } from "@/components/landing/shared";

const LINKS = [
  { href: "#datahub", label: "DataHub" },
  { href: "#capabilities", label: "What it understands" },
  { href: "#how-it-works", label: "How it works" },
  { href: "#workflows", label: "Workflows" },
  { href: "#enterprise", label: "Enterprise" },
];

export function LandingNav() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={cn(
        "sticky top-0 z-50 border-b transition-all duration-300",
        scrolled
          ? "border-border/80 bg-background/85 backdrop-blur-md"
          : "border-transparent bg-transparent"
      )}
    >
      <LandingContainer>
        <nav
          aria-label="Landing navigation"
          className="flex h-16 items-center justify-between gap-4"
        >
          <a
            href="#top"
            className="flex shrink-0 items-center gap-2.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-lg"
            aria-label="DataAtlas home"
          >
            <Image
              src="/dataatlas_logo_transparent.png"
              alt=""
              width={32}
              height={32}
              className="h-8 w-8 object-contain"
            />
            <span className="font-display text-lg tracking-tight text-foreground">
              DataAtlas
            </span>
          </a>

          <div className="hidden items-center gap-1 md:flex">
            {LINKS.map((l) => (
              <a
                key={l.href}
                href={l.href}
                className="rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                {l.label}
              </a>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <Link
              href="/chat"
              className="hidden rounded-lg border border-border bg-card px-4 py-2 text-sm font-semibold text-foreground transition-colors hover:border-primary/40 hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:inline-flex"
            >
              Open Chat
            </Link>
            <Link
              href="/chat"
              className="hidden rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-sm transition-all hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:inline-flex"
            >
              Try DataAtlas
            </Link>

            <button
              type="button"
              onClick={() => setOpen((v) => !v)}
              className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-card text-foreground transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring md:hidden"
              aria-expanded={open}
              aria-label={open ? "Close navigation menu" : "Open navigation menu"}
            >
              {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>
        </nav>
      </LandingContainer>

      {open && (
        <div className="border-t border-border bg-background md:hidden">
          <LandingContainer>
            <div className="flex flex-col gap-1 py-3">
              {LINKS.map((l) => (
                <a
                  key={l.href}
                  href={l.href}
                  onClick={() => setOpen(false)}
                  className="rounded-md px-3 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                >
                  {l.label}
                </a>
              ))}
              <div className="mt-2 grid grid-cols-2 gap-2 border-t border-border pt-3">
                <Link
                  href="/chat"
                  onClick={() => setOpen(false)}
                  className="inline-flex h-11 items-center justify-center rounded-lg border border-border bg-card text-sm font-semibold text-foreground"
                >
                  Open Chat
                </Link>
                <Link
                  href="/chat"
                  onClick={() => setOpen(false)}
                  className="inline-flex h-11 items-center justify-center rounded-lg bg-primary text-sm font-semibold text-primary-foreground"
                >
                  Try DataAtlas
                </Link>
              </div>
            </div>
          </LandingContainer>
        </div>
      )}
    </header>
  );
}
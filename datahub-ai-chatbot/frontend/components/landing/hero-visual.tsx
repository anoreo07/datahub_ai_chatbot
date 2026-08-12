"use client";

import { cn } from "@/lib/utils";
import {
  BookOpen,
  Database,
  GitBranch,
  Layers,
  Table,
  User,
  Sparkles,
  CornerDownRight,
} from "lucide-react";
import { useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";

import styles from "@/components/landing/landing.module.css";

interface MapNode {
  id: string;
  x: number;
  y: number;
  label: string;
  value: string;
  icon: React.ElementType;
}

const NODES: MapNode[] = [
  { id: "dataset", x: 16, y: 32, label: "Dataset", value: "dim_warehouse", icon: Database },
  { id: "field", x: 35, y: 13, label: "Field", value: "warehouse_id", icon: Table },
  { id: "glossary", x: 66, y: 13, label: "Glossary", value: "warehouse facility", icon: BookOpen },
  { id: "owner", x: 84, y: 36, label: "Owner", value: "Data Platform", icon: User },
  { id: "lineage", x: 78, y: 85, label: "Lineage", value: "3 upstreams", icon: GitBranch },
  { id: "domain", x: 16, y: 82, label: "Domain", value: "Logistics", icon: Layers },
];

const CENTER = { x: 50, y: 50 };

const QUESTION = "What is warehouse_id used for?";
const STATUSES = [
  "Understanding intent…",
  "Resolving entities…",
  "Linking schema + glossary…",
  "Tracing lineage & owners…",
];

function useTypewriter(text: string, enabled: boolean) {
  /* Start fully rendered (also on SSR / reduced motion) to avoid hydration
     mismatch; re-type from empty only after mount when enabled. */
  const [count, setCount] = useState(text.length);
  useEffect(() => {
    if (!enabled) {
      setCount(text.length);
      return;
    }
    setCount(0);
    const t = window.setInterval(() => {
      setCount((c) => {
        if (c >= text.length) {
          window.clearInterval(t);
          return c;
        }
        return c + 1;
      });
    }, 42);
    return () => window.clearInterval(t);
  }, [text, enabled]);
  return text.slice(0, count);
}

export function HeroVisual() {
  const reduceMotion = useReducedMotion();
  const [active, setActive] = useState<string | null>(null);
  const [live, setLive] = useState(true);

  const typed = useTypewriter(QUESTION, !reduceMotion);

  useEffect(() => {
    if (!live || reduceMotion) return;
    const timer = window.setTimeout(() => {
      const cycle = window.setInterval(() => {
        setActive((cur) => {
          const idx = NODES.findIndex((n) => n.id === cur);
          return NODES[(idx + 1) % NODES.length].id;
        });
      }, 1100);
      return () => window.clearInterval(cycle);
    }, QUESTION.length * 42 + 600);
    return () => window.clearTimeout(timer);
  }, [live, reduceMotion]);

  const activeIndex = NODES.findIndex((n) => n.id === active);
  const status = STATUSES[Math.min(activeIndex, STATUSES.length - 1)];

  return (
    <div
      className={cn(
        "relative w-full overflow-hidden rounded-2xl border border-border bg-card shadow-sm",
        styles["lp-grid"]
      )}
    >
      <div className="relative aspect-[4/5] w-full sm:aspect-[16/10] lg:aspect-[16/9]">
        {/* Connecting lines */}
        <svg
          className="pointer-events-none absolute inset-0 h-full w-full"
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          {NODES.map((n, i) => {
            const isActive = active === n.id;
            return (
              <g key={n.id}>
                <line
                  x1={CENTER.x}
                  y1={CENTER.y}
                  x2={n.x}
                  y2={n.y}
                  stroke={isActive ? "var(--lp-accent)" : "currentColor"}
                  strokeOpacity={isActive ? 0.65 : 0.2}
                  strokeWidth={i === 0 ? 1.4 : 1}
                  className={cn(styles["lp-line"], "text-foreground")}
                  vectorEffect="non-scaling-stroke"
                  strokeLinecap="round"
                />
              </g>
            );
          })}
        </svg>

        {/* Central query card */}
        <div className="absolute left-1/2 top-1/2 z-10 w-[78%] max-w-xs -translate-x-1/2 -translate-y-1/2 sm:w-[42%]">
          <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4 shadow-sm">
            <div className="flex items-center gap-2 text-xs font-semibold text-primary">
              <Sparkles className="h-4 w-4" />
              DataAtlas
            </div>
            <div className="min-h-[3.25rem] text-sm leading-relaxed text-foreground">
              {typed}
              <span className={cn("ml-0.5 inline-block h-4 w-[2px] translate-y-[3px] bg-primary", styles["lp-caret"])} />
            </div>
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <span
                className={cn(
                  "h-2 w-2 rounded-full bg-primary",
                  styles["lp-pulse"]
                )}
              />
              {live ? status : "Paused"}
            </div>
          </div>
        </div>

        {/* Metadata nodes */}
        {NODES.map((n, i) => {
          const Icon = n.icon;
          const isActive = active === n.id;
          return (
            <button
              key={n.id}
              type="button"
              onMouseEnter={() => {
                setActive(n.id);
                setLive(false);
              }}
              onMouseLeave={() => {
                setActive(null);
                setLive(true);
              }}
              onFocus={() => {
                setActive(n.id);
                setLive(false);
              }}
              onBlur={() => {
                setActive(null);
                setLive(true);
              }}
              aria-label={`${n.label} — ${n.value}`}
              className={cn(
                "absolute z-10 flex -translate-x-1/2 -translate-y-1/2 cursor-default items-center gap-2 rounded-lg border bg-card px-2 py-1.5 text-left shadow-sm transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary sm:px-2.5 sm:py-2",
                isActive
                  ? "border-primary/60 shadow-md"
                  : "border-border hover:border-primary/40",
                i % 3 === 0
                  ? styles["lp-float"]
                  : i % 3 === 1
                    ? styles["lp-float-2"]
                    : styles["lp-float-3"]
              )}
              style={{ left: `${n.x}%`, top: `${n.y}%` }}
            >
              <span
                className={cn(
                  "flex h-6 w-6 shrink-0 items-center justify-center rounded-md transition-colors",
                  isActive ? "bg-primary text-primary-foreground" : "bg-accent text-foreground"
                )}
              >
                <Icon className="h-3.5 w-3.5" />
              </span>
              <span className="flex flex-col leading-none">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  {n.label}
                </span>
                <span className="mt-0.5 text-xs font-medium text-foreground">
                  {n.value}
                </span>
              </span>
              {isActive && (
                <CornerDownRight className="h-3 w-3 shrink-0 text-primary" aria-hidden="true" />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
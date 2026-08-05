"use client";

import type { LineageData, LineageNode } from "@/lib/types";

const NODE_W = 150;
const NODE_H = 34;
const ROW_H = 46;
const PAD_Y = 26;
const ELBOW = 70;

function byUrn(lg: LineageData, list: LineageNode[]): LineageNode[] {
  const seen = new Set<string>();
  const out: LineageNode[] = [];
  for (const n of list || []) {
    if (n && n.urn && !seen.has(n.urn) && n.urn !== lg.entity_urn) {
      seen.add(n.urn);
      out.push(n);
    }
  }
  return out;
}

function truncate(s: string, max = 22) {
  return s.length > max ? s.slice(0, max - 2) + "…" : s;
}

function Node({
  x,
  y,
  label,
  main,
  url,
}: {
  x: number;
  y: number;
  label: string;
  main?: boolean;
  url?: string;
}) {
  const body = (
    <g className={main ? "main" : ""}>
      <rect
        x={x - NODE_W / 2}
        y={y - NODE_H / 2}
        width={NODE_W}
        height={NODE_H}
        rx="6"
        className="fill-card stroke-primary"
        strokeWidth={main ? 2 : 1.2}
      />
      <text
        x={x}
        y={y}
        textAnchor="middle"
        dominantBaseline="central"
        className="fill-foreground"
        style={{ fontSize: 11 }}
      >
        {truncate(label || "?")}
      </text>
    </g>
  );
  if (url) {
    return (
      <a href={url} target="_blank" rel="noopener noreferrer" style={{ display: "inline-block" }}>
        {body}
      </a>
    );
  }
  return body;
}

export function LineageGraph({ lg }: { lg: LineageData }) {
  const up = byUrn(lg, lg.upstreams);
  const down = byUrn(lg, lg.downstreams);
  if (up.length === 0 && down.length === 0) return null;

  const nRows = Math.max(up.length, down.length);
  const leftX = NODE_W / 2;
  const mainX = NODE_W + ELBOW + NODE_W / 2;
  const rightX = NODE_W + ELBOW + NODE_W + ELBOW + NODE_W / 2;
  const width = rightX + NODE_W / 2 + 16;
  const gridH = Math.max(1, nRows) * ROW_H;
  const mainY = PAD_Y + gridH / 2;
  const height = PAD_Y * 2 + gridH;

  const yAt = (i: number) => PAD_Y + i * ROW_H + NODE_H / 2;

  return (
    <div className="mt-2 overflow-x-auto rounded-lg border bg-muted/30 p-1.5">
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Lineage graph">
        <defs>
          <marker id="lgArrowUp" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L9,4.5 L0,9 z" fill="var(--success)" />
          </marker>
          <marker id="lgArrowDown" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L9,4.5 L0,9 z" fill="var(--warning)" />
          </marker>
        </defs>

        {up.map((n, i) => {
          const y = yAt(i);
          const midX = leftX + NODE_W / 2 + ELBOW / 2;
          return (
            <polyline
              key={n.urn}
              className="fill-none stroke-success"
              strokeWidth={1.2}
              markerEnd="url(#lgArrowUp)"
              points={`${leftX + NODE_W / 2},${y} ${midX},${y} ${midX},${mainY} ${mainX - NODE_W / 2},${mainY}`}
            />
          );
        })}
        {down.map((n, i) => {
          const y = yAt(i);
          const midX = mainX + NODE_W / 2 + ELBOW / 2;
          return (
            <polyline
              key={n.urn}
              className="fill-none stroke-warning"
              strokeWidth={1.2}
              markerEnd="url(#lgArrowDown)"
              points={`${mainX + NODE_W / 2},${mainY} ${midX},${mainY} ${midX},${y} ${rightX - NODE_W / 2},${y}`}
            />
          );
        })}

        {up.map((n, i) => (
          <Node key={n.urn} x={leftX} y={yAt(i)} label={n.name || n.urn} url={n.url} />
        ))}
        <Node x={mainX} y={mainY} label={lg.entity_name || ""} main url={lg.entity_url} />
        {down.map((n, i) => (
          <Node key={n.urn} x={rightX} y={yAt(i)} label={n.name || n.urn} url={n.url} />
        ))}
      </svg>
      <div className="mt-1 text-center text-[11px] text-muted-foreground">
        ← upstream &nbsp;·&nbsp; <b className="text-foreground">{lg.entity_name}</b> &nbsp;·&nbsp; downstream →
      </div>
    </div>
  );
}
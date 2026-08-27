"use client";

import Image from "next/image";
import { Globe } from "lucide-react";
import type { EntityItem } from "@/lib/types";

interface EntityCardProps {
  entity: EntityItem;
  onOpenPanel?: (entity: EntityItem) => void;
}

export function EntityCard({ entity, onOpenPanel }: EntityCardProps) {
  return (
    <div
      className="mt-2 cursor-pointer rounded-xl border border-border/60 bg-card p-3 shadow-sm transition-colors hover:border-primary/30 hover:bg-accent/40"
      onClick={() => onOpenPanel?.(entity)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onOpenPanel?.(entity);
        }
      }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2 min-w-0">
          <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-muted">
            <Image
              src="/datahub_logo_no_text.svg"
              alt="DataHub"
              width={20}
              height={20}
              className="object-contain"
            />
          </span>
          <div className="min-w-0">
            <p className="text-sm font-semibold leading-tight truncate">{entity.name}</p>
            <div className="flex flex-wrap items-center gap-1.5 mt-1">
              {entity.entity_type && (
                <span className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                  {entity.entity_type}
                </span>
              )}
              {entity.platform && (
                <span className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                  {entity.platform}
                </span>
              )}
              {entity.domain && (
                <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">
                  <Globe className="h-3 w-3" />
                  {entity.domain}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

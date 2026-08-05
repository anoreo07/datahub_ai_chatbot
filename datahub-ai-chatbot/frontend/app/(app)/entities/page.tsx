"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { apiFetch } from "@/lib/api";
import type { SearchResponse } from "@/lib/types";

const TYPES = ["dataset", "dashboard", "glossary_term", "document"];

export default function EntitiesPage() {
  const [type, setType] = useState("dataset");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [items, setItems] = useState<SearchResponse["results"]>([]);

  useEffect(() => {
    setLoading(true);
    setError("");
    apiFetch<SearchResponse>(
      `/api/v1/search?q=*&entity_type=${type}&limit=50`
    )
      .then((d) => setItems(d.results || []))
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  }, [type]);

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-5xl space-y-4 p-6">
        <div className="flex gap-1 rounded-lg border bg-muted/40 p-1">
          {TYPES.map((t) => (
            <button
              key={t}
              onClick={() => setType(t)}
              className={cn(
                "flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                type === t ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
              )}
            >
              {t}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        ) : error ? (
          <p className="text-sm text-destructive">{error}</p>
        ) : (
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">{items.length} {type}</p>
            {items.map((r) => (
              <Card key={r.urn}>
                <CardContent className="flex items-center justify-between gap-3 pt-4">
                  <div className="min-w-0">
                    <p className="truncate font-medium">{r.name}</p>
                    <p className="mt-0.5 break-all text-xs text-muted-foreground">{r.urn}</p>
                  </div>
                  {r.datahub_url && (
                    <a
                      href={r.datahub_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="shrink-0 text-xs text-primary hover:underline"
                    >
                      DataHub
                    </a>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
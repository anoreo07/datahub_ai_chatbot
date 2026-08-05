"use client";

import { useEffect, useMemo, useState } from "react";
import { Loader2, BookOpen } from "lucide-react";

import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { apiFetch } from "@/lib/api";
import type { GlossaryTerm } from "@/lib/types";

export default function GlossaryPage() {
  const [terms, setTerms] = useState<GlossaryTerm[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("");
  const [selected, setSelected] = useState<GlossaryTerm | null>(null);

  useEffect(() => {
    apiFetch<{ terms: GlossaryTerm[] }>("/api/v1/glossary/terms")
      .then((d) => setTerms(d.terms || []))
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    const f = filter.toLowerCase();
    if (!f) return terms;
    return terms.filter(
      (t) => t.name.toLowerCase().includes(f) || (t.description || "").toLowerCase().includes(f)
    );
  }, [terms, filter]);

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-5xl space-y-4 p-6">
        <Input
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Lọc glossary…"
        />

        {loading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        ) : error ? (
          <p className="text-sm text-destructive">{error}</p>
        ) : (
          <>
            <p className="text-sm text-muted-foreground">{filtered.length} terms</p>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {filtered.map((t) => (
                <Card
                  key={t.urn}
                  className="cursor-pointer transition-shadow hover:shadow-md"
                  onClick={() => setSelected(t)}
                >
                  <CardContent className="pt-4">
                    <div className="flex items-center gap-2">
                      <BookOpen className="h-4 w-4 text-primary" />
                      <p className="truncate font-medium">{t.name}</p>
                    </div>
                    {t.domain && <p className="mt-1 text-xs text-muted-foreground">{t.domain}</p>}
                    {t.description && (
                      <p className="mt-2 line-clamp-3 text-sm text-muted-foreground">
                        {t.description}
                      </p>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          </>
        )}
      </div>

      <Dialog open={!!selected} onOpenChange={(o) => !o && setSelected(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{selected?.name}</DialogTitle>
            {selected?.domain && <DialogDescription>{selected.domain}</DialogDescription>}
          </DialogHeader>
          <div className="space-y-4 text-sm">
            <div>
              <p className="mb-1 text-xs font-medium text-muted-foreground">URN</p>
              <p className="break-all text-xs">{selected?.urn}</p>
            </div>
            {selected?.description && (
              <div>
                <p className="mb-1 text-xs font-medium text-muted-foreground">Description</p>
                <p>{selected.description}</p>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
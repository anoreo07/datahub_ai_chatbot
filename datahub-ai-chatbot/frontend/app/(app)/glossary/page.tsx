"use client";

import { useEffect, useMemo, useState } from "react";
import { Loader2, BookOpen, Search, Copy, Check } from "lucide-react";

import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Pagination } from "@/components/ui/pagination";
import { apiFetch } from "@/lib/api";
import type { GlossaryTerm } from "@/lib/types";
import { cn } from "@/lib/utils";

const PER_PAGE = 8;

export default function GlossaryPage() {
  const [terms, setTerms] = useState<GlossaryTerm[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("");
  const [selectedUrn, setSelectedUrn] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    apiFetch<{ terms: GlossaryTerm[] }>("/api/v1/glossary/terms")
      .then((d) => {
        const list = d.terms || [];
        setTerms(list);
      })
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    const f = filter.toLowerCase().trim();
    if (!f) return terms;
    return terms.filter(
      (t) =>
        t.name.toLowerCase().includes(f) ||
        (t.description || "").toLowerCase().includes(f) ||
        (t.domain || "").toLowerCase().includes(f)
    );
  }, [terms, filter]);

  useEffect(() => {
    if (filtered.length > 0) {
      if (!filtered.some((t) => t.urn === selectedUrn)) {
        setSelectedUrn(filtered[0].urn);
      }
    } else {
      setSelectedUrn(null);
    }
  }, [filtered, selectedUrn]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PER_PAGE));
  const currentPage = Math.min(page, pageCount - 1);
  const pageTerms = filtered.slice(currentPage * PER_PAGE, currentPage * PER_PAGE + PER_PAGE);

  const selectedTerm = useMemo(() => {
    return terms.find((t) => t.urn === selectedUrn) || null;
  }, [terms, selectedUrn]);

  const copyUrn = (urn: string) => {
    void navigator.clipboard.writeText(urn);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="h-full w-full flex flex-col p-6 overflow-hidden">
      {loading ? (
        <div className="flex-1 flex justify-center items-center">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </div>
      ) : error ? (
        <div className="flex-1 flex justify-center items-center">
          <p className="text-sm text-destructive font-medium">{error}</p>
        </div>
      ) : (
        <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-12 gap-6 overflow-hidden">
          {/* Left Column: Glossary List */}
          <Card className="lg:col-span-5 flex flex-col overflow-hidden h-full">
            <CardHeader className="pb-3 border-b flex flex-col gap-3">
              <div className="flex justify-between items-center">
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <BookOpen className="h-4 w-4 text-primary" />
                  Business Glossary
                </CardTitle>
                <Badge variant="secondary" className="font-mono text-xs">
                  {filtered.length} terms
                </Badge>
              </div>
              <div className="relative">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  className="pl-8 h-9 text-sm"
                  value={filter}
                  onChange={(e) => {
                    setFilter(e.target.value);
                    setPage(0);
                  }}
                  placeholder="Search glossary terms..."
                />
              </div>
            </CardHeader>
            <CardContent className="flex-1 flex flex-col overflow-hidden p-0">
              <div className="flex-1 overflow-y-auto divide-y divide-border/40 p-2 space-y-1">
                {pageTerms.map((t) => (
                  <div
                    key={t.urn}
                    onClick={() => setSelectedUrn(t.urn)}
                    className={cn(
                      "p-3 rounded-lg cursor-pointer transition-all border border-transparent flex flex-col gap-1",
                      selectedUrn === t.urn
                        ? "bg-primary/5 border-primary/20"
                        : "hover:bg-muted/30"
                    )}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className={cn("font-medium text-sm truncate", selectedUrn === t.urn ? "text-primary" : "text-foreground")}>
                        {t.name}
                      </p>
                      {t.domain && (
                        <Badge variant="outline" className="text-[10px] shrink-0 font-normal py-0">
                          {t.domain}
                        </Badge>
                      )}
                    </div>
                    {t.description && (
                      <p className="text-xs text-muted-foreground line-clamp-1">
                        {t.description}
                      </p>
                    )}
                  </div>
                ))}
                {pageTerms.length === 0 && (
                  <div className="py-12 text-center text-sm text-muted-foreground">
                    No terms match your search.
                  </div>
                )}
              </div>
              <div className="p-4 border-t mt-auto shrink-0">
                <Pagination page={currentPage} pageCount={pageCount} onPageChange={setPage} />
              </div>
            </CardContent>
          </Card>

          {/* Right Column: Glossary Detail View */}
          <Card className="lg:col-span-7 flex flex-col overflow-hidden h-full">
            <CardHeader className="pb-3 border-b">
              <CardTitle className="text-base font-semibold">Glossary Term Details</CardTitle>
            </CardHeader>
            <CardContent className="flex-1 overflow-y-auto p-6">
              {selectedTerm ? (
                <div className="space-y-6">
                  {/* Term Title & Domain */}
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="flex items-center gap-1 bg-muted/40 text-xs py-0.5 px-2 font-normal">
                        <BookOpen className="h-3 w-3 text-primary" />
                        Glossary Term
                      </Badge>
                      {selectedTerm.domain && (
                        <Badge variant="secondary" className="text-xs font-normal">
                          Domain: {selectedTerm.domain}
                        </Badge>
                      )}
                    </div>
                    <h2 className="text-xl font-bold tracking-tight text-foreground">
                      {selectedTerm.name}
                    </h2>
                  </div>

                  {/* URN display */}
                  <div className="space-y-1.5 rounded-lg border bg-muted/20 p-3.5">
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                        Business Term URN
                      </span>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 px-2 text-xs flex items-center gap-1.5 hover:bg-muted"
                        onClick={() => copyUrn(selectedTerm.urn)}
                      >
                        {copied ? (
                          <>
                            <Check className="h-3.5 w-3.5 text-green-600" />
                            <span className="text-green-600 font-medium">Copied</span>
                          </>
                        ) : (
                          <>
                            <Copy className="h-3.5 w-3.5" />
                            <span>Copy URN</span>
                          </>
                        )}
                      </Button>
                    </div>
                    <p className="font-mono text-xs break-all leading-relaxed text-foreground select-all bg-background border rounded p-2">
                      {selectedTerm.urn}
                    </p>
                  </div>

                  {/* Description Section */}
                  {selectedTerm.description ? (
                    <div className="space-y-2">
                      <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
                        Definition / Description
                      </span>
                      <div className="rounded-lg border p-4 bg-muted/10 text-sm leading-relaxed text-foreground whitespace-pre-wrap">
                        {selectedTerm.description}
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
                        Definition / Description
                      </span>
                      <p className="text-sm text-muted-foreground italic">
                        No description provided for this term.
                      </p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="h-full flex flex-col justify-center items-center text-center p-6">
                  <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center mb-4">
                    <BookOpen className="h-6 w-6 text-muted-foreground" />
                  </div>
                  <h3 className="text-sm font-semibold text-foreground">No Glossary Term Selected</h3>
                  <p className="text-xs text-muted-foreground mt-1 max-w-xs">
                    Select a business term from the glossary list on the left to see its domain scope and definition.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
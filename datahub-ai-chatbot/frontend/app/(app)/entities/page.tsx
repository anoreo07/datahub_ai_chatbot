"use client";

import { useEffect, useState, useMemo } from "react";
import { Loader2, Copy, Check, ExternalLink, Search, Database, LayoutGrid, BookOpen, FileText } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Pagination } from "@/components/ui/pagination";
import { cn } from "@/lib/utils";
import { apiFetch } from "@/lib/api";
import type { SearchResponse } from "@/lib/types";

const TYPES = ["dataset", "dashboard", "glossary_term", "document"];
const PER_PAGE = 10;

export default function EntitiesPage() {
  const [type, setType] = useState("dataset");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [items, setItems] = useState<SearchResponse["results"]>([]);
  const [page, setPage] = useState(0);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedUrn, setSelectedUrn] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError("");
    setPage(0);
    setSearchQuery("");
    apiFetch<SearchResponse>(
      `/api/v1/search?q=*&entity_type=${type}&limit=2000`
    )
      .then((d) => {
        const results = d.results || [];
        setItems(results);
      })
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  }, [type]);

  const filteredItems = useMemo(() => {
    if (!searchQuery) return items;
    const q = searchQuery.toLowerCase();
    return items.filter(
      (item) =>
        item.name.toLowerCase().includes(q) ||
        item.urn.toLowerCase().includes(q) ||
        (item.snippet && item.snippet.toLowerCase().includes(q))
    );
  }, [items, searchQuery]);

  useEffect(() => {
    if (filteredItems.length > 0) {
      if (!filteredItems.some((i) => i.urn === selectedUrn)) {
        setSelectedUrn(filteredItems[0].urn);
      }
    } else {
      setSelectedUrn(null);
    }
  }, [filteredItems, selectedUrn]);

  const pageCount = Math.max(1, Math.ceil(filteredItems.length / PER_PAGE));
  const currentPage = Math.min(page, pageCount - 1);
  const pageItems = filteredItems.slice(currentPage * PER_PAGE, currentPage * PER_PAGE + PER_PAGE);

  const selectedItem = useMemo(() => {
    return items.find((item) => item.urn === selectedUrn) || null;
  }, [items, selectedUrn]);

  const copyUrn = (urn: string) => {
    void navigator.clipboard.writeText(urn);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getEntityIcon = (t: string) => {
    switch (t) {
      case "dataset":
        return <Database className="h-4 w-4" />;
      case "dashboard":
        return <LayoutGrid className="h-4 w-4" />;
      case "glossary_term":
        return <BookOpen className="h-4 w-4" />;
      case "document":
        return <FileText className="h-4 w-4" />;
      default:
        return <Database className="h-4 w-4" />;
    }
  };

  const formatTypeLabel = (t: string) => {
    return t.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  };

  return (
    <div className="h-full w-full flex flex-col p-6 overflow-hidden space-y-4">
      {/* Entity Selector Tabs */}
      <div className="flex gap-1 rounded-lg border bg-muted/40 p-1 shrink-0">
        {TYPES.map((t) => (
          <button
            key={t}
            onClick={() => setType(t)}
            className={cn(
              "flex-1 rounded-md px-3 py-2 text-sm font-medium transition-all flex items-center justify-center gap-2",
              type === t
                ? "bg-background text-foreground shadow-sm border border-border/10"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            {getEntityIcon(t)}
            <span className="capitalize">{t.replace(/_/g, " ")}</span>
          </button>
        ))}
      </div>

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
          {/* Left Column: Entity List */}
          <Card className="lg:col-span-5 flex flex-col overflow-hidden h-full">
            <CardHeader className="pb-3 border-b flex flex-col gap-3">
              <div className="flex justify-between items-center">
                <CardTitle className="text-base font-semibold">
                  List of {formatTypeLabel(type)}s
                </CardTitle>
                <Badge variant="secondary" className="font-mono text-xs">
                  {filteredItems.length} total
                </Badge>
              </div>
              <div className="relative">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  className="pl-8 h-9 text-sm"
                  placeholder={`Search ${type}...`}
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setPage(0);
                  }}
                />
              </div>
            </CardHeader>
            <CardContent className="flex-1 flex flex-col overflow-hidden p-0">
              <div className="flex-1 overflow-y-auto divide-y divide-border/40 p-2 space-y-1">
                {pageItems.map((r) => (
                  <div
                    key={r.urn}
                    onClick={() => setSelectedUrn(r.urn)}
                    className={cn(
                      "p-3 rounded-lg cursor-pointer transition-all border border-transparent",
                      selectedUrn === r.urn
                        ? "bg-primary/5 border-primary/20 text-foreground"
                        : "hover:bg-muted/30 text-muted-foreground hover:text-foreground"
                    )}
                  >
                    <div className="flex justify-between items-start gap-2">
                      <p className={cn("font-medium text-sm truncate", selectedUrn === r.urn ? "text-primary" : "text-foreground")}>
                        {r.name}
                      </p>
                    </div>
                    <p className="mt-1 text-[11px] font-mono truncate text-muted-foreground">
                      {r.urn}
                    </p>
                  </div>
                ))}
                {pageItems.length === 0 && (
                  <div className="py-12 text-center text-sm text-muted-foreground">
                    No results found.
                  </div>
                )}
              </div>
              <div className="p-4 border-t mt-auto">
                <Pagination page={currentPage} pageCount={pageCount} onPageChange={setPage} />
              </div>
            </CardContent>
          </Card>

          {/* Right Column: Entity Detail View */}
          <Card className="lg:col-span-7 flex flex-col overflow-hidden h-full">
            <CardHeader className="pb-3 border-b">
              <CardTitle className="text-base font-semibold">Entity Details</CardTitle>
            </CardHeader>
            <CardContent className="flex-1 overflow-y-auto p-6">
              {selectedItem ? (
                <div className="space-y-6">
                  {/* Entity Summary Header */}
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="flex items-center gap-1 bg-muted/40 text-xs py-0.5 px-2 font-normal">
                        {getEntityIcon(selectedItem.entity_type)}
                        {formatTypeLabel(selectedItem.entity_type)}
                      </Badge>
                      {selectedItem.score > 0 && (
                        <Badge variant="secondary" className="text-xs">
                          Match Score: {selectedItem.score.toFixed(1)}
                        </Badge>
                      )}
                    </div>
                    <h2 className="text-xl font-bold tracking-tight text-foreground">
                      {selectedItem.name}
                    </h2>
                  </div>

                  {/* URN Display & Copy */}
                  <div className="space-y-1.5 rounded-lg border bg-muted/20 p-3.5">
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                        DataHub URN
                      </span>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 px-2 text-xs flex items-center gap-1.5 hover:bg-muted"
                        onClick={() => copyUrn(selectedItem.urn)}
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
                      {selectedItem.urn}
                    </p>
                  </div>

                  {/* Snippet / Context Details */}
                  {selectedItem.snippet && (
                    <div className="space-y-1.5">
                      <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                        Matched Context Snippet
                      </span>
                      <div className="rounded-lg border p-4 bg-muted/10 text-sm leading-relaxed text-foreground whitespace-pre-wrap">
                        {selectedItem.snippet}
                      </div>
                    </div>
                  )}

                  {/* Action Link to DataHub */}
                  {selectedItem.datahub_url && (
                    <div className="pt-2">
                      <a
                        href={selectedItem.datahub_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-2 bg-primary hover:bg-primary/90 text-primary-foreground text-sm font-medium px-4 py-2.5 rounded-lg shadow-sm transition-all"
                      >
                        <ExternalLink className="h-4 w-4" />
                        Open in DataHub Console
                      </a>
                    </div>
                  )}
                </div>
              ) : (
                <div className="h-full flex flex-col justify-center items-center text-center p-6">
                  <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center mb-4">
                    <Database className="h-6 w-6 text-muted-foreground" />
                  </div>
                  <h3 className="text-sm font-semibold text-foreground">No Entity Selected</h3>
                  <p className="text-xs text-muted-foreground mt-1 max-w-xs">
                    Select an entity from the list on the left to view its metadata details and integration parameters.
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
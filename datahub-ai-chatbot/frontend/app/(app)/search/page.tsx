"use client";

import { useState } from "react";
import { SearchIcon, Loader2 } from "lucide-react";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { apiFetch } from "@/lib/api";
import type { SearchResponse } from "@/lib/types";

export default function SearchPage() {
  const [q, setQ] = useState("");
  const [entityType, setEntityType] = useState("");
  const [domain, setDomain] = useState("");
  const [platform, setPlatform] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<SearchResponse | null>(null);

  const run = async () => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({ q: q || "*", limit: "30" });
      if (entityType) params.set("entity_type", entityType);
      if (domain) params.set("domain", domain);
      if (platform) params.set("platform", platform);
      setResult(await apiFetch<SearchResponse>(`/api/v1/search?${params}`));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-4xl space-y-6 p-6">
        <Card>
          <CardContent className="pt-6">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <Label htmlFor="search-q">Tìm kiếm</Label>
                <Input
                  id="search-q"
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  placeholder="vd: sales, customer, revenue…"
                  onKeyDown={(e) => e.key === "Enter" && run()}
                  className="mt-1.5"
                />
              </div>
              <div>
                <Label htmlFor="search-type">Loại entity</Label>
                <select
                  id="search-type"
                  value={entityType}
                  onChange={(e) => setEntityType(e.target.value)}
                  className="mt-1.5 w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-ring"
                >
                  <option value="">Tất cả</option>
                  <option value="dataset">Dataset</option>
                  <option value="dashboard">Dashboard</option>
                  <option value="glossary_term">Glossary</option>
                  <option value="document">Document</option>
                </select>
              </div>
              <div>
                <Label htmlFor="search-domain">Domain</Label>
                <Input id="search-domain" value={domain} onChange={(e) => setDomain(e.target.value)} className="mt-1.5" />
              </div>
              <div className="sm:col-span-2">
                <Label htmlFor="search-platform">Platform</Label>
                <Input id="search-platform" value={platform} onChange={(e) => setPlatform(e.target.value)} className="mt-1.5" />
              </div>
            </div>
            <Button onClick={run} disabled={loading} className="mt-4">
              {loading ? <Loader2 className="animate-spin" /> : <SearchIcon />} Tìm kiếm
            </Button>
          </CardContent>
        </Card>

        {error && <p className="text-sm text-destructive">{error}</p>}

        {result && !loading && (
          <>
            <p className="text-sm text-muted-foreground">
              {result.results.length} kết quả
            </p>
            <div className="space-y-2">
              {result.results.map((r) => (
                <Card key={r.urn}>
                  <CardContent className="flex items-start justify-between gap-3 pt-4">
                    <div className="min-w-0">
                      <p className="truncate font-medium">{r.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {r.entity_type}
                        {r.datahub_url && (
                          <>
                            {" · "}
                            <a href={r.datahub_url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                              Open in DataHub
                            </a>
                          </>
                        )}
                      </p>
                      {r.snippet && <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{r.snippet}</p>}
                    </div>
                    <Badge variant="secondary">{(r.score * 100).toFixed(0)}%</Badge>
                  </CardContent>
                </Card>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
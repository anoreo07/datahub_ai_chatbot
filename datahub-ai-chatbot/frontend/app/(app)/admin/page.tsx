"use client";

import { useCallback, useState } from "react";
import { Loader2, PlugZap } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";

import { RolesPanel } from "./roles-panel";
import { InteractionsPanel } from "./interactions-panel";

const TABS = ["System Operations", "Roles & Permissions", "Interactions"] as const;
type Tab = (typeof TABS)[number];

export default function AdminPage() {
  const [tab, setTab] = useState<Tab>("System Operations");

  return (
    <div className="h-full w-full flex flex-col p-6 overflow-hidden space-y-4">
      {/* Consolidated Admin Tabs */}
      <div className="flex gap-1 rounded-lg border bg-muted/40 p-1 shrink-0">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={cn(
              "flex-1 rounded-md px-3 py-2 text-sm font-medium transition-all",
              tab === t
                ? "bg-background text-foreground shadow-sm border border-border/10"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Panel Area - Fixed Height, Scroll Handled Internally */}
      <div className="flex-1 min-h-0 overflow-hidden flex flex-col">
        {tab === "System Operations" && <SystemOperationsPanel />}
        {tab === "Roles & Permissions" && <RolesPanel />}
        {tab === "Interactions" && <InteractionsPanel />}
      </div>
    </div>
  );
}

function SystemOperationsPanel() {
  return (
    <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-2 gap-6 overflow-y-auto pr-1">
      <div className="space-y-6">
        <DataHubPanel />
        <DocumentsPanel />
      </div>
      <div className="space-y-6">
        <SyncPanel />
        <IndexPanel />
      </div>
    </div>
  );
}

function SyncPanel() {
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<string>("");
  const [urn, setUrn] = useState("");
  const [entityResult, setEntityResult] = useState<string>("");

  const runFull = async () => {
    setRunning(true);
    setResult("");
    try {
      const data = await apiFetch<Record<string, unknown>>("/api/v1/sync/full", { method: "POST" });
      setResult(JSON.stringify(data.results, null, 2));
    } catch (e) {
      setResult((e as Error).message);
    } finally {
      setRunning(false);
    }
  };

  const syncEntity = async () => {
    if (!urn) return;
    setEntityResult("");
    try {
      const data = await apiFetch<Record<string, unknown>>("/api/v1/sync/entity", {
        method: "POST",
        body: JSON.stringify({ urn }),
      });
      setEntityResult(data.changed ? "Changed" : "Up-to-date");
    } catch (e) {
      setEntityResult((e as Error).message);
    }
  };

  return (
    <>
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-semibold">Full Data Sync</CardTitle>
        </CardHeader>
        <CardContent>
          <Button onClick={runFull} disabled={running} className="w-full sm:w-auto">
            {running && <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />} Run Full Sync
          </Button>
          {result && (
            <pre className="mt-3 max-h-[160px] overflow-y-auto overflow-x-auto rounded-lg bg-muted p-3 text-xs font-mono leading-relaxed border">
              {result}
            </pre>
          )}
        </CardContent>
      </Card>
      <Card className="mt-6">
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-semibold">Sync Entity by URN</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2 flex-col sm:flex-row">
            <Input
              value={urn}
              onChange={(e) => setUrn(e.target.value)}
              placeholder="urn:li:dataset:abc"
              className="flex-1 h-9 text-sm"
            />
            <Button onClick={syncEntity} className="h-9 shrink-0">
              Sync Entity
            </Button>
          </div>
          {entityResult && <p className="mt-2 text-xs text-muted-foreground font-mono">{entityResult}</p>}
        </CardContent>
      </Card>
    </>
  );
}

function IndexPanel() {
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState("");

  const rebuild = async () => {
    setRunning(true);
    setResult("");
    try {
      const data = await apiFetch<Record<string, unknown>>("/api/v1/index/rebuild", { method: "POST" });
      setResult(`Index rebuilt: ${data.jobs_created} jobs created`);
    } catch (e) {
      setResult((e as Error).message);
    } finally {
      setRunning(false);
    }
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold">Search Index</CardTitle>
      </CardHeader>
      <CardContent>
        <Button variant="warning" onClick={rebuild} disabled={running} className="w-full sm:w-auto">
          {running && <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />} Rebuild Search Index
        </Button>
        {result && <p className="mt-2.5 text-xs text-muted-foreground font-mono bg-muted/50 p-2 border rounded">{result}</p>}
      </CardContent>
    </Card>
  );
}

function DocumentsPanel() {
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState("");

  const importDoc = async () => {
    if (!url) return;
    setLoading(true);
    setResult("");
    try {
      const params = new URLSearchParams({ url });
      if (title) params.set("title", title);
      const data = await apiFetch<Record<string, unknown>>(`/api/v1/documents/import?${params}`, { method: "POST" });
      setResult(`Imported: ${data.title || data.urn} (${data.chunks} chunks)`);
    } catch (e) {
      setResult((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold">Import Document Reference</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-1">
          <Label htmlFor="doc-url" className="text-xs">Document URL</Label>
          <Input
            id="doc-url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com/document.pdf"
            className="h-9 text-sm"
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="doc-title" className="text-xs">Title (Optional)</Label>
          <Input
            id="doc-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="h-9 text-sm"
          />
        </div>
        <Button onClick={importDoc} disabled={loading} className="w-full sm:w-auto">
          {loading && <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />} Import Document
        </Button>
        {result && <p className="text-xs text-muted-foreground font-mono bg-muted/50 p-2 border rounded">{result}</p>}
      </CardContent>
    </Card>
  );
}

interface DataHubHealth {
  status: string;
  mode: string;
  gms_url?: string;
  latency_ms?: number;
  checked_at?: string;
}

function DataHubPanel() {
  const [checking, setChecking] = useState(false);
  const [health, setHealth] = useState<DataHubHealth | null>(null);
  const [error, setError] = useState("");

  const run = useCallback(async () => {
    setChecking(true);
    setError("");
    try {
      const data = await apiFetch<DataHubHealth>("/api/v1/datasources/datahub/health");
      setHealth(data);
    } catch (e) {
      setError((e as Error).message);
      setHealth({ status: "error", mode: "graphql" });
    } finally {
      setChecking(false);
    }
  }, []);

  const ok = health?.status === "ok";

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0 pb-3">
        <CardTitle className="text-base font-semibold">DataHub Connection</CardTitle>
        <Button onClick={run} disabled={checking} size="sm" className="h-8 px-2">
          {checking ? <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" /> : <PlugZap className="mr-1 h-3.5 w-3.5" />} Ping
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && <p className="text-xs text-destructive bg-destructive/10 p-2 border rounded font-mono">{error}</p>}

        <div className="space-y-2 rounded-lg border p-3 text-xs leading-relaxed">
          <div className="flex items-center justify-between py-1 border-b last:border-0 border-border/40">
            <span className="text-muted-foreground uppercase font-medium">GMS URL</span>
            <span className="font-mono text-foreground font-medium truncate max-w-[200px]">{health?.gms_url || "-"}</span>
          </div>
          <div className="flex items-center justify-between py-1 border-b last:border-0 border-border/40">
            <span className="text-muted-foreground uppercase font-medium">Mode</span>
            <Badge variant="secondary" className="font-normal py-0">{health?.mode === "mock" ? "Mock" : "GraphQL (GMS)"}</Badge>
          </div>
          <div className="flex items-center justify-between py-1 border-b last:border-0 border-border/40">
            <span className="text-muted-foreground uppercase font-medium">Status</span>
            <span className="flex items-center gap-1.5 font-medium">
              {health && (
                <Badge variant={ok ? "success" : "destructive"} className="py-0">{health.status}</Badge>
              )}
              {health?.latency_ms != null && (
                <span className="text-muted-foreground font-mono text-[10px]">({health.latency_ms} ms)</span>
              )}
            </span>
          </div>
          {health?.checked_at && (
            <div className="flex items-center justify-between border-t pt-2 mt-1">
              <span className="text-muted-foreground uppercase font-medium">Last Checked</span>
              <span className="text-muted-foreground font-mono">
                {new Date(health.checked_at).toLocaleString()}
              </span>
            </div>
          )}
        </div>

        {!health && !error && (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground italic">
            <PlugZap className="h-3.5 w-3.5 text-primary" />
            Click Ping to test connections to DataHub GMS instance.
          </div>
        )}
      </CardContent>
    </Card>
  );
}
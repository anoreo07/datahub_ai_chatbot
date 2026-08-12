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

const TABS = ["Sync", "Index", "Documents", "DataHub", "Roles"] as const;
type Tab = (typeof TABS)[number];

export default function AdminPage() {
  const [tab, setTab] = useState<Tab>("Sync");

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl space-y-5 p-6">
        <div className="flex gap-1 rounded-lg border bg-muted/40 p-1">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={cn(
                "flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                tab === t ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
              )}
            >
              {t}
            </button>
          ))}
        </div>
        {tab === "Sync" && <SyncPanel />}
        {tab === "Index" && <IndexPanel />}
        {tab === "Documents" && <DocumentsPanel />}
        {tab === "DataHub" && <DataHubPanel />}
        {tab === "Roles" && <RolesPanel />}
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
        <CardHeader>
          <CardTitle>Full Sync</CardTitle>
        </CardHeader>
        <CardContent>
          <Button onClick={runFull} disabled={running}>
            {running && <Loader2 className="animate-spin" />} Run Full Sync
          </Button>
          {result && (
            <pre className="mt-3 overflow-x-auto rounded-lg bg-muted p-3 text-xs">{result}</pre>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Sync Entity by URN</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input value={urn} onChange={(e) => setUrn(e.target.value)} placeholder="urn:li:dataset:abc" />
            <Button onClick={syncEntity}>Sync</Button>
          </div>
          {entityResult && <p className="mt-2 text-sm text-muted-foreground">{entityResult}</p>}
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
      <CardHeader>
        <CardTitle>Rebuild Index</CardTitle>
      </CardHeader>
      <CardContent>
        <Button variant="warning" onClick={rebuild} disabled={running}>
          {running && <Loader2 className="animate-spin" />} Rebuild Index
        </Button>
        {result && <p className="mt-2 text-sm text-muted-foreground">{result}</p>}
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
      <CardHeader>
        <CardTitle>Import Document</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-1.5">
          <Label htmlFor="doc-url">URL</Label>
          <Input id="doc-url" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://example.com/document.pdf" />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="doc-title">Title (tùy chọn)</Label>
          <Input id="doc-title" value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>
        <Button onClick={importDoc} disabled={loading}>
          {loading && <Loader2 className="animate-spin" />} Import
        </Button>
        {result && <p className="text-sm text-muted-foreground">{result}</p>}
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
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle>Kết nối DataHub</CardTitle>
        <Button onClick={run} disabled={checking} size="sm">
          {checking ? <Loader2 className="animate-spin" /> : <PlugZap />} Kiểm tra kết nối
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && <p className="text-sm text-destructive">{error}</p>}

        <div className="space-y-3 rounded-lg border p-4 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">KẾT NỐI DATAHUB (URL)</span>
            <span className="font-mono font-medium">{health?.gms_url || "-"}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Chế độ</span>
            <Badge variant="secondary">{health?.mode === "mock" ? "Mock" : "GraphQL (GMS)"}</Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Trạng thái</span>
            <span className="flex items-center gap-2">
              {health && (
                <Badge variant={ok ? "success" : "destructive"}>{health.status}</Badge>
              )}
              {health?.latency_ms != null && (
                <span className="text-xs text-muted-foreground">{health.latency_ms} ms</span>
              )}
            </span>
          </div>
          {health?.checked_at && (
            <div className="flex items-center justify-between border-t pt-2">
              <span className="text-muted-foreground">Thời điểm kiểm tra</span>
              <span className="text-xs text-muted-foreground">
                {new Date(health.checked_at).toLocaleString()}
              </span>
            </div>
          )}
        </div>

        {!health && !error && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <PlugZap className="h-4 w-4" />
            Nhấn &ldquo;Kiểm tra kết nối&rdquo; để ping DataHub GMS API.
          </div>
        )}
      </CardContent>
    </Card>
  );
}
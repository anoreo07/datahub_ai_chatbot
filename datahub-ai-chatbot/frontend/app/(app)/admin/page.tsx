"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";

const TABS = ["Sync", "Index", "Documents"] as const;
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
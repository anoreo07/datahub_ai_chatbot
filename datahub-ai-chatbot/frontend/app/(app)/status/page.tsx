"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { RefreshCw, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Pagination } from "@/components/ui/pagination";
import { apiFetch } from "@/lib/api";
import type { HealthResponse, HealthLog, StatsResponse } from "@/lib/types";

const LOGS_PER_PAGE = 8;

export default function StatusPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [logs, setLogs] = useState<HealthLog[]>([]);
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [h, l, s] = await Promise.all([
        apiFetch<HealthResponse>("/ready"),
        apiFetch<{ logs: HealthLog[] }>("/ready/logs?limit=50"),
        apiFetch<StatsResponse>("/api/v1/search/stats"),
      ]);
      setHealth(h);
      setLogs(l.logs || []);
      setStats(s);
      setPage(0);
    } catch {
      /* server may be down in dev without backend */
    } finally {
      setLoading(false);
    }
  }, []);

  const sortedLogs = useMemo(
    () =>
      [...logs].sort(
        (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      ),
    [logs]
  );

  const pageCount = Math.max(1, Math.ceil(sortedLogs.length / LOGS_PER_PAGE));
  const currentPage = Math.min(page, pageCount - 1);
  const pageLogs = sortedLogs.slice(
    currentPage * LOGS_PER_PAGE,
    currentPage * LOGS_PER_PAGE + LOGS_PER_PAGE
  );

  useEffect(() => {
    load();
  }, [load]);

  const tone = (v?: string) =>
    v === "ok" ? "success" : v === "degraded" ? "warning" : "destructive";

  return (
    <div className="h-full w-full flex flex-col p-6 overflow-hidden">
      {loading ? (
        <div className="flex flex-1 items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </div>
      ) : (
        <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-12 gap-6 overflow-hidden">
          {/* Left Column: Health and Stats */}
          <div className="lg:col-span-5 flex flex-col gap-6 overflow-hidden">
            {/* System Health Card */}
            <Card className="flex flex-col min-h-0 flex-1">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
                <CardTitle className="text-lg font-semibold">System Health</CardTitle>
                <Button variant="ghost" size="sm" onClick={load} className="h-8 px-2">
                  <RefreshCw className="mr-1 h-3.5 w-3.5 animate-none" /> Refresh
                </Button>
              </CardHeader>
              <CardContent className="flex-1 overflow-y-auto">
                {health ? (
                  <div className="space-y-3">
                    {Object.entries(health)
                      .filter(([k]) => k !== "status")
                      .map(([k, v]) => (
                        <div key={k} className="flex items-center justify-between text-sm py-1.5 border-b last:border-0 border-border/40">
                          <span className="capitalize text-muted-foreground">{k.replace(/_/g, " ")}</span>
                          <Badge variant={tone(v)}>{String(v)}</Badge>
                        </div>
                      ))}
                    <div className="mt-4 flex items-center justify-between border-t pt-3 text-sm font-medium">
                      <span>Overall Status</span>
                      <Badge variant={tone(health.status)} className="px-3 py-0.5">{health.status}</Badge>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">Không kết nối được backend.</p>
                )}
              </CardContent>
            </Card>

            {/* Quick Stats Card */}
            {stats && (
              <Card className="shrink-0">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg font-semibold">Quick Stats</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-5 gap-2">
                    {[
                      { label: "Datasets", value: stats.dataset },
                      { label: "Dashboards", value: stats.dashboard },
                      { label: "Glossary", value: stats.glossary_term },
                      { label: "Documents", value: stats.document },
                      { label: "Total", value: stats.total },
                    ].map((s) => (
                      <div key={s.label} className="rounded-lg border p-2 text-center bg-muted/20">
                        <p className="text-lg font-bold">{s.value}</p>
                        <p className="text-[9px] text-muted-foreground uppercase tracking-wider mt-0.5 font-medium truncate">
                          {s.label === "glossary_term" ? "Glossary" : s.label}
                        </p>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Right Column: Healthcheck Logs */}
          <Card className="lg:col-span-7 flex flex-col overflow-hidden h-full">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg font-semibold">Healthcheck Logs</CardTitle>
            </CardHeader>
            <CardContent className="flex-1 flex flex-col overflow-hidden pb-4">
              <div className="flex-1 overflow-y-auto pr-1">
                <table className="w-full text-left text-sm border-collapse">
                  <thead className="sticky top-0 bg-background z-10">
                    <tr className="border-b text-xs text-muted-foreground bg-background">
                      <th className="pb-2 font-medium">Thời gian</th>
                      <th className="pb-2 font-medium">Trạng thái</th>
                      <th className="pb-2 font-medium">Thời gian chạy</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/40">
                    {pageLogs.map((l, i) => (
                      <tr key={i} className="hover:bg-muted/10">
                        <td className="py-2.5 text-xs text-muted-foreground">
                          {new Date(l.timestamp).toLocaleString()}
                        </td>
                        <td className="py-2.5">
                          <Badge variant={tone(l.status)} className="text-[10px] px-1.5 py-0 font-normal">
                            {l.status}
                          </Badge>
                        </td>
                        <td className="py-2.5 text-xs font-mono">
                          {l.duration_ms != null ? `${l.duration_ms} ms` : "-"}
                        </td>
                      </tr>
                    ))}
                    {pageLogs.length === 0 && (
                      <tr>
                        <td colSpan={3} className="py-8 text-center text-muted-foreground text-sm">
                          Chưa có healthcheck nào.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              <div className="border-t pt-2 mt-auto">
                <Pagination
                  page={currentPage}
                  pageCount={pageCount}
                  onPageChange={setPage}
                  showTotal
                  total={sortedLogs.length}
                />
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
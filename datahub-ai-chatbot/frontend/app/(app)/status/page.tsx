"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { RefreshCw, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Pagination } from "@/components/ui/pagination";
import { apiFetch } from "@/lib/api";
import type { HealthResponse, HealthLog, StatsResponse } from "@/lib/types";

const LOGS_PER_PAGE = 10;

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
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-4xl space-y-5 p-6">
        {loading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        ) : (
          <>
            <Card>
              <CardHeader className="flex-row items-center justify-between">
                <CardTitle>System Health</CardTitle>
                <Button variant="ghost" size="sm" onClick={load}>
                  <RefreshCw /> Refresh
                </Button>
              </CardHeader>
              <CardContent>
                {health ? (
                  <div className="space-y-2">
                    {Object.entries(health)
                      .filter(([k]) => k !== "status")
                      .map(([k, v]) => (
                        <div key={k} className="flex items-center justify-between text-sm">
                          <span>{k}</span>
                          <Badge variant={tone(v)}>{String(v)}</Badge>
                        </div>
                      ))}
                    <div className="mt-2 flex items-center gap-2 border-t pt-2 text-sm font-medium">
                      Overall
                      <Badge variant={tone(health.status)}>{health.status}</Badge>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">Không kết nối được backend.</p>
                )}
              </CardContent>
            </Card>

            {stats && (
              <Card>
                <CardHeader>
                  <CardTitle>Quick Stats</CardTitle>
                </CardHeader>
                <CardContent className="grid grid-cols-2 gap-3 sm:grid-cols-5">
                  {[
                    { label: "Datasets", value: stats.dataset },
                    { label: "Dashboards", value: stats.dashboard },
                    { label: "Glossary", value: stats.glossary_term },
                    { label: "Documents", value: stats.document },
                    { label: "Total", value: stats.total },
                  ].map((s) => (
                    <div key={s.label} className="rounded-lg border p-3 text-center">
                      <p className="text-2xl font-semibold">{s.value}</p>
                      <p className="text-xs text-muted-foreground">{s.label}</p>
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}

            <Card>
              <CardHeader>
                <CardTitle>Healthcheck Logs</CardTitle>
              </CardHeader>
              <CardContent className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b text-xs text-muted-foreground">
                      <th className="pb-2">Thời gian</th>
                      <th className="pb-2">Trạng thái</th>
                      <th className="pb-2">Thời gian chạy</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pageLogs.map((l, i) => (
                      <tr key={i} className="border-b last:border-0">
                        <td className="py-2">{new Date(l.timestamp).toLocaleString()}</td>
                        <td className="py-2">
                          <Badge variant={tone(l.status)}>{l.status}</Badge>
                        </td>
                        <td className="py-2">{l.duration_ms != null ? `${l.duration_ms} ms` : "-"}</td>
                      </tr>
                    ))}
                    {pageLogs.length === 0 && (
                      <tr>
                        <td colSpan={3} className="py-4 text-center text-muted-foreground">
                          Chưa có healthcheck nào.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
                <Pagination
                  page={currentPage}
                  pageCount={pageCount}
                  onPageChange={setPage}
                  showTotal
                  total={sortedLogs.length}
                />
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </div>
  );
}
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Eye, History as HistoryIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyState, RunStatusPill } from "@/components/shared/bits";
import { api, fmtDateTime } from "@/lib/api";

export default function HistoryPage() {
  const navigate = useNavigate();
  const [runs, setRuns] = useState([]);
  const [statusFilter, setStatusFilter] = useState("all");
  const [loaded, setLoaded] = useState(false);

  const load = useCallback(async () => {
    try {
      const params = statusFilter !== "all" ? { status: statusFilter } : {};
      const res = await api.get("/runs", { params: { limit: 50, ...params } });
      setRuns(res.data);
    } catch { /* noop */ } finally {
      setLoaded(true);
    }
  }, [statusFilter]);

  useEffect(() => {
    load();
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, [load]);

  if (!loaded) return <div className="py-24 text-center text-sm text-muted-foreground">Loading…</div>;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-display text-xl font-semibold">Run history</h2>
          <p className="mt-1 text-sm text-muted-foreground">All pipeline executions with status, duration, and QA flags.</p>
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger data-testid="run-history-filter-status-select" className="w-48 bg-secondary/40">
            <SelectValue placeholder="Filter status" />
          </SelectTrigger>
          <SelectContent className="border-border bg-popover">
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="ready">Ready</SelectItem>
            <SelectItem value="ready_with_warnings">Ready · warnings</SelectItem>
            <SelectItem value="running">Running</SelectItem>
            <SelectItem value="failed">Failed</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {runs.length === 0 ? (
        <EmptyState
          icon={HistoryIcon}
          title="No runs found"
          message={statusFilter !== "all" ? "No runs match this filter." : "Trigger your first pipeline run to see history here."}
          actionLabel="Go to pipeline"
          onAction={() => navigate("/runs")}
          actionTestId="history-goto-pipeline-button"
        />
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table data-testid="run-history-table">
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Started</TableHead>
                  <TableHead className="hidden sm:table-cell">Run ID</TableHead>
                  <TableHead className="hidden md:table-cell">Market date</TableHead>
                  <TableHead>Trigger</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Duration</TableHead>
                  <TableHead className="text-right">QA flags</TableHead>
                  <TableHead className="w-16" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {runs.map((r) => (
                  <TableRow key={r.id} className="hover:bg-accent/40">
                    <TableCell className="text-sm">{fmtDateTime(r.started_at)}</TableCell>
                    <TableCell className="hidden font-mono text-xs text-muted-foreground sm:table-cell">{r.id?.slice(0, 8)}</TableCell>
                    <TableCell className="hidden font-mono text-xs md:table-cell">{r.market_date || "—"}</TableCell>
                    <TableCell className="text-xs capitalize text-muted-foreground">{r.trigger}</TableCell>
                    <TableCell><RunStatusPill status={r.status} /></TableCell>
                    <TableCell className="text-right font-mono tabular-nums text-sm">{r.duration_seconds != null ? `${r.duration_seconds}s` : "—"}</TableCell>
                    <TableCell className="text-right font-mono tabular-nums text-sm">{(r.qa_flags || []).length}</TableCell>
                    <TableCell>
                      <Button
                        data-testid={`run-history-view-${r.id?.slice(0, 8)}`}
                        variant="ghost"
                        size="icon"
                        aria-label="View run"
                        onClick={() => navigate(`/runs?run_id=${r.id}`)}
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

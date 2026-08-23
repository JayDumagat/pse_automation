import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Copy, ImagePlay, PlayCircle, RefreshCcw, TriangleAlert } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { PipelineStageRail } from "@/components/runs/PipelineStageRail";
import { EmptyState, RunStatusPill } from "@/components/shared/bits";
import { api, fmtDateTime } from "@/lib/api";

export default function RunsPage() {
  const [searchParams] = useSearchParams();
  const runIdParam = searchParams.get("run_id");
  const [run, setRun] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [regenerating, setRegenerating] = useState(null);

  const load = useCallback(async () => {
    try {
      const res = runIdParam
        ? await api.get(`/runs/${runIdParam}`)
        : await api.get("/runs/latest");
      setRun(res.data);
    } catch { /* noop */ } finally {
      setLoaded(true);
    }
  }, [runIdParam]);

  useEffect(() => {
    load();
    const id = setInterval(load, 2500);
    return () => clearInterval(id);
  }, [load]);

  const trigger = async () => {
    setTriggering(true);
    try {
      await api.post("/runs/trigger");
      toast.success("Pipeline started");
      setTimeout(load, 500);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to start run");
    } finally {
      setTriggering(false);
    }
  };

  const regenerate = async (target) => {
    if (!run) return;
    setRegenerating(target);
    try {
      await api.post(`/runs/${run.id}/regenerate`, { target });
      toast.success(`${target === "graphics" ? "Graphics" : "Captions"} regenerated`);
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Regeneration failed");
    } finally {
      setRegenerating(null);
    }
  };

  const copyError = (text) => {
    navigator.clipboard.writeText(text);
    toast.success("Error copied to clipboard");
  };

  if (!loaded) return <div className="py-24 text-center text-sm text-muted-foreground">Loading…</div>;

  if (!run) {
    return (
      <EmptyState
        icon={ImagePlay}
        title="No pipeline runs yet"
        message="Start the daily pipeline: fetch PSE data, validate, compute, render graphics, and generate captions."
        actionLabel={triggering ? "Starting…" : "Trigger run"}
        onAction={trigger}
        actionTestId="runs-first-trigger-button"
        loading={triggering}
      />
    );
  }

  const isRunning = run.status === "running";
  const hasSnapshot = run.stages?.find((s) => s.name === "store")?.status === "success";

  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="flex flex-wrap items-center justify-between gap-4 p-6">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="font-display text-xl font-semibold">Daily pipeline</h2>
              <RunStatusPill status={run.status} testId="runs-status-pill" />
            </div>
            <div className="mt-1 font-mono text-xs text-muted-foreground">
              run {run.id?.slice(0, 8)} · {run.trigger} · started {fmtDateTime(run.started_at)}
              {run.duration_seconds ? ` · ${run.duration_seconds}s` : ""}
              {run.market_date ? ` · market date ${run.market_date}` : ""}
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button data-testid="trigger-run-button" onClick={trigger} disabled={triggering || isRunning}>
              <PlayCircle className="mr-1.5 h-4 w-4" />
              {isRunning ? "Running…" : "Trigger run"}
            </Button>
            <Button
              data-testid="regenerate-graphics-button"
              variant="secondary"
              disabled={!hasSnapshot || isRunning || regenerating !== null}
              onClick={() => regenerate("graphics")}
            >
              <RefreshCcw className={`mr-1.5 h-4 w-4 ${regenerating === "graphics" ? "animate-spin" : ""}`} />
              Regenerate graphics
            </Button>
            <Button
              data-testid="regenerate-captions-button"
              variant="secondary"
              disabled={!hasSnapshot || isRunning || regenerating !== null}
              onClick={() => regenerate("captions")}
            >
              <RefreshCcw className={`mr-1.5 h-4 w-4 ${regenerating === "captions" ? "animate-spin" : ""}`} />
              Regenerate captions
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="font-display text-base">Stages</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <PipelineStageRail stages={run.stages || []} />
          <Table data-testid="stage-detail-table">
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead>Stage</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Duration</TableHead>
                <TableHead className="hidden md:table-cell">Details</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(run.stages || []).map((st) => (
                <TableRow key={st.name} className="hover:bg-accent/40">
                  <TableCell className="font-medium capitalize">{st.name}</TableCell>
                  <TableCell>
                    <Badge
                      variant="outline"
                      className={
                        st.status === "success"
                          ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-300"
                          : st.status === "warning"
                          ? "border-amber-400/30 bg-amber-400/10 text-amber-300"
                          : st.status === "failed"
                          ? "border-rose-400/30 bg-rose-400/10 text-rose-300"
                          : st.status === "running"
                          ? "border-sky-400/30 bg-sky-400/10 text-sky-300"
                          : "border-border text-muted-foreground"
                      }
                    >
                      {st.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right font-mono tabular-nums text-muted-foreground">
                    {st.duration_seconds != null ? `${st.duration_seconds}s` : "—"}
                  </TableCell>
                  <TableCell className="hidden md:table-cell">
                    {st.error ? (
                      <span className="inline-flex items-center gap-2 text-xs text-rose-300">
                        <span className="max-w-[380px] truncate">{st.error}</span>
                        <Button variant="ghost" size="icon" className="h-6 w-6" aria-label="Copy error" onClick={() => copyError(st.error)}>
                          <Copy className="h-3 w-3" />
                        </Button>
                      </span>
                    ) : (
                      <span className="font-mono text-xs text-muted-foreground">
                        {st.meta && Object.keys(st.meta).length > 0
                          ? Object.entries(st.meta).map(([k, v]) => `${k}: ${v}`).join(" · ")
                          : "—"}
                      </span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {(run.qa_flags || []).length > 0 && (
        <Card data-testid="qa-flags-card">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 font-display text-base">
              <TriangleAlert className="h-4 w-4 text-amber-400" /> QA flags ({run.qa_flags.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {run.qa_flags.map((f, i) => (
              <div key={i} className={`rounded-lg border p-3 text-sm ${f.severity === "error" ? "border-rose-400/30 bg-rose-400/10 text-rose-200" : "border-amber-400/30 bg-amber-400/10 text-amber-200"}`}>
                <span className="font-mono text-xs uppercase opacity-70">[{f.check}]</span> {f.message}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {run.error && (
        <Card className="border-rose-400/30">
          <CardContent className="p-4 text-sm text-rose-300" data-testid="run-error-message">
            {run.error}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

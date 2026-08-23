import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowRight, BanknoteArrowUp, CalendarClock, LineChart, PlayCircle, TriangleAlert,
} from "lucide-react";
import { toast } from "sonner";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Delta, EmptyState, RunStatusPill, SectionTitle } from "@/components/shared/bits";
import { api, fmtDateTime, fmtLongDate, fmtNum, pesoShort } from "@/lib/api";

const MoversTable = ({ rows, mode, testId }) => (
  <Table data-testid={testId}>
    <TableHeader>
      <TableRow className="hover:bg-transparent">
        <TableHead className="w-10">#</TableHead>
        <TableHead>Symbol</TableHead>
        <TableHead className="hidden md:table-cell">Name</TableHead>
        <TableHead className="text-right">Price</TableHead>
        <TableHead className="text-right">{mode === "active" ? "Value traded" : "Change"}</TableHead>
      </TableRow>
    </TableHeader>
    <TableBody>
      {rows.length === 0 && (
        <TableRow>
          <TableCell colSpan={5} className="py-8 text-center text-muted-foreground">No data</TableCell>
        </TableRow>
      )}
      {rows.map((q, i) => (
        <TableRow key={q.symbol} className="hover:bg-accent/40">
          <TableCell className="text-muted-foreground">{i + 1}</TableCell>
          <TableCell className="font-mono font-semibold">{q.symbol}</TableCell>
          <TableCell className="hidden max-w-[220px] truncate text-muted-foreground md:table-cell">{q.name}</TableCell>
          <TableCell className="text-right font-mono tabular-nums">₱{fmtNum(q.price)}</TableCell>
          <TableCell className="text-right">
            {mode === "active" ? (
              <span className="font-mono tabular-nums">{pesoShort(q.value_traded)}</span>
            ) : (
              <Delta value={q.percent_change} />
            )}
          </TableCell>
        </TableRow>
      ))}
    </TableBody>
  </Table>
);

export default function DashboardPage() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const [triggering, setTriggering] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await api.get("/market/latest");
      setData(res.data);
    } catch { /* noop */ } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, [load]);

  const triggerRun = async () => {
    setTriggering(true);
    try {
      await api.post("/runs/trigger");
      toast.success("Pipeline started");
      navigate("/runs");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to start run");
    } finally {
      setTriggering(false);
    }
  };

  if (!loaded) {
    return <div className="py-24 text-center text-sm text-muted-foreground">Loading market data…</div>;
  }

  const snap = data?.snapshot;
  if (!snap) {
    return (
      <EmptyState
        icon={LineChart}
        title="No market data yet"
        message="Trigger your first pipeline run to fetch live PSE data, compute the market summary, and generate today's social graphics."
        actionLabel={triggering ? "Starting…" : "Run first pipeline"}
        onAction={triggerRun}
        actionTestId="dashboard-first-run-button"
        loading={triggering}
      />
    );
  }

  const s = snap.summary;
  const run = data.latest_run;

  return (
    <div className="space-y-6">
      {data.market_closed && (
        <Alert data-testid="market-closed-banner" className="border-amber-400/30 bg-amber-400/10">
          <TriangleAlert className="h-4 w-4 text-amber-400" />
          <AlertTitle className="text-amber-300">Market closed</AlertTitle>
          <AlertDescription className="text-amber-200/80">
            Showing last trading day — {fmtLongDate(s.market_date)}.
          </AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <div className="space-y-6 lg:col-span-8">
          {/* PSEi hero */}
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
            <Card className="hero-wash relative overflow-hidden">
              <CardContent className="p-6">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <SectionTitle>PSEi · {fmtLongDate(s.market_date)}</SectionTitle>
                    <div data-testid="psei-hero-value" className="mt-2 font-display text-5xl font-bold tracking-tight sm:text-6xl">
                      {fmtNum(s.psei_value)}
                    </div>
                    <div className="mt-2 flex items-baseline gap-3 text-lg">
                      <Delta value={s.change_points} suffix=" pts" testId="psei-hero-change-points" />
                      <Delta value={s.change_percent} testId="psei-hero-change-percent" />
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-2 text-right">
                    <div className="text-xs text-muted-foreground">Approx. value turnover</div>
                    <div data-testid="turnover-value" className="font-mono text-2xl font-semibold tabular-nums">{pesoShort(s.approx_value_turnover)}</div>
                    <div className="text-[11px] text-muted-foreground/70">as of {fmtDateTime(snap.as_of)}</div>
                  </div>
                </div>
                <div className="mt-5 flex flex-wrap gap-2">
                  <span data-testid="breadth-advancers" className="rounded-full border border-emerald-400/30 bg-emerald-400/10 px-3 py-1 text-xs font-medium text-emerald-300">
                    {s.advancers} advancers
                  </span>
                  <span data-testid="breadth-decliners" className="rounded-full border border-rose-400/30 bg-rose-400/10 px-3 py-1 text-xs font-medium text-rose-300">
                    {s.decliners} decliners
                  </span>
                  <span data-testid="breadth-unchanged" className="rounded-full border border-border bg-secondary px-3 py-1 text-xs font-medium text-muted-foreground">
                    {s.unchanged} unchanged
                  </span>
                  <span className="rounded-full border border-border bg-secondary px-3 py-1 text-xs font-medium text-muted-foreground">
                    {s.total_quotes} securities
                  </span>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Sectors */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="font-display text-base">Sector performance</CardTitle>
            </CardHeader>
            <CardContent>
              <div data-testid="sector-strip" className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
                {(snap.sectors || []).map((sec) => {
                  const up = sec.change_percent >= 0;
                  const maxAbs = Math.max(...snap.sectors.map((x) => Math.abs(x.change_percent)), 0.01);
                  const w = Math.max(8, (Math.abs(sec.change_percent) / maxAbs) * 100);
                  return (
                    <div key={sec.name} data-testid={`sector-card-${sec.name.replace(/[^a-z]/gi, "-").toLowerCase()}`} className="rounded-lg border border-border bg-secondary/40 p-3">
                      <div className="truncate text-xs font-medium text-muted-foreground">{sec.name}</div>
                      <div className="mt-1"><Delta value={sec.change_percent} className="text-sm" /></div>
                      <div className="mt-0.5 font-mono text-[11px] tabular-nums text-muted-foreground/70">{fmtNum(sec.value)}</div>
                      <div className="mt-2 h-1 overflow-hidden rounded-full bg-border">
                        <div className={`h-full rounded-full ${up ? "bg-gain" : "bg-loss"}`} style={{ width: `${w}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Movers */}
          <Card>
            <CardHeader className="pb-0">
              <CardTitle className="font-display text-base">Top movers</CardTitle>
            </CardHeader>
            <CardContent className="pt-4">
              <Tabs defaultValue="gainers">
                <TabsList>
                  <TabsTrigger data-testid="movers-tab-gainers" value="gainers">Gainers</TabsTrigger>
                  <TabsTrigger data-testid="movers-tab-losers" value="losers">Losers</TabsTrigger>
                  <TabsTrigger data-testid="movers-tab-active" value="active">Most active</TabsTrigger>
                </TabsList>
                <TabsContent value="gainers"><MoversTable rows={snap.gainers || []} mode="gain" testId="gainers-table" /></TabsContent>
                <TabsContent value="losers"><MoversTable rows={snap.losers || []} mode="loss" testId="losers-table" /></TabsContent>
                <TabsContent value="active"><MoversTable rows={snap.actives || []} mode="active" testId="actives-table" /></TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </div>

        {/* Right rail */}
        <div className="space-y-6 lg:col-span-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center justify-between font-display text-base">
                Latest run
                <RunStatusPill status={run ? run.status : "idle"} testId="dashboard-run-status" />
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="text-xs text-muted-foreground">
                {run ? (
                  <>Started {fmtDateTime(run.started_at)}{run.duration_seconds ? ` · ${run.duration_seconds}s` : ""} · {run.trigger}</>
                ) : (
                  "No runs yet"
                )}
              </div>
              <div className="flex gap-2">
                <Button data-testid="dashboard-trigger-run-button" size="sm" onClick={triggerRun} disabled={triggering || run?.status === "running"}>
                  <PlayCircle className="mr-1.5 h-4 w-4" />
                  {run?.status === "running" ? "Running…" : "Run pipeline"}
                </Button>
                <Button data-testid="dashboard-view-pipeline-button" size="sm" variant="secondary" onClick={() => navigate("/runs")}>
                  View pipeline <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 font-display text-base">
                <BanknoteArrowUp className="h-4 w-4 text-emerald-400" /> Dividend declarations
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div data-testid="dividends-list" className="space-y-3">
                {(snap.dividends || []).filter((d) => d.company).slice(0, 6).map((d) => (
                  <div key={d.edge_no} className="rounded-lg border border-border bg-secondary/40 p-3">
                    <div className="text-sm font-medium">{d.company}</div>
                    <div className="mt-1 text-xs text-muted-foreground">
                      {d.rate ? `₱${d.rate}/share · ` : ""}
                      {d.ex_date ? `Ex ${d.ex_date}` : d.disclosure_date}
                      {d.payment_date ? ` · Pay ${d.payment_date}` : ""}
                    </div>
                  </div>
                ))}
                {(snap.dividends || []).filter((d) => d.company).length === 0 && (
                  <div className="flex items-center gap-2 rounded-lg border border-dashed border-border p-4 text-xs text-muted-foreground">
                    <CalendarClock className="h-4 w-4" /> No enriched dividend disclosures
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="font-display text-base">REIT board</CardTitle>
            </CardHeader>
            <CardContent>
              <Table data-testid="reit-table">
                <TableBody>
                  {(snap.reits || []).map((q) => (
                    <TableRow key={q.symbol} className="hover:bg-accent/40">
                      <TableCell className="py-2 font-mono font-semibold">{q.symbol}</TableCell>
                      <TableCell className="py-2 text-right font-mono tabular-nums">₱{fmtNum(q.price)}</TableCell>
                      <TableCell className="py-2 text-right"><Delta value={q.percent_change} /></TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

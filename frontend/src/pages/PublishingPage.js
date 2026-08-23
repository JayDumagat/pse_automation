import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CheckCheck, Clock, Facebook, Instagram, Linkedin, Send, Twitter, Undo2, Upload } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { EmptyState } from "@/components/shared/bits";
import { api, fmtDateTime, PLATFORM_LABELS } from "@/lib/api";

const ICONS = { instagram: Instagram, facebook: Facebook, linkedin: Linkedin, x: Twitter };

const StatusBadge = ({ status }) => {
  const map = {
    pending: { label: "Pending", cls: "border-border bg-secondary text-muted-foreground", Icon: Clock },
    exported: { label: "Exported", cls: "border-sky-400/30 bg-sky-400/10 text-sky-300", Icon: Upload },
    published: { label: "Published", cls: "border-emerald-400/30 bg-emerald-400/10 text-emerald-300", Icon: CheckCheck },
  };
  const m = map[status] || map.pending;
  return (
    <Badge variant="outline" className={`gap-1.5 ${m.cls}`}>
      <m.Icon className="h-3 w-3" /> {m.label}
    </Badge>
  );
};

export default function PublishingPage() {
  const navigate = useNavigate();
  const [run, setRun] = useState(null);
  const [records, setRecords] = useState([]);
  const [notes, setNotes] = useState({});
  const [loaded, setLoaded] = useState(false);

  const load = useCallback(async () => {
    try {
      const runRes = await api.get("/runs/latest");
      setRun(runRes.data);
      if (runRes.data?.id) {
        const pRes = await api.get(`/runs/${runRes.data.id}/publishing`);
        setRecords(pRes.data);
        setNotes((n) => {
          const next = { ...n };
          pRes.data.forEach((r) => {
            if (next[r.platform] === undefined) next[r.platform] = r.note || "";
          });
          return next;
        });
      }
    } catch { /* noop */ } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const setStatus = async (platform, status) => {
    try {
      const res = await api.post("/publish", { run_id: run.id, platform, status, note: notes[platform] || "" });
      setRecords((rs) => rs.map((r) => (r.platform === platform ? res.data : r)));
      toast.success(`${PLATFORM_LABELS[platform]} marked ${status}`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to update status");
    }
  };

  if (!loaded) return <div className="py-24 text-center text-sm text-muted-foreground">Loading…</div>;

  if (!run || records.length === 0) {
    return (
      <EmptyState
        icon={Send}
        title="Nothing to publish yet"
        message="Complete a pipeline run first — publishing records are created when a run is ready for review."
        actionLabel="Go to pipeline"
        onAction={() => navigate("/runs")}
        actionTestId="publishing-goto-pipeline-button"
      />
    );
  }

  const order = ["instagram", "facebook", "linkedin", "x"];
  const sorted = [...records].sort((a, b) => order.indexOf(a.platform) - order.indexOf(b.platform));

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-xl font-semibold">Review &amp; export</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Social APIs are not connected yet — download graphics, copy captions, then track posting status per platform here.
        </p>
      </div>
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        {sorted.map((r) => {
          const Icon = ICONS[r.platform] || Send;
          return (
            <Card key={r.platform} data-testid={`publishing-card-${r.platform}`}>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center justify-between font-display text-base">
                  <span className="flex items-center gap-2">
                    <Icon className="h-4 w-4 text-muted-foreground" /> {PLATFORM_LABELS[r.platform]}
                  </span>
                  <StatusBadge status={r.status} />
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="text-xs text-muted-foreground">Last update: {fmtDateTime(r.updated_at)}</div>
                <Input
                  data-testid={`publishing-${r.platform}-note-input`}
                  value={notes[r.platform] || ""}
                  onChange={(e) => setNotes((n) => ({ ...n, [r.platform]: e.target.value }))}
                  placeholder="Operator note (optional, saved with status)"
                  className="bg-secondary/40"
                />
                <div className="flex flex-wrap gap-2">
                  <Button
                    data-testid={`publishing-${r.platform}-mark-exported-button`}
                    size="sm"
                    variant="secondary"
                    disabled={r.status !== "pending"}
                    onClick={() => setStatus(r.platform, "exported")}
                  >
                    <Upload className="mr-1.5 h-3.5 w-3.5" /> Mark exported
                  </Button>
                  <Button
                    data-testid={`publishing-${r.platform}-mark-published-button`}
                    size="sm"
                    disabled={r.status === "published"}
                    onClick={() => setStatus(r.platform, "published")}
                  >
                    <CheckCheck className="mr-1.5 h-3.5 w-3.5" /> Mark published
                  </Button>
                  {r.status !== "pending" && (
                    <Button
                      data-testid={`publishing-${r.platform}-reset-button`}
                      size="sm"
                      variant="ghost"
                      onClick={() => setStatus(r.platform, "pending")}
                    >
                      <Undo2 className="mr-1.5 h-3.5 w-3.5" /> Reset
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

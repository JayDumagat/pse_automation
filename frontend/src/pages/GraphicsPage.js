import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Download, Image as ImageIcon, Maximize2 } from "lucide-react";
import { toast } from "sonner";
import { AspectRatio } from "@/components/ui/aspect-ratio";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { EmptyState } from "@/components/shared/bits";
import { API, api, GRAPHIC_LABELS } from "@/lib/api";

const PngCard = ({ g, runId, onApprove }) => {
  const [imgLoaded, setImgLoaded] = useState(false);
  const src = `${API}/graphics/file/${runId}/${g.type}`;
  const dlHref = `${src}?download=true`;
  return (
    <Card data-testid={`graphic-card-${g.type}`} className="overflow-hidden">
      <div className="relative bg-secondary/40">
        <AspectRatio ratio={4 / 5}>
          {!imgLoaded && <Skeleton className="absolute inset-0" />}
          <img
            src={src}
            alt={GRAPHIC_LABELS[g.type] || g.type}
            onLoad={() => setImgLoaded(true)}
            className="h-full w-full object-cover"
            data-testid={`graphic-image-${g.type}`}
          />
        </AspectRatio>
        <Dialog>
          <DialogTrigger asChild>
            <Button
              data-testid={`graphic-expand-${g.type}`}
              variant="secondary"
              size="icon"
              aria-label="Open full preview"
              className="absolute right-3 top-3 h-8 w-8 bg-background/80 backdrop-blur"
            >
              <Maximize2 className="h-4 w-4" />
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl border-border bg-popover p-4">
            <DialogTitle className="font-display">{GRAPHIC_LABELS[g.type]}</DialogTitle>
            <img src={src} alt={g.type} className="w-full rounded-lg" />
          </DialogContent>
        </Dialog>
      </div>
      <CardContent className="space-y-3 p-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="font-display text-sm font-semibold">{GRAPHIC_LABELS[g.type] || g.type}</div>
            <div className="font-mono text-[11px] text-muted-foreground">
              {g.width}×{g.height} · {Math.round((g.size_bytes || 0) / 1024)} KB
            </div>
          </div>
          <label className="flex items-center gap-2 text-xs text-muted-foreground">
            Approved
            <Switch
              data-testid={`graphic-approve-${g.type}`}
              checked={!!g.approved}
              onCheckedChange={(v) => onApprove(g.type, v)}
            />
          </label>
        </div>
        <Button data-testid={`graphics-${g.type}-download-button`} asChild size="sm" className="w-full">
          <a href={dlHref} download={`pse-daily-${g.type}.png`}>
            <Download className="mr-1.5 h-4 w-4" /> Download PNG
          </a>
        </Button>
      </CardContent>
    </Card>
  );
};

export default function GraphicsPage() {
  const navigate = useNavigate();
  const [run, setRun] = useState(null);
  const [graphics, setGraphics] = useState([]);
  const [loaded, setLoaded] = useState(false);

  const load = useCallback(async () => {
    try {
      const runRes = await api.get("/runs/latest");
      setRun(runRes.data);
      if (runRes.data?.id) {
        const gRes = await api.get(`/runs/${runRes.data.id}/graphics`);
        setGraphics(gRes.data);
      }
    } catch { /* noop */ } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, [load]);

  const approve = async (gtype, approved) => {
    try {
      await api.patch(`/graphics/${run.id}/${gtype}/approve`, { approved });
      setGraphics((gs) => gs.map((g) => (g.type === gtype ? { ...g, approved } : g)));
      toast.success(`${GRAPHIC_LABELS[gtype]} ${approved ? "approved" : "unapproved"}`);
    } catch {
      toast.error("Failed to update approval");
    }
  };

  const downloadAll = () => {
    graphics.forEach((g, i) => {
      setTimeout(() => {
        const a = document.createElement("a");
        a.href = `${API}/graphics/file/${run.id}/${g.type}?download=true`;
        a.download = `pse-daily-${g.type}.png`;
        document.body.appendChild(a);
        a.click();
        a.remove();
      }, i * 400);
    });
    toast.success("Downloading all graphics…");
  };

  if (!loaded) return <div className="py-24 text-center text-sm text-muted-foreground">Loading…</div>;

  if (!run || graphics.length === 0) {
    return (
      <EmptyState
        icon={ImageIcon}
        title="No graphics yet"
        message={run?.status === "running" ? "Pipeline is running — graphics will appear once rendered." : "Run the pipeline to render today's 5 social graphics from live PSE data."}
        actionLabel="Go to pipeline"
        onAction={() => navigate("/runs")}
        actionTestId="graphics-goto-pipeline-button"
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-display text-xl font-semibold">Generated graphics</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {graphics.length} graphics · 1080×1350 · market date {run.market_date || "—"}
          </p>
        </div>
        <Button data-testid="graphics-download-all-button" variant="secondary" onClick={downloadAll}>
          <Download className="mr-1.5 h-4 w-4" /> Download all
        </Button>
      </div>
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-3">
        {graphics.map((g) => (
          <PngCard key={g.type} g={g} runId={run.id} onApprove={approve} />
        ))}
      </div>
    </div>
  );
}

import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Check, Copy, MessageSquareText, RefreshCcw, Save } from "lucide-react";
import { toast } from "sonner";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { EmptyState } from "@/components/shared/bits";
import { api, PLATFORM_LABELS, timeAgo } from "@/lib/api";

const CaptionCard = ({ caption, runId, onUpdated }) => {
  const [text, setText] = useState(caption.text || "");
  const [saving, setSaving] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const dirty = text !== caption.text;

  useEffect(() => setText(caption.text || ""), [caption.text]);

  const save = async () => {
    setSaving(true);
    try {
      const res = await api.put(`/runs/${runId}/captions/${caption.platform}`, { text });
      onUpdated(res.data);
      toast.success("Caption saved");
    } catch {
      toast.error("Failed to save caption");
    } finally {
      setSaving(false);
    }
  };

  const copy = async () => {
    await navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard");
  };

  const regenerate = async () => {
    setRegenerating(true);
    try {
      const res = await api.post(`/runs/${runId}/captions/${caption.platform}/regenerate`);
      onUpdated(res.data);
      toast.success("Caption regenerated");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Regeneration failed");
    } finally {
      setRegenerating(false);
    }
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-wrap items-center justify-between gap-2 font-display text-base">
          {PLATFORM_LABELS[caption.platform]}
          <span className="flex items-center gap-2">
            {caption.edited && (
              <Badge variant="outline" className="border-sky-400/30 bg-sky-400/10 text-sky-300">edited</Badge>
            )}
            <Badge data-testid={`caption-${caption.platform}-model-badge`} variant="outline" className="font-mono text-[11px] text-muted-foreground">
              {caption.provider}/{caption.model}
            </Badge>
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <Textarea
          data-testid={`caption-${caption.platform}-textarea`}
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={caption.platform === "x" ? 5 : 9}
          className="resize-y bg-secondary/40 font-sans text-sm leading-6"
          placeholder="Write or regenerate a caption…"
        />
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className={`font-mono text-xs ${caption.platform === "x" && text.length > 280 ? "text-rose-400" : "text-muted-foreground"}`}>
            {text.length} chars {caption.platform === "x" ? "/ 280" : ""} · updated {timeAgo(caption.updated_at)}
          </span>
          <div className="flex gap-2">
            <Button data-testid={`caption-${caption.platform}-copy-button`} variant="ghost" size="sm" onClick={copy}>
              <Copy className="mr-1.5 h-3.5 w-3.5" /> Copy
            </Button>
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button data-testid={`caption-${caption.platform}-regenerate-button`} variant="secondary" size="sm" disabled={regenerating}>
                  <RefreshCcw className={`mr-1.5 h-3.5 w-3.5 ${regenerating ? "animate-spin" : ""}`} />
                  {regenerating ? "Generating…" : "Regenerate"}
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent className="border-border bg-popover">
                <AlertDialogHeader>
                  <AlertDialogTitle>Regenerate {PLATFORM_LABELS[caption.platform]} caption?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This will overwrite the current caption {caption.edited ? "including your manual edits" : ""} using the configured LLM.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction data-testid={`caption-${caption.platform}-regenerate-confirm`} onClick={regenerate}>
                    Regenerate
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
            <Button data-testid={`caption-${caption.platform}-save-button`} size="sm" onClick={save} disabled={!dirty || saving}>
              {dirty ? <Save className="mr-1.5 h-3.5 w-3.5" /> : <Check className="mr-1.5 h-3.5 w-3.5" />}
              {saving ? "Saving…" : dirty ? "Save" : "Saved"}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default function CaptionsPage() {
  const navigate = useNavigate();
  const [run, setRun] = useState(null);
  const [captions, setCaptions] = useState([]);
  const [loaded, setLoaded] = useState(false);

  const load = useCallback(async () => {
    try {
      const runRes = await api.get("/runs/latest");
      setRun(runRes.data);
      if (runRes.data?.id) {
        const cRes = await api.get(`/runs/${runRes.data.id}/captions`);
        setCaptions(cRes.data);
      }
    } catch { /* noop */ } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const onUpdated = (doc) => {
    setCaptions((cs) => cs.map((c) => (c.platform === doc.platform ? doc : c)));
  };

  if (!loaded) return <div className="py-24 text-center text-sm text-muted-foreground">Loading…</div>;

  if (!run || captions.length === 0) {
    return (
      <EmptyState
        icon={MessageSquareText}
        title="No captions yet"
        message={run?.status === "running" ? "Pipeline is running — captions will appear once generated." : "Run the pipeline to generate AI captions for all four platforms."}
        actionLabel="Go to pipeline"
        onAction={() => navigate("/runs")}
        actionTestId="captions-goto-pipeline-button"
      />
    );
  }

  const order = ["instagram", "facebook", "linkedin", "x"];
  const sorted = [...captions].sort((a, b) => order.indexOf(a.platform) - order.indexOf(b.platform));

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-xl font-semibold">Platform captions</h2>
        <p className="mt-1 text-sm text-muted-foreground">Market date {run.market_date || "—"} · edit, copy, or regenerate per platform.</p>
      </div>
      <Tabs defaultValue="instagram">
        <TabsList>
          {sorted.map((c) => (
            <TabsTrigger key={c.platform} data-testid={`captions-tab-${c.platform}`} value={c.platform}>
              {PLATFORM_LABELS[c.platform]}
            </TabsTrigger>
          ))}
        </TabsList>
        {sorted.map((c) => (
          <TabsContent key={c.platform} value={c.platform} className="mt-4">
            <CaptionCard caption={c} runId={run.id} onUpdated={onUpdated} />
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}

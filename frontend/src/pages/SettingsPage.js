import { useCallback, useEffect, useState } from "react";
import { Plus, Save, Trash2, X } from "lucide-react";
import { toast } from "sonner";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { api } from "@/lib/api";

export default function SettingsPage() {
  const [settings, setSettings] = useState(null);
  const [newTicker, setNewTicker] = useState("");
  const [newDivyTicker, setNewDivyTicker] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const sRes = await api.get("/settings");
      setSettings(sRes.data);
    } catch {
      toast.error("Failed to load settings");
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const save = async () => {
    setSaving(true);
    try {
      const res = await api.put("/settings", settings);
      setSettings(res.data);
      toast.success("Settings saved");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const clearRuns = async () => {
    try {
      await api.delete("/runs");
      toast.success("All runs and artifacts cleared");
    } catch {
      toast.error("Failed to clear runs");
    }
  };

  if (!settings) return <div className="py-24 text-center text-sm text-muted-foreground">Loading…</div>;

  return (
    <div className="max-w-3xl space-y-6">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="font-display text-base">Manual captions</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-6 text-muted-foreground">
            Automatic AI caption generation is disabled. After each run, open the Captions page to write, edit, and save the final copy manually for each platform.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="font-display text-base">Daily schedule</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between rounded-lg border border-border bg-secondary/40 p-4">
            <div>
              <div className="text-sm font-medium">Automatic daily run</div>
              <div className="text-xs text-muted-foreground">Runs the full pipeline every trading day at the set time.</div>
            </div>
            <Switch
              data-testid="settings-schedule-enabled-switch"
              checked={settings.schedule_enabled}
              onCheckedChange={(v) => setSettings((s) => ({ ...s, schedule_enabled: v }))}
            />
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>Run time (Asia/Manila)</Label>
              <Input
                data-testid="settings-schedule-time-input"
                type="time"
                value={settings.schedule_time}
                onChange={(e) => setSettings((s) => ({ ...s, schedule_time: e.target.value }))}
                className="bg-secondary/40"
              />
            </div>
            <div className="space-y-2">
              <Label>Brand name (on graphics)</Label>
              <Input
                data-testid="settings-brand-name-input"
                value={settings.brand_name}
                onChange={(e) => setSettings((s) => ({ ...s, brand_name: e.target.value }))}
                className="bg-secondary/40"
              />
            </div>
          </div>
          <p className="text-xs text-muted-foreground">PSE trading closes 3:30 PM — 5:00 PM is a safe default for settled data.</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="font-display text-base">REIT tickers</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div data-testid="settings-reit-tickers" className="flex flex-wrap gap-2">
            {settings.reit_tickers.map((t) => (
              <Badge key={t} variant="outline" className="gap-1.5 border-border bg-secondary/60 py-1.5 pl-3 pr-1.5 font-mono">
                {t}
                <button
                  data-testid={`settings-reit-remove-${t}`}
                  aria-label={`Remove ${t}`}
                  onClick={() => setSettings((s) => ({ ...s, reit_tickers: s.reit_tickers.filter((x) => x !== t) }))}
                  className="rounded-full p-0.5 transition-colors duration-150 hover:bg-accent"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))}
          </div>
          <div className="flex gap-2">
            <Input
              data-testid="settings-reit-add-input"
              value={newTicker}
              onChange={(e) => setNewTicker(e.target.value.toUpperCase())}
              placeholder="Add ticker e.g. AREIT"
              className="max-w-52 bg-secondary/40 font-mono"
              onKeyDown={(e) => {
                if (e.key === "Enter" && newTicker.trim()) {
                  setSettings((s) => ({ ...s, reit_tickers: [...new Set([...s.reit_tickers, newTicker.trim()])] }));
                  setNewTicker("");
                }
              }}
            />
            <Button
              data-testid="settings-reit-add-button"
              variant="secondary"
              disabled={!newTicker.trim()}
              onClick={() => {
                setSettings((s) => ({ ...s, reit_tickers: [...new Set([...s.reit_tickers, newTicker.trim()])] }));
                setNewTicker("");
              }}
            >
              <Plus className="mr-1 h-4 w-4" /> Add
            </Button>
          </div>
          </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="font-display text-base">DivY stock tickers</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-xs text-muted-foreground">Maintain your own dividend-stock selection. The daily board is sorted by highest positive change.</p>
          <div data-testid="settings-divy-tickers" className="flex flex-wrap gap-2">
            {settings.divy_tickers.map((t) => (
              <Badge key={t} variant="outline" className="gap-1.5 border-border bg-secondary/60 py-1.5 pl-3 pr-1.5 font-mono">
                {t}
                <button
                  data-testid={`settings-divy-remove-${t}`}
                  aria-label={`Remove ${t}`}
                  onClick={() => setSettings((s) => ({ ...s, divy_tickers: s.divy_tickers.filter((x) => x !== t) }))}
                  className="rounded-full p-0.5 transition-colors duration-150 hover:bg-accent"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))}
          </div>
          <div className="flex gap-2">
            <Input
              data-testid="settings-divy-add-input"
              value={newDivyTicker}
              onChange={(e) => setNewDivyTicker(e.target.value.toUpperCase())}
              placeholder="Add ticker e.g. DMC"
              className="max-w-52 bg-secondary/40 font-mono"
              onKeyDown={(e) => {
                if (e.key === "Enter" && newDivyTicker.trim()) {
                  setSettings((s) => ({ ...s, divy_tickers: [...new Set([...s.divy_tickers, newDivyTicker.trim()])] }));
                  setNewDivyTicker("");
                }
              }}
            />
            <Button
              data-testid="settings-divy-add-button"
              variant="secondary"
              disabled={!newDivyTicker.trim()}
              onClick={() => {
                setSettings((s) => ({ ...s, divy_tickers: [...new Set([...s.divy_tickers, newDivyTicker.trim()])] }));
                setNewDivyTicker("");
              }}
            >
              <Plus className="mr-1 h-4 w-4" /> Add
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button data-testid="settings-save-button" onClick={save} disabled={saving}>
          <Save className="mr-1.5 h-4 w-4" /> {saving ? "Saving…" : "Save settings"}
        </Button>
      </div>

      <Card className="border-rose-400/20">
        <CardHeader className="pb-3">
          <CardTitle className="font-display text-base text-rose-300">Danger zone</CardTitle>
        </CardHeader>
        <CardContent>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button data-testid="settings-clear-runs-button" variant="destructive">
                <Trash2 className="mr-1.5 h-4 w-4" /> Clear all runs &amp; artifacts
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent className="border-border bg-popover">
              <AlertDialogHeader>
                <AlertDialogTitle>Clear all runs?</AlertDialogTitle>
                <AlertDialogDescription>
                  This permanently deletes all runs, snapshots, graphics, captions, publishing records, and notifications. Settings are kept.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction data-testid="settings-clear-runs-confirm" onClick={clearRuns} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
                  Yes, clear everything
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </CardContent>
      </Card>
    </div>
  );
}

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import { fmtSigned } from "@/lib/api";

export const RunStatusPill = ({ status, testId }) => {
  const map = {
    running: { label: "Running", cls: "bg-sky-400/15 text-sky-300 border-sky-400/30" },
    ready: { label: "Ready", cls: "bg-emerald-400/15 text-emerald-300 border-emerald-400/30" },
    ready_with_warnings: { label: "Ready · warnings", cls: "bg-amber-400/15 text-amber-300 border-amber-400/30" },
    failed: { label: "Failed", cls: "bg-rose-400/15 text-rose-300 border-rose-400/30" },
    idle: { label: "Idle", cls: "bg-secondary text-muted-foreground border-border" },
  };
  const m = map[status] || map.idle;
  return (
    <Badge data-testid={testId} variant="outline" className={`gap-1.5 font-medium ${m.cls}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${status === "running" ? "bg-sky-400 stage-dot-running" : status === "failed" ? "bg-rose-400" : status?.startsWith("ready") ? "bg-emerald-400" : "bg-muted-foreground"}`} />
      {m.label}
    </Badge>
  );
};

export const Delta = ({ value, dp = 2, suffix = "%", className = "", testId }) => {
  if (value === null || value === undefined) return <span className="text-muted-foreground">—</span>;
  const up = value > 0;
  const flat = value === 0;
  const Icon = flat ? Minus : up ? ArrowUpRight : ArrowDownRight;
  return (
    <span
      data-testid={testId}
      className={`inline-flex items-center gap-0.5 font-mono tabular-nums font-semibold ${flat ? "text-muted-foreground" : up ? "text-gain" : "text-loss"} ${className}`}
    >
      <Icon className="h-[1em] w-[1em]" />
      {fmtSigned(value, dp)}{suffix}
    </span>
  );
};

export const SectionTitle = ({ children, className = "" }) => (
  <div className={`text-xs font-semibold tracking-widest uppercase text-muted-foreground ${className}`}>{children}</div>
);

export const EmptyState = ({ icon: Icon, title, message, actionLabel, onAction, actionTestId, loading }) => (
  <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card/50 px-8 py-16 text-center">
    {Icon && <Icon className="mb-4 h-10 w-10 text-muted-foreground" />}
    <h3 className="font-display text-lg font-semibold">{title}</h3>
    <p className="mt-2 max-w-md text-sm text-muted-foreground">{message}</p>
    {actionLabel && (
      <Button data-testid={actionTestId} onClick={onAction} disabled={loading} className="mt-6">
        {actionLabel}
      </Button>
    )}
  </div>
);

export const SeverityDot = ({ severity }) => {
  const cls = {
    success: "bg-emerald-400",
    info: "bg-sky-400",
    warning: "bg-amber-400",
    error: "bg-rose-400",
  }[severity] || "bg-muted-foreground";
  return <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${cls}`} />;
};

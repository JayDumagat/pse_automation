import { Check, CircleDashed, Loader2, TriangleAlert, X } from "lucide-react";

const STAGE_LABELS = {
  fetch: "Fetch",
  validate: "Validate",
  compute: "Compute",
  store: "Store",
  graphics: "Graphics",
  captions: "Captions",
  qa: "QA",
  ready: "Ready",
};

const StageIcon = ({ status }) => {
  if (status === "success") return <Check className="h-3.5 w-3.5 text-emerald-400" />;
  if (status === "warning") return <TriangleAlert className="h-3.5 w-3.5 text-amber-400" />;
  if (status === "failed") return <X className="h-3.5 w-3.5 text-rose-400" />;
  if (status === "running") return <Loader2 className="h-3.5 w-3.5 animate-spin text-sky-400" />;
  return <CircleDashed className="h-3.5 w-3.5 text-muted-foreground/50" />;
};

export const PipelineStageRail = ({ stages = [] }) => (
  <div className="flex flex-wrap items-center gap-y-3">
    {stages.map((st, i) => (
      <div key={st.name} className="flex items-center">
        <div
          data-testid={`pipeline-stage-${st.name}-status`}
          data-status={st.status}
          className={`flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors duration-150 ${
            st.status === "success"
              ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-300"
              : st.status === "warning"
              ? "border-amber-400/30 bg-amber-400/10 text-amber-300"
              : st.status === "failed"
              ? "border-rose-400/30 bg-rose-400/10 text-rose-300"
              : st.status === "running"
              ? "border-sky-400/30 bg-sky-400/10 text-sky-300"
              : "border-border bg-secondary/50 text-muted-foreground"
          }`}
        >
          <StageIcon status={st.status} />
          {STAGE_LABELS[st.name] || st.name}
          {st.duration_seconds != null && (
            <span className="font-mono tabular-nums text-[10px] opacity-70">{st.duration_seconds}s</span>
          )}
        </div>
        {i < stages.length - 1 && <div className="mx-1.5 h-px w-4 bg-border sm:w-6" />}
      </div>
    ))}
  </div>
);

"""Reusable async orchestration primitives for automation workflows.

The daily market pipeline predates this module and has its own persisted run
documents.  New workflows can use :class:`AutomationOrchestrator` without
coupling their stages to MongoDB or FastAPI.  Stages are explicit, support
dependencies, retries, timeouts, and can be marked as non-critical so one
optional step does not take down the whole workflow.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger("orchestrator")

StageHandler = Callable[["WorkflowContext"], Any]
StageListener = Callable[["StageEvent"], Any]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Stage:
    """A single workflow stage.

    ``handler`` may be synchronous or asynchronous.  A stage with
    ``continue_on_error=True`` records its failure and lets dependent stages
    continue; otherwise the workflow is failed and later stages are skipped.
    """

    name: str
    handler: StageHandler
    depends_on: tuple[str, ...] = ()
    retries: int = 0
    timeout_seconds: float | None = None
    continue_on_error: bool = False


@dataclass
class StageEvent:
    stage: str
    status: str
    attempt: int = 0
    started_at: str | None = None
    ended_at: str | None = None
    duration_seconds: float | None = None
    output: Any = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "status": self.status,
            "attempt": self.attempt,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_seconds": self.duration_seconds,
            "output": self.output,
            "error": self.error,
        }


@dataclass
class WorkflowContext:
    """Mutable data shared by stages in one workflow run."""

    values: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    events: list[StageEvent] = field(default_factory=list)


@dataclass
class WorkflowResult:
    status: str
    values: dict[str, Any]
    warnings: list[str]
    events: list[StageEvent]

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "values": self.values,
            "warnings": self.warnings,
            "events": [event.as_dict() for event in self.events],
        }


class AutomationOrchestrator:
    """Run a small dependency-aware workflow sequentially.

    Stages are kept sequential by design: most automation stages share a
    mutable result (for example fetch -> transform -> publish), and this gives
    deterministic execution and easy-to-follow logs.  Independent stages can
    still be expressed and parallelized later without changing their config.
    """

    def __init__(self, stages: list[Stage], listener: StageListener | None = None):
        self.stages = stages
        self.listener = listener
        self._validate()

    def _validate(self) -> None:
        names = [stage.name for stage in self.stages]
        if len(names) != len(set(names)):
            raise ValueError("stage names must be unique")
        known = set(names)
        for stage in self.stages:
            if stage.retries < 0:
                raise ValueError(f"stage '{stage.name}' retries cannot be negative")
            if stage.timeout_seconds is not None and stage.timeout_seconds <= 0:
                raise ValueError(f"stage '{stage.name}' timeout must be positive")
            missing = set(stage.depends_on) - known
            if missing:
                raise ValueError(f"stage '{stage.name}' depends on unknown stage(s): {sorted(missing)}")
        visiting: set[str] = set()
        visited: set[str] = set()
        by_name = {stage.name: stage for stage in self.stages}

        def visit(name: str) -> None:
            if name in visiting:
                raise ValueError("stage dependencies contain a cycle")
            if name in visited:
                return
            visiting.add(name)
            for dependency in by_name[name].depends_on:
                visit(dependency)
            visiting.remove(name)
            visited.add(name)

        for name in names:
            visit(name)

    async def _notify(self, event: StageEvent) -> None:
        if self.listener is None:
            return
        result = self.listener(event)
        if inspect.isawaitable(result):
            await result

    async def _run_stage(self, stage: Stage, context: WorkflowContext) -> Any:
        started = time.monotonic()
        started_at = now_iso()
        event = StageEvent(stage=stage.name, status="running", started_at=started_at)
        context.events.append(event)
        await self._notify(event)

        last_error: Exception | None = None
        for attempt in range(1, stage.retries + 2):
            event.attempt = attempt
            try:
                value = stage.handler(context)
                if inspect.isawaitable(value):
                    if stage.timeout_seconds is None:
                        value = await value
                    else:
                        value = await asyncio.wait_for(value, stage.timeout_seconds)
                event.status = "success"
                event.output = value
                event.ended_at = now_iso()
                event.duration_seconds = round(time.monotonic() - started, 3)
                await self._notify(event)
                return value
            except Exception as exc:  # stage policy decides whether to re-raise
                last_error = exc
                logger.warning(
                    "stage %s failed on attempt %s/%s: %s",
                    stage.name, attempt, stage.retries + 1, exc,
                )
                if attempt <= stage.retries:
                    await asyncio.sleep(min(2 ** (attempt - 1), 8))

        assert last_error is not None
        event.status = "failed"
        event.error = str(last_error)
        event.ended_at = now_iso()
        event.duration_seconds = round(time.monotonic() - started, 3)
        await self._notify(event)
        if stage.continue_on_error:
            context.warnings.append(f"Stage '{stage.name}' failed: {last_error}")
            return None
        raise last_error

    async def run(self, context: WorkflowContext | None = None) -> WorkflowResult:
        context = context or WorkflowContext()
        completed: set[str] = set()
        failed: set[str] = set()

        # Repeatedly choose the first stage whose dependencies have completed.
        # The validation above guarantees this terminates for a valid workflow.
        pending = list(self.stages)
        while pending:
            progress = False
            for stage in pending[:]:
                if not set(stage.depends_on).issubset(completed | failed):
                    continue
                pending.remove(stage)
                progress = True
                blocked = any(dependency in failed for dependency in stage.depends_on)
                if blocked:
                    event = StageEvent(stage=stage.name, status="skipped", error="dependency failed")
                    context.events.append(event)
                    await self._notify(event)
                    failed.add(stage.name)
                    continue
                try:
                    context.values[stage.name] = await self._run_stage(stage, context)
                    completed.add(stage.name)
                except Exception:
                    failed.add(stage.name)
                    # A failed critical stage makes all remaining work
                    # ineligible; retain explicit skipped events for observability.
                    for remaining in pending:
                        event = StageEvent(stage=remaining.name, status="skipped", error=f"blocked by {stage.name}")
                        context.events.append(event)
                        await self._notify(event)
                    pending.clear()
                    break
            if not progress and pending:
                raise RuntimeError("workflow could not make progress; check stage dependencies")

        status = "failed" if failed and any(
            event.status == "failed" and not next(
                stage.continue_on_error for stage in self.stages if stage.name == event.stage
            ) for event in context.events
        ) else ("completed_with_warnings" if context.warnings else "completed")
        return WorkflowResult(status, context.values, context.warnings, context.events)


__all__ = ["AutomationOrchestrator", "Stage", "StageEvent", "WorkflowContext", "WorkflowResult"]

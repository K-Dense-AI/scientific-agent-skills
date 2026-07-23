#!/usr/bin/env python3
"""Bounded resource monitoring and deterministic event tracing for SimPy."""

from __future__ import annotations

import argparse
import csv
import io
import json
from dataclasses import asdict, dataclass
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    import simpy

from _common import (
    MAX_TRACE_RECORDS,
    CliError,
    emit_json,
    emit_text,
    integer,
    load_simpy,
)


@dataclass(frozen=True)
class ResourceSample:
    """One resource state observed at a simulation timestamp."""

    time: float
    event: str
    count: int
    queue_length: int
    utilization: float


class ResourceMonitor:
    """Monitor one Resource/PriorityResource/PreemptiveResource instance."""

    def __init__(
        self,
        env: simpy.Environment,
        resource: simpy.Resource,
        name: str = "resource",
    ):
        simpy_module = load_simpy()
        if not isinstance(
            resource,
            (
                simpy_module.Resource,
                simpy_module.PriorityResource,
                simpy_module.PreemptiveResource,
            ),
        ):
            raise CliError("ResourceMonitor requires a SimPy Resource-like object")
        if getattr(resource, "_simpy_skill_monitor_attached", False):
            raise CliError("this resource already has a ResourceMonitor")
        self.env = env
        self.resource = resource
        self.name = name
        self.samples: list[ResourceSample] = []
        self.wait_times: list[float] = []
        self._request_times: dict[Any, float] = {}
        self._original_request = resource.request
        self._original_release = resource.release
        setattr(resource, "_simpy_skill_monitor_attached", True)
        self._record("initial")
        self._patch()

    def _record(self, event: str, *, at: float | None = None) -> None:
        time = float(self.env.now if at is None else at)
        self.samples.append(
            ResourceSample(
                time=time,
                event=event,
                count=int(self.resource.count),
                queue_length=len(self.resource.queue),
                utilization=float(self.resource.count / self.resource.capacity),
            )
        )

    def _patch(self) -> None:
        @wraps(self._original_request)
        def monitored_request(*args: Any, **kwargs: Any) -> Any:
            requested_at = float(self.env.now)
            request = self._original_request(*args, **kwargs)
            self._request_times[request] = requested_at
            self._record("request")

            def granted(_: Any) -> None:
                start = self._request_times.pop(request, None)
                if start is not None:
                    self.wait_times.append(float(self.env.now) - start)
                self._record("grant")

            if request.callbacks is not None:
                request.callbacks.append(granted)

            original_cancel = request.cancel

            @wraps(original_cancel)
            def monitored_cancel() -> None:
                original_cancel()
                self._request_times.pop(request, None)
                self._record("cancel")

            try:
                request.cancel = monitored_cancel
            except (AttributeError, TypeError):
                # Current SimPy events allow instance wrappers. If a future release
                # changes that implementation, later state samples remain valid but
                # cancellation instants may need explicit user instrumentation.
                pass
            return request

        @wraps(self._original_release)
        def monitored_release(*args: Any, **kwargs: Any) -> Any:
            released = self._original_release(*args, **kwargs)
            self._record("release")
            return released

        self.resource.request = monitored_request
        self.resource.release = monitored_release

    def detach(self) -> None:
        """Restore the resource methods patched by this monitor."""

        self.resource.request = self._original_request
        self.resource.release = self._original_release
        setattr(self.resource, "_simpy_skill_monitor_attached", False)

    def finalize(self, *, at: float | None = None) -> None:
        """Close the final time interval with the resource's current state."""

        final_time = float(self.env.now if at is None else at)
        if final_time < self.samples[-1].time:
            raise CliError("monitor final time cannot precede its latest sample")
        self._record("final", at=final_time)

    def _time_weighted(
        self,
        attribute: str,
        *,
        start: float,
        end: float,
    ) -> float:
        if start < self.samples[0].time:
            raise CliError("monitor window starts before monitoring began")
        if end <= start:
            raise CliError("monitor window end must be greater than start")
        if end > self.samples[-1].time:
            raise CliError("call finalize() through the requested window end first")

        current = self.samples[0]
        for sample in self.samples:
            if sample.time <= start:
                current = sample
            else:
                break
        cursor = start
        weighted = 0.0
        for sample in self.samples:
            if sample.time <= start:
                continue
            if sample.time >= end:
                break
            weighted += float(getattr(current, attribute)) * (sample.time - cursor)
            cursor = sample.time
            current = sample
        weighted += float(getattr(current, attribute)) * (end - cursor)
        return weighted / (end - start)

    def average_queue_length(
        self, *, start: float = 0.0, end: float | None = None
    ) -> float:
        """Return the time-weighted queue length over [start, end)."""

        final = self.samples[-1].time if end is None else float(end)
        return self._time_weighted(
            "queue_length", start=float(start), end=final
        )

    def average_utilization(
        self, *, start: float = 0.0, end: float | None = None
    ) -> float:
        """Return time-weighted allocated capacity over [start, end)."""

        final = self.samples[-1].time if end is None else float(end)
        return self._time_weighted("utilization", start=float(start), end=final)

    def summary(
        self, *, start: float = 0.0, end: float | None = None
    ) -> dict[str, Any]:
        """Return a JSON-compatible summary of this monitor."""

        final = self.samples[-1].time if end is None else float(end)
        return {
            "average_queue_length": self.average_queue_length(
                start=start, end=final
            ),
            "average_utilization": self.average_utilization(
                start=start, end=final
            ),
            "capacity": self.resource.capacity,
            "end": final,
            "final_count": self.resource.count,
            "final_queue_length": len(self.resource.queue),
            "granted_requests": len(self.wait_times),
            "maximum_queue_length": max(
                sample.queue_length for sample in self.samples
            ),
            "mean_wait": (
                sum(self.wait_times) / len(self.wait_times)
                if self.wait_times
                else None
            ),
            "name": self.name,
            "pending_requests": len(self._request_times),
            "samples": len(self.samples),
            "start": start,
        }

    def export_csv(self, output: str, *, force: bool = False) -> None:
        """Write state samples to a bounded, private local CSV."""

        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(
            buffer,
            fieldnames=[
                "time",
                "event",
                "count",
                "queue_length",
                "utilization",
            ],
        )
        writer.writeheader()
        for sample in self.samples:
            writer.writerow(asdict(sample))
        emit_text(buffer.getvalue(), output=output, suffixes={".csv"}, force=force)


class MultiResourceMonitor:
    """Manage uniquely named ResourceMonitor instances in one environment."""

    def __init__(self, env: simpy.Environment):
        load_simpy()
        self.env = env
        self.monitors: dict[str, ResourceMonitor] = {}

    def add_resource(
        self, resource: simpy.Resource, name: str
    ) -> ResourceMonitor:
        if not name or name in self.monitors:
            raise CliError("resource monitor names must be non-empty and unique")
        monitor = ResourceMonitor(self.env, resource, name)
        self.monitors[name] = monitor
        return monitor

    def finalize(self, *, at: float | None = None) -> None:
        for monitor in self.monitors.values():
            monitor.finalize(at=at)

    def summaries(
        self, *, start: float = 0.0, end: float | None = None
    ) -> dict[str, dict[str, Any]]:
        return {
            name: monitor.summary(start=start, end=end)
            for name, monitor in self.monitors.items()
        }


class ContainerMonitor:
    """Record completed put/get operations and time-weighted Container level."""

    def __init__(
        self,
        env: simpy.Environment,
        container: simpy.Container,
        name: str = "container",
    ):
        load_simpy()
        if getattr(container, "_simpy_skill_monitor_attached", False):
            raise CliError("this container already has a ContainerMonitor")
        self.env = env
        self.container = container
        self.name = name
        self.samples: list[tuple[float, str, float]] = [
            (float(env.now), "initial", float(container.level))
        ]
        self._original_put = container.put
        self._original_get = container.get
        setattr(container, "_simpy_skill_monitor_attached", True)
        self._patch()

    def _record(self, event: str, *, at: float | None = None) -> None:
        self.samples.append(
            (
                float(self.env.now if at is None else at),
                event,
                float(self.container.level),
            )
        )

    def _patch_operation(
        self, operation: Callable[..., Any], event_name: str
    ) -> Callable[..., Any]:
        @wraps(operation)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            event = operation(*args, **kwargs)
            if event.callbacks is not None:
                event.callbacks.append(lambda _: self._record(event_name))
            return event

        return wrapper

    def _patch(self) -> None:
        self.container.put = self._patch_operation(self._original_put, "put")
        self.container.get = self._patch_operation(self._original_get, "get")

    def finalize(self, *, at: float | None = None) -> None:
        final_time = float(self.env.now if at is None else at)
        if final_time < self.samples[-1][0]:
            raise CliError("monitor final time cannot precede its latest sample")
        self._record("final", at=final_time)

    def average_level(
        self, *, start: float = 0.0, end: float | None = None
    ) -> float:
        final = self.samples[-1][0] if end is None else float(end)
        if final <= start:
            raise CliError("monitor window end must be greater than start")
        if final > self.samples[-1][0]:
            raise CliError("call finalize() through the requested window end first")
        current = self.samples[0]
        for sample in self.samples:
            if sample[0] <= start:
                current = sample
            else:
                break
        cursor = start
        weighted = 0.0
        for sample in self.samples:
            if sample[0] <= start:
                continue
            if sample[0] >= final:
                break
            weighted += current[2] * (sample[0] - cursor)
            cursor = sample[0]
            current = sample
        weighted += current[2] * (final - cursor)
        return weighted / (final - start)


class EventTraceRecorder:
    """Trace the next queued event before each Environment.step() call."""

    def __init__(
        self,
        env: simpy.Environment,
        *,
        max_records: int = 100_000,
    ):
        load_simpy()
        self.env = env
        self.max_records = integer(
            max_records,
            name="max_records",
            minimum=1,
            maximum=MAX_TRACE_RECORDS,
        )
        self.records: list[dict[str, Any]] = []
        self.truncated = False
        self._original_step = env.step
        self._patch()

    def _patch(self) -> None:
        @wraps(self._original_step)
        def tracing_step() -> None:
            queue = getattr(self.env, "_queue", None)
            if queue:
                if len(self.records) < self.max_records:
                    time, priority, event_id, event = queue[0]
                    self.records.append(
                        {
                            "event_id": int(event_id),
                            "event_type": type(event).__name__,
                            "priority": int(priority),
                            "queue_size_before": len(queue),
                            "time": float(time),
                        }
                    )
                else:
                    self.truncated = True
            self._original_step()

        self.env.step = tracing_step

    def detach(self) -> None:
        self.env.step = self._original_step

    def export_jsonl(self, output: str, *, force: bool = False) -> None:
        """Write deterministic JSON Lines without object repr or memory addresses."""

        text = "".join(
            json.dumps(
                record,
                sort_keys=True,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )
            + "\n"
            for record in self.records
        )
        emit_text(text, output=output, suffixes={".jsonl"}, force=force)


def _demo() -> tuple[dict[str, Any], ResourceMonitor]:
    simpy_module = load_simpy()
    env = simpy_module.Environment()
    resource = simpy_module.Resource(env, capacity=2)
    monitor = ResourceMonitor(env, resource, "demo_server")

    def user(identifier: int) -> Any:
        yield env.timeout(identifier * 0.5)
        with resource.request() as request:
            yield request
            yield env.timeout(1.0 + identifier * 0.1)

    for index in range(8):
        env.process(user(index))
    env.run(until=10)
    monitor.finalize(at=10)
    return monitor.summary(start=0, end=10), monitor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run a finite synthetic Resource-monitor demonstration and emit a "
            "time-weighted summary. No network or external service is used."
        )
    )
    parser.add_argument("--output", help="Optional local .json summary")
    parser.add_argument("--samples", help="Optional local .csv state samples")
    parser.add_argument("--force", action="store_true", help="Replace explicit outputs")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        summary, monitor = _demo()
        if args.samples:
            monitor.export_csv(args.samples, force=args.force)
        emit_json(
            {
                "monitor": summary,
                "network_used": False,
                "schema_version": "1.1",
            },
            output=args.output,
            force=args.force,
        )
    except CliError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

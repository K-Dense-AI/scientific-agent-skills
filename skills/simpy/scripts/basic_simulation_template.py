#!/usr/bin/env python3
"""Bounded, reproducible SimPy queue template with independent random streams."""

from __future__ import annotations

import argparse
import random
from dataclasses import asdict, dataclass, field
from statistics import fmean
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import simpy

from _common import (
    DEFAULT_SEED,
    MAX_ENTITIES,
    MAX_EVENTS,
    MAX_QUEUE_CAPACITY,
    MAX_SIM_TIME,
    CliError,
    derive_seed,
    emit_json,
    finite_number,
    integer,
    load_json_object,
    load_simpy,
    validate_keys,
)
from resource_monitor import EventTraceRecorder, ResourceMonitor


_SIMPY = load_simpy(required=False)


CONFIG_KEYS = {
    "analysis_mode",
    "base_seed",
    "horizon",
    "max_entities",
    "max_events",
    "mean_interarrival",
    "mean_service",
    "queue_capacity",
    "servers",
    "warm_up",
}


class EventLimitExceeded(RuntimeError):
    """Raised when a simulation attempts to process too many events."""


if _SIMPY is not None:

    class BoundedEnvironment(_SIMPY.Environment):
        """Environment that enforces a public, explicit event-processing budget."""

        def __init__(self, *, max_events: int):
            super().__init__()
            self.max_events = max_events
            self.processed_events = 0

        def step(self) -> None:
            if self.processed_events >= self.max_events:
                raise EventLimitExceeded(
                    f"simulation reached the max_events limit ({self.max_events})"
                )
            super().step()
            self.processed_events += 1

else:

    class BoundedEnvironment:
        """Unavailable placeholder used only when SimPy is not installed."""

        def __init__(self, *, max_events: int):
            del max_events
            load_simpy()
            raise AssertionError("unreachable")


@dataclass(frozen=True)
class QueueConfig:
    """Validated configuration for a finite-horizon multi-server queue."""

    analysis_mode: str = "terminating"
    horizon: float = 480.0
    warm_up: float = 0.0
    servers: int = 2
    queue_capacity: int = 20
    mean_interarrival: float = 4.0
    mean_service: float = 6.0
    base_seed: int = DEFAULT_SEED
    max_entities: int = 10_000
    max_events: int = 200_000

    @classmethod
    def from_mapping(cls, value: dict[str, Any] | None) -> "QueueConfig":
        """Build a strict configuration; unknown JSON keys are rejected."""

        value = {} if value is None else dict(value)
        validate_keys(value, allowed=CONFIG_KEYS, context="queue configuration")
        defaults = cls()
        analysis_mode = value.get("analysis_mode", defaults.analysis_mode)
        if analysis_mode not in {"terminating", "steady_state"}:
            raise CliError(
                "analysis_mode must be either 'terminating' or 'steady_state'"
            )
        horizon = finite_number(
            value.get("horizon", defaults.horizon),
            name="horizon",
            minimum=0.0,
            maximum=MAX_SIM_TIME,
            minimum_inclusive=False,
        )
        warm_up = finite_number(
            value.get("warm_up", defaults.warm_up),
            name="warm_up",
            minimum=0.0,
            maximum=horizon,
        )
        if warm_up >= horizon:
            raise CliError("warm_up must be strictly less than horizon")
        if analysis_mode == "terminating" and warm_up != 0:
            raise CliError("terminating analyses must use warm_up=0")
        if analysis_mode == "steady_state" and warm_up <= 0:
            raise CliError("steady_state analyses require a positive warm_up")
        return cls(
            analysis_mode=analysis_mode,
            horizon=horizon,
            warm_up=warm_up,
            servers=integer(
                value.get("servers", defaults.servers),
                name="servers",
                minimum=1,
                maximum=10_000,
            ),
            queue_capacity=integer(
                value.get("queue_capacity", defaults.queue_capacity),
                name="queue_capacity",
                minimum=0,
                maximum=MAX_QUEUE_CAPACITY,
            ),
            mean_interarrival=finite_number(
                value.get("mean_interarrival", defaults.mean_interarrival),
                name="mean_interarrival",
                minimum=0.0,
                maximum=MAX_SIM_TIME,
                minimum_inclusive=False,
            ),
            mean_service=finite_number(
                value.get("mean_service", defaults.mean_service),
                name="mean_service",
                minimum=0.0,
                maximum=MAX_SIM_TIME,
                minimum_inclusive=False,
            ),
            base_seed=integer(
                value.get("base_seed", defaults.base_seed),
                name="base_seed",
                minimum=0,
                maximum=2**63 - 1,
            ),
            max_entities=integer(
                value.get("max_entities", defaults.max_entities),
                name="max_entities",
                minimum=1,
                maximum=MAX_ENTITIES,
            ),
            max_events=integer(
                value.get("max_events", defaults.max_events),
                name="max_events",
                minimum=10,
                maximum=MAX_EVENTS,
            ),
        )


@dataclass
class QueueStatistics:
    """Per-run counters and post-warm-up observations."""

    arrivals: int = 0
    admitted: int = 0
    rejected: int = 0
    completed: int = 0
    observed_completed: int = 0
    wait_times: list[float] = field(default_factory=list)
    service_times: list[float] = field(default_factory=list)
    system_times: list[float] = field(default_factory=list)
    entity_limit_hit: bool = False


def _optional_mean(values: list[float]) -> float | None:
    return fmean(values) if values else None


def _customer(
    env: BoundedEnvironment,
    *,
    resource: simpy.Resource,
    stats: QueueStatistics,
    service_rng: random.Random,
    mean_service: float,
    arrival_time: float,
    warm_up: float,
) -> Any:
    """Request one server, receive service, and record a completed observation."""

    with resource.request() as request:
        yield request
        service_start = env.now
        service_time = service_rng.expovariate(1.0 / mean_service)
        yield env.timeout(service_time)
    stats.completed += 1
    if arrival_time >= warm_up:
        stats.observed_completed += 1
        stats.wait_times.append(service_start - arrival_time)
        stats.service_times.append(service_time)
        stats.system_times.append(env.now - arrival_time)

def _arrivals(
    env: BoundedEnvironment,
    *,
    resource: simpy.Resource,
    config: QueueConfig,
    stats: QueueStatistics,
    arrival_rng: random.Random,
    service_rng: random.Random,
) -> Any:
    """Generate at most max_entities arrivals strictly before the horizon."""

    while stats.arrivals < config.max_entities:
        delay = arrival_rng.expovariate(1.0 / config.mean_interarrival)
        if env.now + delay >= config.horizon:
            return
        yield env.timeout(delay)
        stats.arrivals += 1
        system_capacity = config.servers + config.queue_capacity
        if resource.count + len(resource.queue) >= system_capacity:
            stats.rejected += 1
            continue
        stats.admitted += 1
        env.process(
            _customer(
                env,
                resource=resource,
                stats=stats,
                service_rng=service_rng,
                mean_service=config.mean_service,
                arrival_time=env.now,
                warm_up=config.warm_up,
            )
        )
    stats.entity_limit_hit = True


def run_simulation(
    config: QueueConfig,
    *,
    replication: int = 0,
    trace_max_records: int | None = None,
) -> dict[str, Any]:
    """Run one bounded replication and return a strict-JSON-compatible report."""

    simpy_module = load_simpy()
    replication = integer(
        replication,
        name="replication",
        minimum=0,
        maximum=999,
    )
    arrival_seed = derive_seed(config.base_seed, replication, "arrivals")
    service_seed = derive_seed(config.base_seed, replication, "service")
    arrival_rng = random.Random(arrival_seed)
    service_rng = random.Random(service_seed)
    env = BoundedEnvironment(max_events=config.max_events)
    trace = (
        EventTraceRecorder(env, max_records=trace_max_records)
        if trace_max_records is not None
        else None
    )
    resource = simpy_module.Resource(env, capacity=config.servers)
    monitor = ResourceMonitor(env, resource, name="server")
    stats = QueueStatistics()
    env.process(
        _arrivals(
            env,
            resource=resource,
            config=config,
            stats=stats,
            arrival_rng=arrival_rng,
            service_rng=service_rng,
        )
    )
    try:
        env.run(until=config.horizon)
    except EventLimitExceeded as exc:
        raise CliError(str(exc)) from exc
    if trace is not None:
        trace.detach()
    monitor.finalize(at=config.horizon)

    observed_duration = config.horizon - config.warm_up
    warnings: list[str] = []
    unfinished = stats.admitted - stats.completed
    if stats.entity_limit_hit:
        warnings.append(
            "max_entities was reached before the horizon; arrivals were truncated"
        )
    if unfinished:
        warnings.append(
            "some admitted entities were unfinished at the horizon; completed-customer "
            "metrics exclude those right-censored paths"
        )
    if stats.observed_completed == 0:
        warnings.append("no completed entities were observed in the analysis window")
    if config.analysis_mode == "steady_state":
        warnings.append(
            "warm-up deletion is user-specified and does not prove steady state"
        )

    loss_probability = (
        stats.rejected / stats.arrivals if stats.arrivals else None
    )
    report = {
        "config": asdict(config),
        "counters": {
            "admitted": stats.admitted,
            "arrivals": stats.arrivals,
            "completed": stats.completed,
            "observed_completed": stats.observed_completed,
            "rejected": stats.rejected,
            "unfinished_at_horizon": unfinished,
        },
        "event_processing": {
            "limit": config.max_events,
            "processed": env.processed_events,
        },
        "metrics": {
            "average_queue_length": monitor.average_queue_length(
                start=config.warm_up, end=config.horizon
            ),
            "average_system_time": _optional_mean(stats.system_times),
            "average_wait": _optional_mean(stats.wait_times),
            "loss_probability": loss_probability,
            "mean_service_time": _optional_mean(stats.service_times),
            "server_utilization": monitor.average_utilization(
                start=config.warm_up, end=config.horizon
            ),
            "throughput_per_time_unit": (
                stats.observed_completed / observed_duration
            ),
        },
        "replication": replication,
        "schema_version": "1.1",
        "seed_manifest": {
            "algorithm": "BLAKE2b-derived Python random.Random streams",
            "arrival_seed": arrival_seed,
            "base_seed": config.base_seed,
            "service_seed": service_seed,
        },
        "warnings": warnings,
    }
    if trace is not None:
        report["event_trace"] = {
            "records": trace.records,
            "truncated": trace.truncated,
        }
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run a deterministic, finite-horizon queue template. JSON input is "
            "allowlisted and all time, event, entity, and queue bounds are enforced."
        )
    )
    parser.add_argument(
        "--config",
        help="Optional local .json queue configuration; URLs and symlinks are rejected",
    )
    parser.add_argument(
        "--replication",
        type=int,
        default=0,
        help="Deterministic replication index from 0 through 999 (default: 0)",
    )
    parser.add_argument("--output", help="Optional local .json report")
    parser.add_argument("--force", action="store_true", help="Replace explicit output")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = QueueConfig.from_mapping(
            load_json_object(args.config) if args.config else None
        )
        report = run_simulation(config, replication=args.replication)
        report["source"] = {
            "config": None if args.config is None else "local_json",
            "network_used": False,
        }
        emit_json(report, output=args.output, force=args.force)
    except CliError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

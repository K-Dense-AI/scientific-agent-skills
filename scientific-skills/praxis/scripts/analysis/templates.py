"""Analysis template system: save, load, and replay analysis pipelines.

Templates are stored as human-readable JSON files (.praxis-template.json)
that reference analysis functions by their importable path. This allows
users to build reproducible analysis workflows and share them.
"""

from __future__ import annotations

import importlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class AnalysisStep:
    """One step in an analysis pipeline."""
    function: str       # e.g. "analysis.baseline.correct_baseline"
    params: dict        # kwargs for the function
    description: str    # human-readable description

    def to_dict(self) -> dict:
        """Convert to JSON-serialisable dict."""
        return {
            "function": self.function,
            "params": self.params,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, d: dict) -> AnalysisStep:
        """Create from a dict (loaded from JSON)."""
        return cls(
            function=d["function"],
            params=d.get("params", {}),
            description=d.get("description", ""),
        )


@dataclass
class AnalysisTemplate:
    """A saved analysis pipeline."""
    name: str
    description: str
    steps: list[AnalysisStep]
    created: str = ""           # ISO timestamp, set automatically if empty
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.created:
            self.created = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        """Convert to JSON-serialisable dict."""
        return {
            "name": self.name,
            "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
            "created": self.created,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> AnalysisTemplate:
        """Create from a dict (loaded from JSON)."""
        return cls(
            name=d["name"],
            description=d.get("description", ""),
            steps=[AnalysisStep.from_dict(s) for s in d.get("steps", [])],
            created=d.get("created", ""),
            metadata=d.get("metadata", {}),
        )

    def summary(self) -> str:
        """Human-readable summary of the template."""
        lines = [
            f"[Praxis] Template: {self.name}",
            f"  {self.description}",
            f"  Created: {self.created}",
            f"  Steps ({len(self.steps)}):",
        ]
        for i, step in enumerate(self.steps, 1):
            lines.append(f"    {i}. {step.description} [{step.function}]")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.summary()


# ---------------------------------------------------------------------------
# Template file extension
# ---------------------------------------------------------------------------

TEMPLATE_EXTENSION = ".praxis-template.json"


# ---------------------------------------------------------------------------
# Save / Load
# ---------------------------------------------------------------------------

def save_template(template: AnalysisTemplate, path: str) -> Path:
    """Save template as a human-readable JSON file.

    Parameters
    ----------
    template : AnalysisTemplate
        The template to save.
    path : str
        File path. If it doesn't end with the template extension,
        the extension is appended automatically.

    Returns
    -------
    Path
        The path the template was written to.
    """
    p = Path(path)
    if not p.name.endswith(TEMPLATE_EXTENSION):
        p = p.with_suffix("").with_suffix(TEMPLATE_EXTENSION)

    p.parent.mkdir(parents=True, exist_ok=True)

    with open(p, "w", encoding="utf-8") as f:
        json.dump(template.to_dict(), f, indent=2, ensure_ascii=False)

    print(f"[Praxis] Template saved: {p}")
    return p


def load_template(path: str) -> AnalysisTemplate:
    """Load a template from a JSON file.

    Parameters
    ----------
    path : str
        Path to the template file.

    Returns
    -------
    AnalysisTemplate
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Template not found: {p}")

    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)

    template = AnalysisTemplate.from_dict(data)
    print(f"[Praxis] Template loaded: {template.name} ({len(template.steps)} steps)")
    return template


# ---------------------------------------------------------------------------
# Execute
# ---------------------------------------------------------------------------

def _resolve_function(dotted_path: str):
    """Import and return a function from a dotted path.

    Accepts paths like:
        "analysis.baseline.correct_baseline"   -> scripts.analysis.baseline.correct_baseline
        "scripts.analysis.fitting.fit_curve"    -> scripts.analysis.fitting.fit_curve

    The 'scripts.' prefix is added if not already present, so template
    authors can use the shorter form.
    """
    if not dotted_path.startswith("scripts."):
        dotted_path = f"scripts.{dotted_path}"

    parts = dotted_path.rsplit(".", 1)
    if len(parts) != 2:
        raise ImportError(f"Cannot parse function path: {dotted_path}")

    module_path, func_name = parts
    module = importlib.import_module(module_path)
    func = getattr(module, func_name, None)
    if func is None:
        raise ImportError(f"Function '{func_name}' not found in module '{module_path}'")
    return func


def execute_template(
    template: AnalysisTemplate,
    x: Any,
    y: Any,
    **kwargs: Any,
) -> list[dict]:
    """Execute all steps in a template on data.

    Each step receives `x` and `y` as positional arguments plus its own
    params merged with any extra **kwargs. If a step returns a tuple of
    two arrays, those become the x and y for the next step (pipeline
    chaining). Otherwise the original x and y are passed forward.

    Parameters
    ----------
    template : AnalysisTemplate
        The template to execute.
    x, y : array-like
        Input data arrays.
    **kwargs
        Extra keyword arguments passed to every step.

    Returns
    -------
    list of dict
        One dict per step with keys: 'step', 'function', 'description',
        'result', 'x_out', 'y_out'.
    """
    import numpy as np

    results = []
    x_current = np.asarray(x, dtype=float)
    y_current = np.asarray(y, dtype=float)

    print(f"[Praxis] Executing template: {template.name} ({len(template.steps)} steps)")

    for i, step in enumerate(template.steps, 1):
        print(f"  Step {i}/{len(template.steps)}: {step.description}")

        func = _resolve_function(step.function)

        # Merge step params with global kwargs (step params take priority)
        merged = {**kwargs, **step.params}
        result = func(x_current, y_current, **merged)

        # Determine output arrays for the next step
        x_out, y_out = x_current, y_current
        if isinstance(result, tuple) and len(result) == 2:
            try:
                a, b = result
                a_arr = np.asarray(a, dtype=float)
                b_arr = np.asarray(b, dtype=float)
                if a_arr.ndim == 1 and b_arr.ndim == 1 and len(a_arr) == len(b_arr):
                    x_out, y_out = a_arr, b_arr
            except (ValueError, TypeError):
                pass  # Not array-like outputs; keep previous x, y

        x_current, y_current = x_out, y_out

        results.append({
            "step": i,
            "function": step.function,
            "description": step.description,
            "result": result,
            "x_out": x_out,
            "y_out": y_out,
        })

    print(f"[Praxis] Template complete: {len(results)} steps executed")
    return results


# ---------------------------------------------------------------------------
# List templates
# ---------------------------------------------------------------------------

def list_templates(directory: str = ".") -> list[str]:
    """List available .praxis-template.json files in a directory.

    Parameters
    ----------
    directory : str
        Directory to search (non-recursive).

    Returns
    -------
    list of str
        File paths of discovered templates.
    """
    d = Path(directory)
    if not d.is_dir():
        return []

    templates = sorted(str(p) for p in d.glob(f"*{TEMPLATE_EXTENSION}"))

    if templates:
        print(f"[Praxis] Found {len(templates)} template(s) in {d}:")
        for t in templates:
            print(f"  {t}")
    else:
        print(f"[Praxis] No templates found in {d}")

    return templates

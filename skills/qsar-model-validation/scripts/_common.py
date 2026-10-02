#!/usr/bin/env python3
"""Shared, standard-library-first helpers for the QSAR model validation CLIs.

The scientific packages (RDKit, scikit-learn, pandas, NumPy, SciPy) are
imported lazily, inside the functions that need them, so that `--help` works in
an environment where none of them is installed.  A missing package raises
``CliError`` carrying the install command rather than a bare traceback.

Everything here is deterministic: every split, bootstrap, and model fit takes an
explicit seed, because a metric quoted without knowing how much it moves under
reseeding is not evidence.  The helper names are deliberately free of any
project's proprietary conventions -- they implement the definitions stated in
`references/metrics-and-calibration.md` and nothing more.
"""

from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence


PINNED_INSTALL = 'uv pip install "rdkit>=2024.3" "scikit-learn>=1.4" "pandas>=2.2" "numpy>=1.26" "scipy>=1.11"'

#: Molecule tables are larger than the report files the other skills cap at 4 MB;
#: a 32 MB ceiling still refuses a mis-pointed file (a ChEMBL dump, a tarball)
#: before pandas tries to allocate for it.
MAX_INPUT_BYTES = 32 * 1024 * 1024
MAX_SMILES_CHARS = 5_000
MAX_ROWS = 2_000_000

DEFAULT_SEED = 20_260_930
DEFAULT_TEST_SIZE = 0.2
DEFAULT_FINGERPRINT_RADIUS = 2
DEFAULT_FINGERPRINT_BITS = 2048

#: Tanimoto at or above this counts as a near-duplicate across a split.  0.8 is
#: the conventional "same chemotype" line; it is a reporting threshold, not a
#: claim about mechanism, and the CLI exposes it so a reader can disagree.
DEFAULT_DUPLICATE_THRESHOLD = 0.8

#: Column names the CLIs guess when the caller does not name them.
SMILES_ALIASES = ("smiles", "SMILES", "canonical_smiles", "structure", "smi")
TARGET_ALIASES = ("target", "y", "label", "activity", "value", "pIC50", "pic50")
TIME_ALIASES = ("time", "year", "date", "timestamp", "split_time")
GROUP_ALIASES = ("group", "series", "compound_id", "inchikey", "cluster")


class CliError(ValueError):
    """An expected command-line validation error."""


# --------------------------------------------------------------------------
# argparse converters
# --------------------------------------------------------------------------


def bounded_int(minimum: int, maximum: int) -> Callable[[str], int]:
    """Return an argparse converter for an integer inside ``[minimum, maximum]``."""

    def convert(value: str) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise CliError(f"expected an integer, got {value!r}") from exc
        if not minimum <= parsed <= maximum:
            raise CliError(f"expected an integer in [{minimum}, {maximum}], got {parsed}")
        return parsed

    return convert


def finite_float(value: str) -> float:
    """Return an argparse converter for a finite float."""

    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise CliError(f"expected a number, got {value!r}") from exc
    if not math.isfinite(parsed):
        raise CliError(f"expected a finite number, got {value!r}")
    return parsed


def fraction(value: str) -> float:
    """Return an argparse converter for a fraction strictly between 0 and 1."""

    parsed = finite_float(value)
    if not 0.0 < parsed < 1.0:
        raise CliError(f"expected a fraction strictly between 0 and 1, got {parsed}")
    return parsed


def non_negative_float(value: str) -> float:
    """Return an argparse converter for a float that is not negative."""

    parsed = finite_float(value)
    if parsed < 0:
        raise CliError(f"expected a non-negative number, got {parsed}")
    return parsed


def seed_list(value: str) -> list[int]:
    """Parse `0,1,2` into a list of seeds, preserving order and duplicates out."""

    seeds: list[int] = []
    for chunk in value.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            seeds.append(int(chunk))
        except ValueError as exc:
            raise CliError(f"expected comma-separated integers, got {value!r}") from exc
    if not seeds:
        raise CliError("expected at least one seed")
    return seeds


# --------------------------------------------------------------------------
# lazy scientific imports
# --------------------------------------------------------------------------


def _require(module: str, *, purpose: str) -> Any:
    """Import ``module`` or raise a CliError naming the install command."""

    try:
        return __import__(module)
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise CliError(
            f"{purpose} needs the {module!r} package, which is not importable here; "
            f"install with `{PINNED_INSTALL}`"
        ) from exc


def require_pandas() -> Any:
    """Return the pandas module, or fail with an install hint."""

    return _require("pandas", purpose="reading and writing molecule tables")


def require_numpy() -> Any:
    """Return the NumPy module, or fail with an install hint."""

    return _require("numpy", purpose="the numeric work in this skill")


def require_rdkit() -> Any:
    """Return the ``rdkit.Chem`` module, or fail with an install hint."""

    _require("rdkit", purpose="parsing structures and computing fingerprints")
    from rdkit import Chem  # noqa: PLC0415 - deliberately lazy

    return Chem


def require_sklearn() -> Any:
    """Return the scikit-learn helpers this skill fits, or fail with a hint."""

    _require("sklearn", purpose="fitting the comparison models")
    from sklearn import (  # noqa: PLC0415 - deliberately lazy
        dummy,
        ensemble,
        metrics,
        model_selection,
    )

    return {"dummy": dummy, "ensemble": ensemble, "metrics": metrics, "model_selection": model_selection}


def require_scipy() -> Any:
    """Return ``scipy.stats``, or fail with an install hint."""

    _require("scipy", purpose="the correlation and interval helpers")
    from scipy import stats  # noqa: PLC0415 - deliberately lazy

    return stats


# --------------------------------------------------------------------------
# input and output
# --------------------------------------------------------------------------


def checked_input_file(path: str | os.PathLike[str], *, label: str) -> Path:
    """Resolve ``path`` to an existing, readable, size-bounded regular file."""

    candidate = Path(path).expanduser()
    if not candidate.exists():
        raise CliError(f"{label} does not exist: {candidate}")
    if not candidate.is_file():
        raise CliError(f"{label} is not a regular file: {candidate}")
    size = candidate.stat().st_size
    if size == 0:
        raise CliError(f"{label} is empty: {candidate}")
    if size > MAX_INPUT_BYTES:
        raise CliError(
            f"{label} is {size / 1e6:.1f} MB, above the {MAX_INPUT_BYTES / 1e6:.0f} MB limit; "
            "subset it before validating"
        )
    return candidate


def read_table(path: str | os.PathLike[str], *, label: str = "input") -> Any:
    """Read a CSV or TSV molecule table into a DataFrame."""

    pandas = require_pandas()
    source = checked_input_file(path, label=label)
    separator = "\t" if source.suffix.lower() in {".tsv", ".tab"} else ","
    try:
        frame = pandas.read_csv(source, sep=separator, engine="python")
    except Exception as exc:  # pandas raises several unrelated parser errors
        raise CliError(f"{label} could not be parsed as a delimited table: {exc}") from exc
    if frame.empty:
        raise CliError(f"{label} has a header but no data rows: {source}")
    if len(frame) > MAX_ROWS:
        raise CliError(f"{label} has {len(frame)} rows, above the {MAX_ROWS} row limit")
    return frame


def resolve_column(frame: Any, requested: str | None, *, kind: str, aliases: Sequence[str]) -> str:
    """Return the column to use, guessing from ``aliases`` when not requested."""

    if requested:
        if requested not in frame.columns:
            raise CliError(
                f"column {requested!r} (--{kind}-col) is not in the table; "
                f"available: {', '.join(map(str, frame.columns))}"
            )
        return requested
    for alias in aliases:
        if alias in frame.columns:
            return alias
    for alias in aliases:
        for column in frame.columns:
            if str(column).lower() == alias.lower():
                return str(column)
    raise CliError(
        f"no {kind} column found; name it explicitly with --{kind}-col "
        f"(looked for {', '.join(aliases)}; available: {', '.join(map(str, frame.columns))})"
    )


def emit_json(
    document: dict[str, Any],
    *,
    output: str | os.PathLike[str] | None = None,
    force: bool = False,
) -> None:
    """Print ``document`` as JSON, or write it to ``output``."""

    text = json.dumps(document, indent=2, ensure_ascii=False, default=str)
    if output is None:
        print(text)
        return
    destination = Path(output).expanduser()
    if destination.exists() and not force:
        raise CliError(f"{destination} exists; pass --force to overwrite it")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text + "\n", encoding="utf-8")


def print_to_stderr(*values: Any) -> None:
    """Write the human-readable summary to stderr.

    stdout carries the JSON document and nothing else, so a caller can pipe it
    straight into `jq` while still seeing the table in the terminal.
    """

    import sys as _sys  # noqa: PLC0415 - kept local to keep the module import-light

    print(*values, file=_sys.stderr)


# --------------------------------------------------------------------------
# structure handling
# --------------------------------------------------------------------------


def _clean_smiles(value: Any) -> str:
    """Return a stripped SMILES string, rejecting empty and oversized values."""

    if value is None:
        raise CliError("a structure value is missing")
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        raise CliError("a structure value is empty")
    if len(text) > MAX_SMILES_CHARS:
        raise CliError(f"a structure value is longer than {MAX_SMILES_CHARS} characters")
    return text


def canonicalize(smiles_values: Iterable[Any]) -> tuple[list[str | None], list[str]]:
    """Canonicalize SMILES, returning the values and one message per rejection.

    Unparseable rows are reported rather than dropped silently: the count of
    rejected structures belongs in the validation report, because a model that
    silently trained on 92% of the table is not the model the report describes.
    """

    Chem = require_rdkit()
    canonical: list[str | None] = []
    problems: list[str] = []
    for position, value in enumerate(smiles_values):
        try:
            text = _clean_smiles(value)
        except CliError as error:
            canonical.append(None)
            problems.append(f"row {position}: {error}")
            continue
        molecule = Chem.MolFromSmiles(text)
        if molecule is None:
            canonical.append(None)
            problems.append(f"row {position}: RDKit could not parse {text[:60]!r}")
            continue
        canonical.append(Chem.MolToSmiles(molecule))
    return canonical, problems


def morgan_generator(*, radius: int, bits: int) -> Any:
    """Return a Morgan fingerprint generator.

    RDKit 2024.09 deprecated `AllChem.GetMorganFingerprintAsBitVect` in favour of
    `rdFingerprintGenerator`, which also lets the generator be built once and
    reused across a whole table instead of rebuilding it per molecule.  The older
    entry point is still reached when the module is absent, so the scripts run on
    RDKit releases on both sides of that change.
    """

    _require("rdkit", purpose="computing molecular fingerprints")
    try:
        from rdkit.Chem import rdFingerprintGenerator  # noqa: PLC0415 - deliberately lazy
    except ImportError:  # pragma: no cover - RDKit older than 2024.09
        from rdkit.Chem import AllChem  # noqa: PLC0415 - deliberately lazy

        return ("legacy", AllChem, radius, bits)
    return (
        "modern",
        rdFingerprintGenerator.GetMorganGenerator(radius=radius, fpSize=bits),
        radius,
        bits,
    )


def morgan_fingerprints(
    smiles_values: Sequence[str],
    *,
    radius: int,
    bits: int,
    generator: Any = None,
) -> list[Any]:
    """Return Morgan fingerprints for already-canonical SMILES."""

    Chem = require_rdkit()
    handle = generator if generator is not None else morgan_generator(radius=radius, bits=bits)

    fingerprints = []
    for smiles in smiles_values:
        molecule = Chem.MolFromSmiles(smiles)
        if molecule is None:
            raise CliError(f"RDKit could not parse {smiles[:60]!r} after canonicalization")
        if handle[0] == "modern":
            fingerprints.append(handle[1].GetFingerprint(molecule))
        else:  # pragma: no cover - RDKit older than 2024.09
            fingerprints.append(handle[1].GetMorganFingerprintAsBitVect(molecule, radius, nBits=bits))
    return fingerprints


def morgan_feature_matrix(smiles_values: Sequence[str], *, radius: int, bits: int) -> Any:
    """Return a dense float matrix of Morgan bits, shaped for scikit-learn."""

    numpy = require_numpy()
    from rdkit.Chem import DataStructs  # noqa: PLC0415 - deliberately lazy

    generator = morgan_generator(radius=radius, bits=bits)
    fingerprints = morgan_fingerprints(
        smiles_values, radius=radius, bits=bits, generator=generator
    )
    matrix = numpy.zeros((len(fingerprints), bits), dtype=numpy.float32)
    for row, fingerprint in enumerate(fingerprints):
        DataStructs.ConvertToNumpyArray(fingerprint, matrix[row])
    return matrix


def bemis_murcko_scaffold(smiles: str) -> str:
    """Return the Bemis-Murcko scaffold of ``smiles`` as a canonical SMILES.

    Acyclic molecules have an empty scaffold.  They are returned as the empty
    string and grouped together, which is the behaviour that matters: a split
    that puts some acyclic molecules in train and the rest in test is a random
    split wearing a scaffold split's name.
    """

    Chem = require_rdkit()
    from rdkit.Chem.Scaffolds import MurckoScaffold  # noqa: PLC0415 - deliberately lazy

    molecule = Chem.MolFromSmiles(smiles)
    if molecule is None:
        raise CliError(f"RDKit could not parse {smiles[:60]!r} while computing a scaffold")
    scaffold = MurckoScaffold.MurckoScaffoldSmiles(mol=molecule, includeChirality=False)
    return scaffold


def scaffolds_for(smiles_values: Sequence[str]) -> list[str]:
    """Return one scaffold per SMILES, in input order."""

    return [bemis_murcko_scaffold(smiles) for smiles in smiles_values]


# --------------------------------------------------------------------------
# splits
# --------------------------------------------------------------------------


def random_split_indices(count: int, *, test_size: float, seed: int) -> tuple[list[int], list[int]]:
    """Split ``range(count)`` at random, returning ``(train, test)``."""

    if count < 2:
        raise CliError(f"a split needs at least 2 rows, got {count}")
    sklearn = require_sklearn()
    indices = list(range(count))
    train, test = sklearn["model_selection"].train_test_split(
        indices, test_size=test_size, random_state=seed, shuffle=True
    )
    return sorted(train), sorted(test)


def scaffold_split_indices(
    smiles_values: Sequence[str],
    *,
    test_size: float,
    seed: int,
) -> tuple[list[int], list[int]]:
    """Split by Bemis-Murcko scaffold so no scaffold appears on both sides.

    Scaffolds are assigned whole, largest first, until the test side reaches
    ``test_size``.  Ties are broken by a seeded shuffle so the split is
    reproducible yet not biased toward the order rows happen to appear in.
    """

    import random  # noqa: PLC0415 - only this function needs it

    count = len(smiles_values)
    if count < 2:
        raise CliError(f"a split needs at least 2 rows, got {count}")

    scaffolds = scaffolds_for(smiles_values)
    buckets: dict[str, list[int]] = {}
    for index, scaffold in enumerate(scaffolds):
        buckets.setdefault(scaffold, []).append(index)

    generator = random.Random(seed)
    # Largest scaffolds first; equal-sized groups are ordered by a seeded
    # shuffle so that neither the input order nor the scaffold string decides.
    ordered = list(buckets.items())
    generator.shuffle(ordered)
    ordered.sort(key=lambda item: len(item[1]), reverse=True)

    target = max(1, int(round(count * test_size)))
    test: list[int] = []
    train: list[int] = []
    for _, members in ordered:
        if len(test) + len(members) <= target or not test:
            test.extend(members)
        else:
            train.extend(members)

    if not train:  # a single scaffold covering everything cannot be split
        raise CliError(
            "every row shares one Bemis-Murcko scaffold, so a scaffold split cannot "
            "hold out anything; check that the structures are not all one series"
        )
    return sorted(train), sorted(test)


def group_split_indices(
    groups: Sequence[Any],
    *,
    test_size: float,
    seed: int,
) -> tuple[list[int], list[int]]:
    """Split so that no value of ``groups`` appears on both sides.

    Use this when the same compound was measured more than once, or when the
    table carries an explicit series/cluster column: a random split puts the
    same compound in train and test, which measures memorization.
    """

    import random  # noqa: PLC0415 - only this function needs it

    count = len(groups)
    if count < 2:
        raise CliError(f"a split needs at least 2 rows, got {count}")

    buckets: dict[str, list[int]] = {}
    for index, value in enumerate(groups):
        buckets.setdefault(str(value), []).append(index)

    generator = random.Random(seed)
    ordered = list(buckets.items())
    generator.shuffle(ordered)
    ordered.sort(key=lambda item: len(item[1]), reverse=True)

    target = max(1, int(round(count * test_size)))
    test: list[int] = []
    train: list[int] = []
    for _, members in ordered:
        if len(test) + len(members) <= target or not test:
            test.extend(members)
        else:
            train.extend(members)
    if not train:
        raise CliError("every row belongs to one group, so a group split holds nothing out")
    return sorted(train), sorted(test)


# --------------------------------------------------------------------------
# leakage
# --------------------------------------------------------------------------


def duplicate_leakage(
    train_smiles: Sequence[str],
    test_smiles: Sequence[str],
) -> dict[str, Any]:
    """Count exact-structure overlap between the two sides."""

    train_set = set(train_smiles)
    repeated = sorted({smiles for smiles in test_smiles if smiles in train_set})
    return {
        "exact_overlap_compounds": len(repeated),
        "exact_overlap_examples": repeated[:5],
    }


def near_duplicate_leakage(
    train_smiles: Sequence[str],
    test_smiles: Sequence[str],
    *,
    threshold: float,
    radius: int,
    bits: int,
) -> dict[str, Any]:
    """Count test compounds whose nearest training neighbour is very similar.

    This is the check random splits fail and scaffold splits are designed to
    pass.  The per-compound maximum similarity is returned as a distribution so
    the reader can pick their own threshold instead of inheriting this one.
    """

    numpy = require_numpy()
    from rdkit.Chem import DataStructs  # noqa: PLC0415 - deliberately lazy

    if not train_smiles or not test_smiles:
        return {"threshold": threshold, "near_duplicate_compounds": 0, "similarity_quantiles": {}}

    train_fingerprints = morgan_fingerprints(train_smiles, radius=radius, bits=bits)
    test_fingerprints = morgan_fingerprints(test_smiles, radius=radius, bits=bits)

    maxima = []
    for fingerprint in test_fingerprints:
        similarities = DataStructs.BulkTanimotoSimilarity(fingerprint, train_fingerprints)
        maxima.append(max(similarities))

    array = numpy.asarray(maxima, dtype=float)
    return {
        "threshold": threshold,
        "near_duplicate_compounds": int((array >= threshold).sum()),
        "test_compounds": len(maxima),
        "similarity_quantiles": {
            "min": float(numpy.min(array)),
            "median": float(numpy.median(array)),
            "max": float(numpy.max(array)),
        },
    }


def scaffold_overlap(
    train_smiles: Sequence[str],
    test_smiles: Sequence[str],
) -> dict[str, Any]:
    """Report how many test scaffolds also occur in training."""

    train_scaffolds = set(scaffolds_for(list(train_smiles)))
    test_scaffolds = scaffolds_for(list(test_smiles))
    shared = sorted({scaffold for scaffold in test_scaffolds if scaffold in train_scaffolds})
    return {
        "test_scaffolds": len(set(test_scaffolds)),
        "shared_scaffolds": len(shared),
        "shared_examples": shared[:5],
    }


# --------------------------------------------------------------------------
# metrics
# --------------------------------------------------------------------------


def regression_metrics(
    y_true: Sequence[float],
    y_pred: Sequence[float],
    *,
    train_mean: float | None = None,
) -> dict[str, Any]:
    """RMSE, MAE, R2, and RAE with the sample size attached.

    RAE is computed against ``train_mean`` when it is given, which is the
    definition benchmark suites use: the naive predictor is the training-set
    mean, not the test-set mean.  Passing the test mean instead makes a model
    look better than it is whenever the test set is not representative.
    """

    numpy = require_numpy()
    truth = numpy.asarray(y_true, dtype=float)
    prediction = numpy.asarray(y_pred, dtype=float)
    if truth.shape != prediction.shape:
        raise CliError(f"y_true has {truth.shape} and y_pred has {prediction.shape}")
    if truth.size == 0:
        raise CliError("no rows to score")
    if not numpy.isfinite(truth).all() or not numpy.isfinite(prediction).all():
        raise CliError("metrics need finite values; drop or impute missing targets first")

    residual = truth - prediction
    rmse = float(numpy.sqrt(numpy.mean(residual**2)))
    mae = float(numpy.mean(numpy.abs(residual)))

    spread = float(numpy.sum((truth - truth.mean()) ** 2))
    r2 = None if spread <= 0 else float(1.0 - numpy.sum(residual**2) / spread)

    baseline = float(train_mean) if train_mean is not None else float(truth.mean())
    denominator = float(numpy.sum(numpy.abs(truth - baseline)))
    rae = None if denominator <= 0 else float(numpy.sum(numpy.abs(residual)) / denominator)

    metrics: dict[str, Any] = {
        "n": int(truth.size),
        "rmse": rmse,
        "mae": mae,
        "r2": r2,
        "rae": rae,
        "baseline": baseline,
        "spearman": _spearman(truth, prediction),
    }
    return metrics


def _is_constant(values: Any) -> bool:
    """Report whether every element is identical.

    Counting distinct values rather than testing ``std() == 0`` is deliberate.  A
    constant array's standard deviation is not reliably zero: floating-point
    cancellation leaves the dummy regressor's repeated prediction with a std of
    about 1e-16, which passes a `== 0.0` test and lets a rank correlation be
    computed on a constant input.  That returned a warning here rather than a
    wrong number, but the same comparison in a filter would silently admit rows
    it should have rejected.
    """

    numpy = require_numpy()
    return numpy.unique(numpy.asarray(values)).size < 2


def _spearman(truth: Any, prediction: Any) -> float | None:
    """Rank correlation, or None when either side is constant."""

    try:
        stats = require_scipy()
    except CliError:
        return None
    if _is_constant(truth) or _is_constant(prediction):
        return None
    value = stats.spearmanr(truth, prediction).statistic
    return None if value is None or not math.isfinite(float(value)) else float(value)


def classification_metrics(
    y_true: Sequence[int],
    y_prob: Sequence[float],
    *,
    threshold: float = 0.5,
) -> dict[str, Any]:
    """ROC-AUC, PR-AUC, accuracy, and the class counts behind them.

    AUCs are returned as None when only one class is present.  That is not a
    missing value to paper over: a test split with no actives cannot support any
    claim about ranking actives.
    """

    numpy = require_numpy()
    sklearn = require_sklearn()
    metrics = sklearn["metrics"]

    truth = numpy.asarray(y_true, dtype=int)
    probability = numpy.asarray(y_prob, dtype=float)
    if truth.shape != probability.shape:
        raise CliError(f"y_true has {truth.shape} and y_prob has {probability.shape}")
    if truth.size == 0:
        raise CliError("no rows to score")
    if not numpy.isfinite(probability).all():
        raise CliError("probabilities must be finite")
    if probability.min() < 0.0 or probability.max() > 1.0:
        raise CliError("probabilities must lie in [0, 1]; pass scores through a sigmoid first")

    positives = int((truth == 1).sum())
    negatives = int((truth == 0).sum())
    both_present = positives > 0 and negatives > 0

    return {
        "n": int(truth.size),
        "n_positive": positives,
        "n_negative": negatives,
        "prevalence": positives / int(truth.size),
        "roc_auc": float(metrics.roc_auc_score(truth, probability)) if both_present else None,
        "pr_auc": float(metrics.average_precision_score(truth, probability)) if both_present else None,
        "accuracy": float(metrics.accuracy_score(truth, (probability >= threshold).astype(int))),
        "brier": float(metrics.brier_score_loss(truth, probability)),
        "threshold": threshold,
    }


def expected_calibration_error(
    y_true: Sequence[int],
    y_prob: Sequence[float],
    *,
    bins: int = 10,
) -> dict[str, Any]:
    """Equal-width expected calibration error plus the reliability curve.

    ECE answers the question AUC cannot: when the model says 0.8, how often is
    it right?  A model can rank perfectly and still be badly calibrated, which
    is exactly the case that misleads a go/no-go decision.
    """

    numpy = require_numpy()
    truth = numpy.asarray(y_true, dtype=float)
    probability = numpy.asarray(y_prob, dtype=float)
    if truth.shape != probability.shape:
        raise CliError(f"y_true has {truth.shape} and y_prob has {probability.shape}")
    if bins < 2:
        raise CliError("calibration needs at least 2 bins")

    edges = numpy.linspace(0.0, 1.0, bins + 1)
    curve = []
    total = truth.size
    error = 0.0
    for lower, upper in zip(edges[:-1], edges[1:]):
        # The last bin is closed on the right so that p == 1.0 is counted.
        if upper >= 1.0:
            mask = (probability >= lower) & (probability <= upper)
        else:
            mask = (probability >= lower) & (probability < upper)
        count = int(mask.sum())
        if count == 0:
            curve.append({"lower": float(lower), "upper": float(upper), "n": 0,
                          "mean_predicted": None, "observed_frequency": None})
            continue
        mean_predicted = float(probability[mask].mean())
        observed = float(truth[mask].mean())
        error += (count / total) * abs(observed - mean_predicted)
        curve.append({
            "lower": float(lower),
            "upper": float(upper),
            "n": count,
            "mean_predicted": mean_predicted,
            "observed_frequency": observed,
        })

    return {"ece": float(error), "bins": bins, "curve": curve}


def bootstrap_interval(
    metric: Callable[[Any, Any], float | None],
    y_true: Sequence[Any],
    y_pred: Sequence[Any],
    *,
    resamples: int = 1000,
    seed: int = DEFAULT_SEED,
    confidence: float = 0.95,
) -> dict[str, Any]:
    """Percentile bootstrap interval for a metric.

    Resamples that make the metric undefined (a bootstrap draw containing only
    one class, say) are discarded and counted, because silently treating them as
    zero would widen or narrow the interval for the wrong reason.
    """

    numpy = require_numpy()
    truth = numpy.asarray(y_true)
    prediction = numpy.asarray(y_pred)
    if truth.shape[0] != prediction.shape[0]:
        raise CliError("bootstrap needs y_true and y_pred of equal length")
    count = truth.shape[0]
    if count < 2:
        raise CliError("bootstrap needs at least 2 rows")

    generator = numpy.random.default_rng(seed)
    values = []
    discarded = 0
    for _ in range(resamples):
        positions = generator.integers(0, count, size=count)
        try:
            value = metric(truth[positions], prediction[positions])
        except Exception:  # a degenerate draw is expected, not a bug
            value = None
        if value is None or not math.isfinite(float(value)):
            discarded += 1
            continue
        values.append(float(value))

    if not values:
        return {"point": None, "low": None, "high": None, "resamples": resamples,
                "discarded": discarded, "confidence": confidence}

    alpha = (1.0 - confidence) / 2.0
    return {
        "point": metric(truth, prediction),
        "low": float(numpy.quantile(values, alpha)),
        "high": float(numpy.quantile(values, 1.0 - alpha)),
        "resamples": resamples,
        "discarded": discarded,
        "confidence": confidence,
    }


# --------------------------------------------------------------------------
# model fitting
# --------------------------------------------------------------------------


def fit_predict(
    train_features: Any,
    train_targets: Sequence[Any],
    test_features: Any,
    *,
    task: str,
    seed: int,
    n_estimators: int = 256,
) -> dict[str, Any]:
    """Fit a random forest and a dummy baseline, returning both predictions.

    The forest is a stand-in for whatever model is actually under review; it is
    fixed here so that the *split*, not the learner, is what differs between the
    rows of a comparison.  The dummy predictor is fitted on the same training
    fold, because "beats the majority class" is the floor every other number has
    to clear.
    """

    numpy = require_numpy()
    sklearn = require_sklearn()

    targets = numpy.asarray(train_targets)
    if task == "classification":
        model = sklearn["ensemble"].RandomForestClassifier(
            n_estimators=n_estimators, random_state=seed, n_jobs=1
        )
        baseline = sklearn["dummy"].DummyClassifier(strategy="most_frequent", random_state=seed)
    elif task == "regression":
        model = sklearn["ensemble"].RandomForestRegressor(
            n_estimators=n_estimators, random_state=seed, n_jobs=1
        )
        baseline = sklearn["dummy"].DummyRegressor(strategy="mean")
    else:
        raise CliError(f"task must be 'classification' or 'regression', got {task!r}")

    if len(numpy.unique(targets)) < 2:
        raise CliError(
            "the training side of this split has only one distinct target value; "
            "widen the split or check the label column"
        )

    model.fit(train_features, targets)
    baseline.fit(train_features, targets)

    if task == "classification":
        return {
            "model": model.predict_proba(test_features)[:, 1],
            "baseline": baseline.predict_proba(test_features)[:, 1],
        }
    return {
        "model": model.predict(test_features),
        "baseline": baseline.predict(test_features),
    }


def as_classification_labels(values: Sequence[Any], *, threshold: float | None) -> list[int]:
    """Turn a numeric or boolean activity column into 0/1 labels.

    A threshold has to come from the caller.  Choosing it here -- at the median,
    or at whatever splits the data most evenly -- would manufacture a balanced
    problem out of an imbalanced one and inflate every metric downstream.
    """

    numpy = require_numpy()
    array = numpy.asarray(values)
    if array.dtype == bool:
        return [int(value) for value in array]
    try:
        numeric = array.astype(float)
    except (TypeError, ValueError) as exc:
        raise CliError(
            "classification needs a numeric activity column plus --active-threshold; "
            f"got values like {array[:3]!r}"
        ) from exc
    if threshold is None:
        raise CliError(
            "classification needs --active-threshold to say what counts as active "
            "(for example --active-threshold 6.0 on a pIC50 column)"
        )
    return [int(value >= threshold) for value in numeric]


# --------------------------------------------------------------------------
# formatting
# --------------------------------------------------------------------------


def format_number(value: Any, *, digits: int = 3) -> str:
    """Format a metric for the human-readable table, or '-' when undefined."""

    if value is None:
        return "-"
    if isinstance(value, float):
        if not math.isfinite(value):
            return "-"
        return f"{value:.{digits}f}"
    return str(value)


def format_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    """Render a fixed-width table; the scripts print this next to their JSON."""

    widths = [len(str(header)) for header in headers]
    for row in rows:
        for position, cell in enumerate(row):
            widths[position] = max(widths[position], len(str(cell)))
    lines = [
        "  ".join(str(header).ljust(widths[position]) for position, header in enumerate(headers)),
        "  ".join("-" * width for width in widths),
    ]
    for row in rows:
        lines.append(
            "  ".join(str(cell).ljust(widths[position]) for position, cell in enumerate(row))
        )
    return "\n".join(lines)


def slugify(text: str) -> str:
    """Return a filesystem-safe slug, used for naming per-target outputs."""

    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", text.strip()).strip("-")
    return cleaned or "table"

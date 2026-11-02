"""Evaluate binary target containers through the real training pipeline."""

from pathlib import Path
import sys

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "scikit-learn"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

np = pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")
pytest.importorskip("sklearn")

from sklearn.metrics import roc_auc_score  # noqa: E402
import classification_pipeline  # noqa: E402


@pytest.mark.parametrize("container", [list, tuple, np.array, pd.Series])
def test_string_target_containers_produce_binary_roc_auc(container):
    frame = pd.DataFrame({"value": np.arange(40)})
    labels = ["case"] * 20 + ["control"] * 20
    target = container(labels)
    result = classification_pipeline.train_and_evaluate_model(
        frame, target, ["value"], [], cv=2, test_size=0.25,
    )
    # Preserve the estimator's class order, not an assumed semantic case label.
    assert list(result["classes"]) == ["case", "control"]
    assert result["positive_class"] == "control"
    expected = roc_auc_score(result["y_test"], result["y_pred_proba"][:, 1])
    assert result["metrics"]["roc_auc"] == pytest.approx(expected)
    assert np.asarray(target).tolist() == labels


def test_numeric_list_target_preserves_binary_roc_auc():
    frame = pd.DataFrame({"value": np.arange(40)})
    target = [2] * 20 + [7] * 20
    result = classification_pipeline.train_and_evaluate_model(
        frame, target, ["value"], [], cv=2, test_size=0.25,
    )
    assert result["positive_class"] == 7
    expected = roc_auc_score(result["y_test"], result["y_pred_proba"][:, 1])
    assert result["metrics"]["roc_auc"] == pytest.approx(expected)
    assert target == [2] * 20 + [7] * 20

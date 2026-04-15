"""
moa_classifier.py
=================
Machine-learning based mechanism-of-action (MoA) classification from
quantitative proteomics signatures.

Workflow:
    1. build_reference_signatures  – define known MoA proteome fingerprints
    2. train_moa_classifier        – fit RandomForest on reference data
    3. predict_moa                 – classify a query compound's MoA
    4. get_feature_importance      – identify the most informative proteins
    5. compute_moa_similarity      – cosine similarity to reference signatures

Reference MoA classes included:
    MDM2_inhibitor   – p53 stabilisation without DNA damage (Nutlin-3a-like)
    DNA_damaging     – ATM/ATR activation + broad DNA damage response
    HDAC_inhibitor   – histone deacetylase inhibition (acetylation-driven)
    CDK_inhibitor    – CDK4/6 arrest without p53 induction
    Proteasome_inhib – UPS overload, global proteome disruption
    Negative_control – DMSO vehicle (no significant changes)

Skill references:
    scikit-learn/SKILL.md         – RandomForest, Pipeline, GridSearchCV,
                                    feature_importances_, cross_val_score
    scikit-learn/scripts/classification_pipeline.py – pipeline patterns
    statistical-analysis/SKILL.md – cross-validation, effect size
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import anndata as ad
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.decomposition import PCA
from scipy.spatial.distance import cosine


# ---------------------------------------------------------------------------
# Reference MoA protein signatures
# (log2FC expected at 24h, high-dose treatment in MCF7-like cells)
# ---------------------------------------------------------------------------

_REFERENCE_SIGNATURES: dict[str, dict[str, float]] = {
    "MDM2_inhibitor": {
        # Strong p53 stabilization, no DNA damage
        "TP53": +2.5, "MDM2": +4.0, "CDKN1A": +5.0, "MDM4": +1.5,
        "GADD45A": +3.0, "SESN1": +2.0, "SESN2": +2.0, "TIGAR": +1.5,
        "BBC3": +2.5, "PMAIP1": +2.0, "BAX": +1.5, "CASP3": +2.0,
        "CCNE1": -2.5, "CCNE2": -2.0, "CDK2": -1.0, "MYC": -2.0,
        "MCM2": -1.5, "ATM": +0.5, "CHEK1": +0.5,   # minimal DNA damage
    },
    "DNA_damaging": {
        # ATM/ATR activation → p53, plus broad DDR markers
        "TP53": +2.0, "MDM2": +2.5, "CDKN1A": +4.0,
        "H2AX": +3.5, "ATM": +2.0, "CHEK1": +2.5, "CHEK2": +2.5,
        "BRCA1": +1.5, "RAD51": +1.5, "FANCD2": +1.5,
        "BBC3": +3.0, "PMAIP1": +2.5, "BAX": +2.5, "CASP3": +3.0,
        "GADD45A": +3.5, "CCNE1": -3.0, "CDK2": -2.0, "CCNB1": -2.5,
        "MYC": -2.5, "MCM2": -2.5, "PCNA": -2.0,
        "MDM4": +0.3,   # less MDM4 induction vs MDM2i
    },
    "HDAC_inhibitor": {
        # Hyperacetylation → p21 induction, but different upstream
        "CDKN1A": +4.5, "GADD45A": +2.0,
        "TP53": +1.0,   # moderate p53 – not the primary driver
        "MDM2": +1.5,
        "MYC": -2.5, "CCND1": -2.5, "CDK4": -1.5, "E2F1": -2.5,
        "CCNB1": -3.0, "CDK1": -2.5, "AURKA": -2.5, "BIRC5": -3.0,
        "BBC3": +2.0, "CASP3": +2.5,
        "BCL2": -1.5, "MCL1": -2.0,
        "ATM": +0.8, "H2AX": +1.0,   # secondary DDR
        "SESN1": +1.0, "TIGAR": +0.5,
    },
    "CDK_inhibitor": {
        # CDK4/6 inhibitor: G1 arrest without direct p53 activation
        "CDKN1A": +2.0,   # via RB pathway
        "CDK4": -0.5, "CDK6": -0.5, "CCND1": -1.5, "CCND2": -1.5,
        "E2F1": -3.0, "E2F2": -2.5,
        "CCNE1": -1.0, "CDK2": -1.0,
        "MCM2": -2.0, "PCNA": -2.0, "MKI67": -3.0, "TOP2A": -3.0,
        "MYC": -1.0,
        "TP53": +0.2,   # minimal p53 activation
        "MDM2": +0.3,
        "BBC3": +0.5, "BAX": +0.3,   # minimal apoptosis at cytostatic doses
    },
    "Proteasome_inhibitor": {
        # UPS overload: ER stress, UPR, p53 accumulation via global degradation block
        "TP53": +1.5,   # p53 accumulates but not fully activated
        "CDKN1A": +1.5, "MDM2": +1.0,
        "HSP90AA1": +3.0, "HSPA5": +3.5, "DDIT3": +3.0,  # UPR / ER stress
        "SQSTM1": +3.0, "UBIQUITIN": +3.5,                 # ubiquitin accumulation
        "BBC3": +2.0, "PMAIP1": +3.0, "MCL1": +2.0,        # MCL1 accumulates
        "CASP3": +3.0, "CASP4": +2.5,
        "CCNB1": -1.5, "CDK1": -1.5,
        "ATF3": +2.5, "ATF4": +2.5,                         # stress TFs
    },
    "Negative_control": {
        # DMSO / vehicle: no significant changes
        "TP53": 0.0, "MDM2": 0.0, "CDKN1A": 0.0,
        "H2AX": 0.0, "CASP3": 0.0, "BBC3": 0.0,
        "CDK2": 0.0, "CCNE1": 0.0, "MYC": 0.0,
    },
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_reference_signatures(
    extra_signatures: dict[str, dict[str, float]] | None = None,
) -> dict[str, dict[str, float]]:
    """
    Return the built-in MoA reference signatures, optionally extended.

    Each signature is a dict mapping gene symbol → expected log2FC at
    24 h, high-dose treatment.

    Parameters
    ----------
    extra_signatures:  Additional MoA signatures to merge in.
    """
    sigs = _REFERENCE_SIGNATURES.copy()
    if extra_signatures:
        sigs.update(extra_signatures)
    return sigs


def train_moa_classifier(
    diff_df: pd.DataFrame,
    signatures: dict[str, dict[str, float]] | None = None,
    feature_genes: list[str] | None = None,
    n_estimators: int = 300,
    max_depth: int | None = 8,
    n_augment: int = 50,
    noise_std: float = 0.3,
    cv_folds: int = 5,
    random_state: int = 42,
) -> dict:
    """
    Train a RandomForest MoA classifier on synthetic reference data
    generated from built-in MoA signatures.

    Because real reference datasets are rarely available, the training set
    is synthesised by adding Gaussian noise to each reference signature
    (n_augment replicates per class).  This creates a classifier that can
    recognise broad MoA categories from fold-change vectors.

    Parameters
    ----------
    diff_df:       Output of run_differential_abundance().  Used only to
                   define the feature space (gene list).
    signatures:    MoA reference signatures; uses built-in if None.
    feature_genes: Subset of genes to use as features.  Auto-selected as
                   the union of signature genes if None.
    n_augment:     Synthetic replicates per MoA class for training.
    noise_std:     SD of Gaussian noise added to each replicate.
    cv_folds:      Stratified k-fold cross-validation folds.

    Returns
    -------
    dict with keys:
        'pipeline'           – fitted sklearn Pipeline (scaler → RF)
        'feature_genes'      – ordered gene list used as features
        'label_encoder'      – LabelEncoder for class names
        'cv_accuracy'        – mean ± std cross-validation accuracy
        'feature_importances'– pd.Series (gene → importance)
        'class_names'        – list of MoA class names
    """
    signatures = signatures or build_reference_signatures()
    rng = np.random.default_rng(random_state)

    # Feature space = union of all signature genes that appear in diff_df
    all_sig_genes = {g for sig in signatures.values() for g in sig}
    available = set(diff_df["gene"].unique())
    if feature_genes is None:
        feature_genes = sorted(all_sig_genes & available)

    if len(feature_genes) < 5:
        raise ValueError(
            f"Only {len(feature_genes)} signature genes found in diff_df. "
            "Check that gene names match."
        )

    # Build training matrix by augmenting each reference signature
    X_train, y_train = [], []
    for moa_label, sig_dict in signatures.items():
        base_vector = np.array([sig_dict.get(g, 0.0) for g in feature_genes])
        for _ in range(n_augment):
            noise = rng.normal(0, noise_std, size=len(feature_genes))
            X_train.append(base_vector + noise)
            y_train.append(moa_label)

    X_train = np.array(X_train)
    y_train = np.array(y_train)

    le = LabelEncoder().fit(y_train)
    y_enc = le.transform(y_train)

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf",    RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            class_weight="balanced",
            random_state=random_state,
            n_jobs=-1,
        )),
    ])

    # Cross-validation
    cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
    cv_scores = cross_val_score(pipeline, X_train, y_enc, cv=cv, scoring="accuracy")
    print(
        f"[train_moa_classifier] CV accuracy = "
        f"{cv_scores.mean():.3f} ± {cv_scores.std():.3f}  "
        f"({len(feature_genes)} feature genes, {len(signatures)} MoA classes)"
    )

    pipeline.fit(X_train, y_enc)

    # Feature importances
    rf = pipeline.named_steps["clf"]
    importances = pd.Series(
        rf.feature_importances_, index=feature_genes
    ).sort_values(ascending=False)

    return {
        "pipeline":            pipeline,
        "feature_genes":       feature_genes,
        "label_encoder":       le,
        "cv_accuracy":         (cv_scores.mean(), cv_scores.std()),
        "feature_importances": importances,
        "class_names":         le.classes_.tolist(),
    }


def predict_moa(
    diff_df: pd.DataFrame,
    classifier: dict,
    condition: str | None = None,
    timepoint: str | None = None,
) -> pd.DataFrame:
    """
    Predict MoA class probabilities for each (condition, timepoint) pair.

    Parameters
    ----------
    diff_df:     Output of run_differential_abundance().
    classifier:  Dict returned by train_moa_classifier().
    condition:   Predict only for this condition.
    timepoint:   Predict only for this timepoint.

    Returns
    -------
    pd.DataFrame  indexed by (condition, timepoint) with columns:
        predicted_moa, confidence, plus one column per MoA class with
        class probabilities.
    """
    pipeline     = classifier["pipeline"]
    feature_genes = classifier["feature_genes"]
    le            = classifier["label_encoder"]

    # Subset
    mask = pd.Series([True] * len(diff_df), index=diff_df.index)
    if condition:
        mask &= diff_df["condition"] == condition
    if timepoint:
        mask &= diff_df["timepoint"] == timepoint

    sub = diff_df[mask].copy()
    combos = sub[["condition", "timepoint"]].drop_duplicates().values

    rows = []
    for cond, tp in combos:
        ctp_mask = (sub["condition"] == cond) & (sub["timepoint"] == tp)
        ctp_df = sub[ctp_mask].set_index("gene")["log2FC"].reindex(
            feature_genes, fill_value=0.0
        )
        x = ctp_df.values.reshape(1, -1)
        proba = pipeline.predict_proba(x)[0]
        pred_idx = np.argmax(proba)
        pred_moa = le.inverse_transform([pred_idx])[0]
        row = {
            "condition": cond,
            "timepoint": tp,
            "predicted_moa": pred_moa,
            "confidence": proba[pred_idx],
        }
        for i, cls in enumerate(le.classes_):
            row[f"prob_{cls}"] = proba[i]
        rows.append(row)

    result = pd.DataFrame(rows).sort_values(["condition", "timepoint"])
    print(
        f"[predict_moa] Predictions for "
        f"{len(result)} condition × timepoint combinations"
    )
    for _, r in result.iterrows():
        print(
            f"  {r['condition']:20s} @ {r['timepoint']:5s} → "
            f"{r['predicted_moa']} (confidence={r['confidence']:.2f})"
        )
    return result


def compute_moa_similarity(
    diff_df: pd.DataFrame,
    signatures: dict[str, dict[str, float]] | None = None,
    condition: str | None = None,
    timepoint: str | None = None,
) -> pd.DataFrame:
    """
    Compute cosine similarity between each (condition, timepoint) fold-change
    vector and each reference MoA signature.

    Unlike predict_moa (probabilistic), this gives a continuous similarity
    score useful for heatmap visualisation and ranking.

    Returns
    -------
    pd.DataFrame  (comparisons × MoA classes), values ∈ [-1, 1].
    """
    signatures = signatures or build_reference_signatures()
    feature_genes = sorted({g for sig in signatures.values() for g in sig})

    mask = pd.Series([True] * len(diff_df), index=diff_df.index)
    if condition:
        mask &= diff_df["condition"] == condition
    if timepoint:
        mask &= diff_df["timepoint"] == timepoint

    sub = diff_df[mask].copy()
    combos = sub[["condition", "timepoint"]].drop_duplicates().values

    rows = []
    for cond, tp in combos:
        ctp_mask = (sub["condition"] == cond) & (sub["timepoint"] == tp)
        query_vec = (
            sub[ctp_mask].set_index("gene")["log2FC"]
            .reindex(feature_genes, fill_value=0.0)
            .values
        )
        row = {"condition": cond, "timepoint": tp}
        for moa, sig_dict in signatures.items():
            ref_vec = np.array([sig_dict.get(g, 0.0) for g in feature_genes])
            # Cosine similarity: 1 - cosine distance
            q_norm = np.linalg.norm(query_vec)
            r_norm = np.linalg.norm(ref_vec)
            if q_norm == 0 or r_norm == 0:
                sim = 0.0
            else:
                sim = float(np.dot(query_vec, ref_vec) / (q_norm * r_norm))
            row[moa] = round(sim, 4)
        rows.append(row)

    result = pd.DataFrame(rows).set_index(["condition", "timepoint"])
    return result

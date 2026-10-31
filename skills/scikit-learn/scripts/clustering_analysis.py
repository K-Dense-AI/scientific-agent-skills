"""
Clustering analysis example with multiple algorithms, evaluation, and visualization.
"""

import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.mixture import GaussianMixture
from sklearn.metrics import (
    silhouette_score, calinski_harabasz_score, davies_bouldin_score
)
from sklearn.utils.validation import check_array


def preprocess_for_clustering(X, scale=True, pca_components=None):
    """
    Preprocess data for clustering.

    Parameters:
    -----------
    X : array-like
        Feature matrix
    scale : bool
        Whether to standardize features
    pca_components : int or None
        Number of PCA components (None to skip PCA)

    Returns:
    --------
    array
        Preprocessed data
    """
    X_processed = check_array(X, ensure_min_samples=2, copy=True)

    if scale:
        scaler = StandardScaler()
        X_processed = scaler.fit_transform(X_processed)

    if pca_components is not None:
        pca = PCA(n_components=pca_components)
        X_processed = pca.fit_transform(X_processed)
        print(f"PCA: Explained variance ratio = {pca.explained_variance_ratio_.sum():.3f}")

    return X_processed


def find_optimal_k_kmeans(X, k_range=range(2, 11)):
    """
    Explore candidate K values with inertia and silhouette; no truth guarantee.

    Parameters:
    -----------
    X : array-like
        Feature matrix (should be scaled)
    k_range : range
        Range of K values to test

    Returns:
    --------
    dict
        Dictionary with inertia and silhouette scores for each K
    """
    X = check_array(X, ensure_min_samples=3)
    k_range = list(k_range)
    if not k_range or any(not isinstance(k, (int, np.integer)) or
                          not 2 <= k < len(X) for k in k_range):
        raise ValueError("k_range must contain integers with 2 <= k < n_samples")
    inertias = []
    silhouette_scores = []

    for k in k_range:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X)

        inertias.append(kmeans.inertia_)
        # Duplicate rows can collapse requested clusters; an undefined metric
        # must not be ranked as evidence for a particular K.
        score = clustering_metrics(X, labels)['silhouette']
        silhouette_scores.append(np.nan if score is None else score)

    if not np.isfinite(silhouette_scores).any():
        raise ValueError("No candidate produced 2 <= distinct labels < n_samples")

    # Plot results
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

    # Elbow plot
    ax1.plot(k_range, inertias, 'bo-')
    ax1.set_xlabel('Number of clusters (K)')
    ax1.set_ylabel('Inertia')
    ax1.set_title('Elbow Method')
    ax1.grid(True)

    # Silhouette plot
    ax2.plot(k_range, silhouette_scores, 'ro-')
    ax2.set_xlabel('Number of clusters (K)')
    ax2.set_ylabel('Silhouette Score')
    ax2.set_title('Silhouette Analysis')
    ax2.grid(True)

    plt.tight_layout()
    plt.savefig('clustering_optimization.png', dpi=300, bbox_inches='tight')
    print("Saved: clustering_optimization.png")
    plt.close()

    # Find best K based on silhouette score
    best_k = k_range[int(np.nanargmax(silhouette_scores))]
    print(f"\nCandidate K with highest silhouette (exploratory): {best_k}")

    return {
        'k_values': list(k_range),
        'inertias': inertias,
        'silhouette_scores': silhouette_scores,
        'best_k': best_k
    }


def clustering_metrics(X, labels):
    """Score an explicit set of rows, preserving undefined metrics as None."""
    n_labels = len(np.unique(labels))
    if not 2 <= n_labels < len(labels):
        return dict(silhouette=None, calinski_harabasz=None, davies_bouldin=None,
                    metric_reason="Requires 2 <= distinct labels < scored samples")
    return dict(silhouette=float(silhouette_score(X, labels)),
                calinski_harabasz=float(calinski_harabasz_score(X, labels)),
                davies_bouldin=float(davies_bouldin_score(X, labels)),
                metric_reason=None)


def compare_clustering_algorithms(X, n_clusters=3):
    """Compare exploratory Euclidean clusterings on finite numeric features.

    DBSCAN scores exclude noise and therefore describe a different population;
    use n_scored/coverage and metric_reason when interpreting its scores.
    Internal scores alone do not establish scientific clusters.
    """
    X = check_array(X, ensure_min_samples=2)
    if not isinstance(n_clusters, (int, np.integer)) or not 1 <= n_clusters <= len(X):
        raise ValueError("n_clusters must be an integer between 1 and n_samples")
    algorithms = {
        'K-Means': KMeans(n_clusters=n_clusters, random_state=42, n_init=10),
        'Agglomerative': AgglomerativeClustering(n_clusters=n_clusters, linkage='ward'),
        'Gaussian Mixture': GaussianMixture(n_components=n_clusters, random_state=42),
        'DBSCAN': DBSCAN(eps=0.5, min_samples=5),
    }
    results = {}
    for name, algorithm in algorithms.items():
        labels = algorithm.fit_predict(X)
        mask = labels != -1
        n_scored = int(mask.sum())
        result = dict(labels=labels, n_clusters=len(np.unique(labels[mask])),
                      n_noise=int((~mask).sum()), n_scored=n_scored,
                      coverage=n_scored / len(X),
                      **clustering_metrics(X[mask], labels[mask]))
        results[name] = result
        print(f"\n{name}: {result['n_clusters']} clusters; "
              f"{result['n_noise']} noise; coverage={result['coverage']:.1%}")
        for metric in ('silhouette', 'calinski_harabasz', 'davies_bouldin'):
            value = result[metric]
            print(f"  {metric}: {value:.4f}" if value is not None else f"  {metric}: undefined")
        if result['metric_reason']:
            print(f"  {result['metric_reason']}")
    return results


def visualize_clusters(X, results, true_labels=None):
    """
    Visualize clustering results using PCA for 2D projection.

    Parameters:
    -----------
    X : array-like
        Feature matrix
    results : dict
        Dictionary with clustering results
    true_labels : array-like or None
        True labels (if available) for comparison
    """
    X = check_array(X, ensure_min_samples=2, ensure_min_features=2)
    if not results and true_labels is None:
        raise ValueError("At least one clustering result or true_labels is required")
    # Reduce to 2D using PCA (display only; scores use the clustering space).
    pca = PCA(n_components=2)
    X_2d = pca.fit_transform(X)

    # Determine number of subplots
    n_plots = len(results)
    if true_labels is not None:
        n_plots += 1

    n_cols = min(3, n_plots)
    n_rows = (n_plots + n_cols - 1) // n_cols

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(5*n_cols, 4*n_rows))
    if n_plots == 1:
        axes = np.array([axes])
    axes = axes.flatten()

    plot_idx = 0

    # Plot true labels if available
    if true_labels is not None:
        ax = axes[plot_idx]
        scatter = ax.scatter(X_2d[:, 0], X_2d[:, 1], c=true_labels, cmap='viridis', alpha=0.6)
        ax.set_title('True Labels')
        ax.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.2%})')
        ax.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.2%})')
        plt.colorbar(scatter, ax=ax)
        plot_idx += 1

    # Plot clustering results
    for name, result in results.items():
        ax = axes[plot_idx]
        labels = result['labels']

        scatter = ax.scatter(X_2d[:, 0], X_2d[:, 1], c=labels, cmap='viridis', alpha=0.6)

        # Highlight noise points for DBSCAN
        if name == 'DBSCAN' and -1 in labels:
            noise_mask = labels == -1
            ax.scatter(X_2d[noise_mask, 0], X_2d[noise_mask, 1],
                      c='red', marker='x', s=100, label='Noise', alpha=0.8)
            ax.legend()

        title = f"{name} (K={result['n_clusters']})"
        if result.get('silhouette') is not None:
            title += f"\nSilhouette: {result['silhouette']:.3f}"
        title += f"\nCoverage: {result.get('coverage', 1.0):.0%}"
        ax.set_title(title)
        ax.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.2%})')
        ax.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.2%})')
        plt.colorbar(scatter, ax=ax)

        plot_idx += 1

    # Hide unused subplots
    for idx in range(plot_idx, len(axes)):
        axes[idx].axis('off')

    plt.tight_layout()
    plt.savefig('clustering_results.png', dpi=300, bbox_inches='tight')
    print("\nSaved: clustering_results.png")
    plt.close()


def complete_clustering_analysis(X, true_labels=None, scale=True,
                                 find_k=True, k_range=range(2, 11), n_clusters=3):
    """
    Complete clustering analysis workflow.

    Parameters:
    -----------
    X : array-like
        Feature matrix
    true_labels : array-like or None
        True labels (for comparison only, not used in clustering)
    scale : bool
        Whether to scale features
    find_k : bool
        Whether to search for optimal K
    k_range : range
        Range of K values to test
    n_clusters : int
        Number of clusters to use in comparison

    Returns:
    --------
    dict
        Dictionary with all analysis results
    """
    print("="*60)
    print("Clustering Analysis")
    print("="*60)
    print(f"Data shape: {X.shape}")

    # Preprocess data
    X_processed = preprocess_for_clustering(X, scale=scale)

    # Find optimal K if requested
    optimization_results = None
    if find_k:
        print("\n" + "="*60)
        print("Finding Optimal Number of Clusters")
        print("="*60)
        optimization_results = find_optimal_k_kmeans(X_processed, k_range=k_range)

        # Use recommended K
        if optimization_results:
            n_clusters = optimization_results['best_k']

    # Compare clustering algorithms
    comparison_results = compare_clustering_algorithms(X_processed, n_clusters=n_clusters)

    # Visualize results
    print("\n" + "="*60)
    print("Visualizing Results")
    print("="*60)
    visualize_clusters(X_processed, comparison_results, true_labels=true_labels)

    return {
        'X_processed': X_processed,
        'optimization': optimization_results,
        'comparison': comparison_results
    }


# Example usage
if __name__ == "__main__":
    from sklearn.datasets import load_iris, make_blobs

    print("="*60)
    print("Example 1: Iris Dataset")
    print("="*60)

    # Load Iris dataset
    iris = load_iris()
    X_iris = iris.data
    y_iris = iris.target

    results_iris = complete_clustering_analysis(
        X_iris,
        true_labels=y_iris,
        scale=True,
        find_k=True,
        k_range=range(2, 8),
        n_clusters=3
    )

    print("\n" + "="*60)
    print("Example 2: Synthetic Dataset with Noise")
    print("="*60)

    # Create synthetic dataset
    X_synth, y_synth = make_blobs(
        n_samples=500, n_features=2, centers=4,
        cluster_std=0.5, random_state=42
    )

    # Add noise points
    noise = np.random.default_rng(42).normal(size=(50, 2)) * 3
    X_synth = np.vstack([X_synth, noise])
    y_synth_with_noise = np.concatenate([y_synth, np.full(50, -1)])

    results_synth = complete_clustering_analysis(
        X_synth,
        true_labels=y_synth_with_noise,
        scale=True,
        find_k=True,
        k_range=range(2, 8),
        n_clusters=4
    )

    print("\n" + "="*60)
    print("Analysis Complete!")
    print("="*60)

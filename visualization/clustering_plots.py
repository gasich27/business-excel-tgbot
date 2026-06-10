from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import plotly.express as px
import pandas as pd

from analysis.clustering import ClusteringResult


def create_cluster_plot_png(result: ClusteringResult, output_path: str) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    embedding = _embedding(result)
    fig, ax = plt.subplots(figsize=(10, 7))
    scatter = ax.scatter(embedding[:, 0], embedding[:, 1], c=result.labels, cmap="tab20", s=18, alpha=0.8)
    ax.set_title(f"Кластеризация данных: {result.method}")
    ax.set_xlabel("UMAP-1")
    ax.set_ylabel("UMAP-2")
    ax.grid(True, alpha=0.25)
    fig.colorbar(scatter, ax=ax, label="cluster")
    subtitle = f"clusters={result.n_clusters}; noise={result.noise_count}; silhouette={result.silhouette_score}"
    fig.text(0.01, 0.01, subtitle, fontsize=8)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(path)


def create_cluster_plot_html(result: ClusteringResult, output_path: str) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    embedding = _embedding(result)
    data = pd.DataFrame({"x": embedding[:, 0], "y": embedding[:, 1], "cluster": result.labels.astype(str)})
    fig = px.scatter(data, x="x", y="y", color="cluster", title=f"Кластеризация данных: {result.method}")
    fig.write_html(path, include_plotlyjs="cdn")
    return str(path)


def _embedding(result: ClusteringResult):
    if result.embedding_2d is not None:
        return result.embedding_2d
    return pd.DataFrame({"x": range(len(result.labels)), "y": result.labels}).to_numpy()

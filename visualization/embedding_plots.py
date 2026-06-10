from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from analysis.embedding_comparison import EmbeddingComparisonResult


def create_embedding_comparison_png(result: EmbeddingComparisonResult, output_path: str) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    _scatter(axes[0], result.pca_embedding, "PCA")
    _scatter(axes[1], result.umap_embedding, "UMAP")
    if result.tsne_embedding is not None:
        _scatter(axes[2], result.tsne_embedding, "t-SNE")
    else:
        axes[2].text(0.5, 0.5, "t-SNE не построен", ha="center", va="center")
        axes[2].set_title("t-SNE")
    fig.suptitle("PCA / UMAP / t-SNE сравнение структуры данных")
    fig.text(0.01, 0.01, f"Строк: {result.sample_size} из {result.total_rows}. Признаки: {', '.join(result.used_columns[:8])}", fontsize=8)
    fig.tight_layout(rect=(0, 0.06, 1, 0.95))
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(path)


def create_embedding_comparison_html(result: EmbeddingComparisonResult, output_path: str) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig = make_subplots(rows=1, cols=3, subplot_titles=("PCA", "UMAP", "t-SNE"))
    _plotly_scatter(fig, result.pca_embedding, "PCA", 1)
    _plotly_scatter(fig, result.umap_embedding, "UMAP", 2)
    if result.tsne_embedding is not None:
        _plotly_scatter(fig, result.tsne_embedding, "t-SNE", 3)
    fig.update_layout(title="PCA / UMAP / t-SNE", showlegend=False, height=520)
    fig.write_html(path, include_plotlyjs="cdn")
    return str(path)


def _scatter(ax, embedding, title: str) -> None:
    ax.scatter(embedding[:, 0], embedding[:, 1], s=14, alpha=0.75)
    ax.set_title(title)
    ax.set_xlabel(f"{title}-1")
    ax.set_ylabel(f"{title}-2")
    ax.grid(True, alpha=0.25)


def _plotly_scatter(fig: go.Figure, embedding, name: str, col: int) -> None:
    fig.add_trace(
        go.Scatter(
            x=embedding[:, 0],
            y=embedding[:, 1],
            mode="markers",
            marker={"size": 5},
            text=[f"row {index}" for index in range(len(embedding))],
            name=name,
        ),
        row=1,
        col=col,
    )

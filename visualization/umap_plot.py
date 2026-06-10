from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from analysis.umap_analysis import UmapResult


def create_umap_plot(result: UmapResult, output_path: str) -> str:
    """Create a PNG scatter plot for a UMAP result."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 7))
    embedding = result.embedding
    if result.color_values:
        _scatter_by_category(ax, embedding, result.color_values, result.color_column or "category")
    else:
        ax.scatter(embedding[:, 0], embedding[:, 1], s=18, alpha=0.75, color="#4c78a8")

    ax.set_title("UMAP-карта структуры данных")
    ax.set_xlabel("UMAP-1")
    ax.set_ylabel("UMAP-2")
    ax.grid(True, alpha=0.25)
    details = (
        f"Использовано строк: {result.sample_size} из {result.total_rows}\n"
        f"Признаки: {', '.join(result.used_columns[:8])}"
        f"{'...' if len(result.used_columns) > 8 else ''}\n"
        f"Sample: {'да' if result.sampled else 'нет'}"
    )
    fig.text(0.01, 0.01, details, fontsize=8, va="bottom")
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(path)


def _scatter_by_category(ax, embedding: np.ndarray, values: list[object], label: str) -> None:
    categories = sorted(set(values), key=str)
    cmap = plt.get_cmap("tab20")
    for index, category in enumerate(categories):
        mask = np.array([value == category for value in values])
        ax.scatter(
            embedding[mask, 0],
            embedding[mask, 1],
            s=18,
            alpha=0.75,
            color=cmap(index % 20),
            label=str(category),
        )
    ax.legend(title=label, fontsize=8, title_fontsize=8, loc="best")

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

from analysis.ml_preprocessing import prepare_numeric_matrix, sample_for_ml, scale_features, validate_ml_data


@dataclass
class EmbeddingComparisonResult:
    pca_embedding: np.ndarray
    umap_embedding: np.ndarray
    tsne_embedding: np.ndarray | None
    used_columns: list[str]
    sampled: bool
    sample_size: int
    total_rows: int
    explained_variance_ratio: list[float] | None
    message: str
    warnings: list[str]


def build_pca_embedding(x_scaled: np.ndarray) -> tuple[np.ndarray, list[float]]:
    pca = PCA(n_components=2, random_state=42)
    embedding = pca.fit_transform(x_scaled)
    return embedding, [float(value) for value in pca.explained_variance_ratio_]


def build_umap_embedding(x_scaled: np.ndarray) -> np.ndarray:
    try:
        import umap
    except ImportError as exc:
        raise RuntimeError("UMAP не установлен. Установите umap-learn.") from exc
    reducer = umap.UMAP(
        n_neighbors=min(15, len(x_scaled) - 1),
        min_dist=0.1,
        metric="euclidean",
        random_state=42,
    )
    return reducer.fit_transform(x_scaled)


def build_tsne_embedding(x_scaled: np.ndarray) -> np.ndarray:
    perplexity = min(30, max(5, (len(x_scaled) - 1) // 3))
    model = TSNE(
        n_components=2,
        perplexity=perplexity,
        learning_rate="auto",
        init="pca",
        random_state=42,
    )
    return model.fit_transform(x_scaled)


def build_embedding_comparison(df: pd.DataFrame) -> EmbeddingComparisonResult:
    valid, message = validate_ml_data(df)
    if not valid:
        raise ValueError(message)

    prepared, used_columns = prepare_numeric_matrix(df)
    total_rows = len(prepared)
    sampled_data, sampled = sample_for_ml(prepared, max_rows=5000)
    x_scaled = scale_features(sampled_data)

    pca_embedding, ratio = build_pca_embedding(x_scaled)
    umap_embedding = build_umap_embedding(x_scaled)
    warnings: list[str] = []

    tsne_embedding = None
    try:
        tsne_data, _ = sample_for_ml(sampled_data, max_rows=2000)
        tsne_scaled = scale_features(tsne_data)
        tsne_embedding = build_tsne_embedding(tsne_scaled)
    except Exception:
        warnings.append("t-SNE не удалось построить, но PCA и UMAP готовы.")

    return EmbeddingComparisonResult(
        pca_embedding=pca_embedding,
        umap_embedding=umap_embedding,
        tsne_embedding=tsne_embedding,
        used_columns=used_columns,
        sampled=sampled,
        sample_size=len(sampled_data),
        total_rows=total_rows,
        explained_variance_ratio=ratio,
        message="PCA / UMAP / t-SNE сравнение построено.",
        warnings=warnings,
    )


def interpret_embedding_comparison(result: EmbeddingComparisonResult) -> list[str]:
    notes = [
        "PCA показывает линейную структуру данных и долю объясненной дисперсии.",
        "UMAP лучше подсвечивает локальные группы похожих строк.",
        "t-SNE полезен для визуального поиска локальных сегментов, но искажает глобальные расстояния.",
        "Выводы по embeddings стоит трактовать осторожно и проверять бизнес-гипотезами.",
    ]
    if result.explained_variance_ratio:
        total = sum(result.explained_variance_ratio) * 100
        notes.append(f"Первые две PCA-компоненты объясняют примерно {total:.1f}% вариации числовых признаков.")
    notes.extend(result.warnings)
    return notes

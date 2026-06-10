from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


@dataclass
class UmapResult:
    embedding: np.ndarray
    used_columns: list[str]
    sampled: bool
    sample_size: int
    total_rows: int
    message: str
    color_column: str | None = None
    color_values: list[Any] | None = None


def can_build_umap(df: pd.DataFrame) -> tuple[bool, str]:
    """Check whether a dataframe has enough numeric structure for UMAP."""

    if df.empty:
        return False, "UMAP-карта не построена: таблица пустая."
    if len(df) < 10:
        return False, "UMAP-карта не построена: нужно минимум 10 строк."

    prepared, used_columns = prepare_umap_data(df)
    if len(_numeric_non_empty_columns(df)) < 3:
        return False, "UMAP-карта не построена: нужно минимум 3 числовые колонки."
    if prepared.empty:
        return False, "UMAP-карта не построена: после подготовки не осталось данных."
    if len(used_columns) < 3:
        return False, "UMAP-карта не построена: после удаления константных признаков нужно минимум 3 числовые колонки."
    if prepared.isna().any().any():
        return False, "UMAP-карта не построена: после предобработки остались пропуски."
    return True, "UMAP-карта может быть построена."


def prepare_umap_data(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Select numeric features, fill gaps with medians and remove constants."""

    numeric = df.select_dtypes(include="number").copy()
    numeric = numeric.dropna(axis=1, how="all")
    if numeric.empty:
        return numeric, []

    numeric = numeric.apply(pd.to_numeric, errors="coerce")
    medians = numeric.median(numeric_only=True)
    numeric = numeric.fillna(medians).dropna(axis=1, how="any")

    variable_columns = [
        column
        for column in numeric.columns
        if numeric[column].nunique(dropna=True) > 1
    ]
    numeric = numeric[variable_columns]
    return numeric, [str(column) for column in numeric.columns]


def build_umap_embedding(df: pd.DataFrame) -> UmapResult:
    """Build a 2D UMAP embedding for dataframe rows."""

    can_build, message = can_build_umap(df)
    if not can_build:
        raise ValueError(message)

    prepared, used_columns = prepare_umap_data(df)
    total_rows = len(prepared)
    sampled = total_rows > 5000
    if sampled:
        prepared = prepared.sample(n=5000, random_state=42)

    scaled = StandardScaler().fit_transform(prepared)
    if np.isnan(scaled).any():
        raise ValueError("UMAP-карта не построена: после масштабирования появились NaN.")

    try:
        import umap
    except ImportError as exc:
        raise RuntimeError("UMAP-карта не построена: библиотека umap-learn не установлена.") from exc

    n_neighbors = min(15, len(prepared) - 1)
    reducer = umap.UMAP(
        n_neighbors=n_neighbors,
        min_dist=0.1,
        metric="euclidean",
        random_state=42,
    )
    embedding = reducer.fit_transform(scaled)
    color_column, color_values = _detect_color_values(df, prepared.index)
    return UmapResult(
        embedding=embedding,
        used_columns=used_columns,
        sampled=sampled,
        sample_size=len(prepared),
        total_rows=total_rows,
        message="UMAP-карта структуры данных построена.",
        color_column=color_column,
        color_values=color_values,
    )


def interpret_umap_result(result: UmapResult) -> list[str]:
    """Create cautious business-readable comments for a UMAP embedding."""

    embedding = result.embedding
    if len(embedding) < 3:
        return ["На карте слишком мало точек для интерпретации."]

    center = embedding.mean(axis=0)
    distances = np.linalg.norm(embedding - center, axis=1)
    spread = float(np.median(distances))
    high_distance_share = float((distances > distances.mean() + 2 * distances.std()).mean())

    comments: list[str] = []
    if spread < 2:
        comments.append("Точки расположены относительно компактно: данные могут иметь однородную структуру.")
    else:
        comments.append("Точки распределены достаточно широко: возможно, в данных есть разные группы наблюдений.")
    if high_distance_share > 0.03:
        comments.append("Есть удаленные точки: это может указывать на выбросы или редкие случаи.")
    if _looks_grouped(embedding):
        comments.append("На карте видны области сгущения точек: возможно, в данных есть сегменты клиентов, товаров или операций.")
    comments.append("UMAP — метод визуализации, а не строгое доказательство кластеров.")
    return comments


def _numeric_non_empty_columns(df: pd.DataFrame) -> list[str]:
    numeric = df.select_dtypes(include="number").dropna(axis=1, how="all")
    return [str(column) for column in numeric.columns]


def _detect_color_values(df: pd.DataFrame, index: pd.Index) -> tuple[str | None, list[Any] | None]:
    candidates = ("category", "категория", "class", "label", "segment")
    normalized = {str(column).lower(): column for column in df.columns}
    for candidate in candidates:
        for lowered, original in normalized.items():
            if candidate in lowered:
                values = df.loc[index, original]
                if 1 < values.nunique(dropna=True) <= 15:
                    return str(original), values.astype(str).fillna("Нет данных").tolist()
    return None, None


def _looks_grouped(embedding: np.ndarray) -> bool:
    try:
        from sklearn.cluster import KMeans
        from sklearn.metrics import silhouette_score
    except ImportError:
        return False
    if len(embedding) < 20:
        return False
    labels = KMeans(n_clusters=2, n_init=10, random_state=42).fit_predict(embedding)
    return silhouette_score(embedding, labels) > 0.35

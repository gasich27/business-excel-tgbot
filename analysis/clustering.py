from __future__ import annotations

from dataclasses import dataclass
from math import log, sqrt

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, KMeans
from sklearn.metrics import silhouette_score
from sklearn.neighbors import NearestNeighbors

from analysis.embedding_comparison import build_umap_embedding
from analysis.ml_preprocessing import prepare_numeric_matrix, sample_for_ml, scale_features, validate_ml_data


@dataclass
class ClusteringResult:
    method: str
    labels: np.ndarray
    n_clusters: int
    noise_count: int
    silhouette_score: float | None
    used_columns: list[str]
    sampled: bool
    sample_size: int
    total_rows: int
    embedding_2d: np.ndarray | None
    message: str


def run_kmeans(x_scaled: np.ndarray, max_k: int = 8) -> ClusteringResult:
    best_labels = None
    best_score = None
    best_k = 2
    upper = max(2, min(max_k, int(sqrt(len(x_scaled)))))
    for k in range(2, upper + 1):
        labels = KMeans(n_clusters=k, random_state=42, n_init="auto").fit_predict(x_scaled)
        score = _safe_silhouette(x_scaled, labels)
        if score is not None and (best_score is None or score > best_score):
            best_score = score
            best_labels = labels
            best_k = k
    if best_labels is None:
        best_labels = KMeans(n_clusters=2, random_state=42, n_init="auto").fit_predict(x_scaled)
        best_score = _safe_silhouette(x_scaled, best_labels)
    return ClusteringResult("KMeans", best_labels, best_k, 0, best_score, [], False, len(x_scaled), len(x_scaled), None, "KMeans-кластеризация построена.")


def run_dbscan(x_scaled: np.ndarray) -> ClusteringResult:
    min_samples = max(5, int(log(len(x_scaled))))
    neighbors = NearestNeighbors(n_neighbors=min_samples).fit(x_scaled)
    distances, _ = neighbors.kneighbors(x_scaled)
    eps = float(np.percentile(distances[:, -1], 90))
    labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(x_scaled)
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    noise_count = int((labels == -1).sum())
    score = _safe_silhouette(x_scaled, labels)
    return ClusteringResult("DBSCAN", labels, n_clusters, noise_count, score, [], False, len(x_scaled), len(x_scaled), None, "DBSCAN-кластеризация построена.")


def choose_best_clustering(x_scaled: np.ndarray) -> ClusteringResult:
    kmeans = run_kmeans(x_scaled)
    dbscan = run_dbscan(x_scaled)
    noise_share = dbscan.noise_count / max(len(dbscan.labels), 1)
    if dbscan.n_clusters >= 2 and noise_share < 0.4 and (dbscan.silhouette_score or -1) >= (kmeans.silhouette_score or -1):
        return dbscan
    if dbscan.n_clusters < 2 or noise_share >= 0.4:
        kmeans.message = "DBSCAN не нашел устойчивых групп, поэтому использован KMeans."
    return kmeans


def build_clustering_analysis(df: pd.DataFrame, method: str = "auto") -> ClusteringResult:
    valid, message = validate_ml_data(df)
    if not valid:
        raise ValueError(message)
    prepared, used_columns = prepare_numeric_matrix(df)
    total_rows = len(prepared)
    sampled_data, sampled = sample_for_ml(prepared)
    x_scaled = scale_features(sampled_data)
    result = run_kmeans(x_scaled) if method == "kmeans" else run_dbscan(x_scaled) if method == "dbscan" else choose_best_clustering(x_scaled)
    result.used_columns = used_columns
    result.sampled = sampled
    result.sample_size = len(sampled_data)
    result.total_rows = total_rows
    try:
        result.embedding_2d = build_umap_embedding(x_scaled)
    except Exception:
        result.embedding_2d = None
    return result


def interpret_clustering(result: ClusteringResult) -> list[str]:
    notes = [
        f"Метод: {result.method}. Найдено кластеров: {result.n_clusters}.",
        f"Silhouette score: {result.silhouette_score:.2f}." if result.silhouette_score is not None else "Silhouette score не удалось посчитать.",
    ]
    if result.noise_count:
        notes.append(f"Найдено noise/выбросов: {result.noise_count}.")
    notes.append(result.message)
    notes.append("Кластеры стоит трактовать как гипотезы для бизнес-проверки, а не как окончательные сегменты.")
    return notes


def _safe_silhouette(x_scaled: np.ndarray, labels: np.ndarray) -> float | None:
    unique = set(labels)
    if len(unique) < 2 or len(unique) >= len(labels):
        return None
    try:
        return float(silhouette_score(x_scaled, labels))
    except Exception:
        return None

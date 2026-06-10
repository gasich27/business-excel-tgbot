from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class ClusterExplanation:
    cluster_id: int
    size: int
    share_percent: float
    top_features: dict[str, float]
    description: str
    recommendations: list[str]


def explain_clusters(original_df: pd.DataFrame, labels: np.ndarray, used_columns: list[str]) -> list[ClusterExplanation]:
    data = original_df.iloc[: len(labels)].copy()
    data["_cluster"] = labels
    numeric = data[used_columns].apply(pd.to_numeric, errors="coerce")
    global_mean = numeric.mean()
    explanations: list[ClusterExplanation] = []
    total = len(data)

    for cluster_id in sorted(label for label in set(labels) if label != -1):
        cluster_mask = data["_cluster"] == cluster_id
        cluster_numeric = numeric.loc[cluster_mask]
        size = int(cluster_mask.sum())
        share = size / max(total, 1) * 100
        diff = (cluster_numeric.mean() - global_mean).sort_values(key=lambda value: value.abs(), ascending=False)
        top = {str(key): float(value) for key, value in diff.head(5).items()}
        description = _description(cluster_id, size, share, top)
        recommendations = _recommendations(share, top)
        explanations.append(ClusterExplanation(cluster_id, size, share, top, description, recommendations))
    return explanations


def _description(cluster_id: int, size: int, share: float, top: dict[str, float]) -> str:
    if not top:
        return f"Кластер {cluster_id}: группа из {size} объектов ({share:.1f}%), без ярко выраженных отличий по числовым признакам."
    lead = next(iter(top))
    direction = "высокими" if top[lead] > 0 else "низкими"
    return f"Кластер {cluster_id}: группа из {size} объектов ({share:.1f}%), похоже, отличается {direction} значениями по признаку {lead}."


def _recommendations(share: float, top: dict[str, float]) -> list[str]:
    recs = ["Проверьте этот сегмент на бизнес-смысл перед принятием решений."]
    lowered = {key.lower(): value for key, value in top.items()}
    if any("revenue" in key or "выруч" in key for key in lowered):
        recs.append("Если выручка выше среднего, сегмент можно рассматривать как приоритетный.")
    if share < 5:
        recs.append("Небольшой и сильно отличающийся сегмент может быть нишевым или аномальным.")
    if any(("quantity" in key or "колич" in key) and value < 0 for key, value in lowered.items()):
        recs.append("Проверьте причины низкой активности сегмента.")
    return recs

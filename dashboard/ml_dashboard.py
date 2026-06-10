from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from analysis.cluster_explanation import ClusterExplanation
from analysis.clustering import ClusteringResult
from analysis.embedding_comparison import EmbeddingComparisonResult


def generate_ml_dashboard(
    df: pd.DataFrame,
    embedding_result: EmbeddingComparisonResult,
    clustering_result: ClusteringResult,
    explanations: list[ClusterExplanation],
    output_path: str,
) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    embeddings_html = _embedding_figure(embedding_result).to_html(full_html=False, include_plotlyjs="cdn")
    clusters_html = _cluster_figure(clustering_result).to_html(full_html=False, include_plotlyjs=False)
    explanation_html = "".join(
        f"<section><h3>Кластер {item.cluster_id}</h3><p>{item.description}</p>"
        f"<p>Размер: {item.size} ({item.share_percent:.1f}%)</p>"
        f"<pre>{item.top_features}</pre><ul>{''.join(f'<li>{rec}</li>' for rec in item.recommendations)}</ul></section>"
        for item in explanations
    )
    html = f"""
<!doctype html>
<html lang="ru">
<head><meta charset="utf-8"><title>ML-анализ структуры данных</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 28px; background: #f8fafc; color: #172033; }}
.kpi {{ display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; margin-bottom: 22px; }}
.card {{ background: white; padding: 14px; border: 1px solid #d8dee9; border-radius: 8px; }}
section {{ background: white; padding: 18px; border: 1px solid #d8dee9; border-radius: 8px; margin: 18px 0; }}
table {{ border-collapse: collapse; width: 100%; }} td, th {{ border: 1px solid #d8dee9; padding: 6px; }}
</style></head>
<body>
<h1>ML-анализ структуры данных</h1>
<div class="kpi">
<div class="card"><b>Строк</b><br>{len(df)}</div>
<div class="card"><b>Признаков</b><br>{len(embedding_result.used_columns)}</div>
<div class="card"><b>Кластеров</b><br>{clustering_result.n_clusters}</div>
<div class="card"><b>Silhouette</b><br>{clustering_result.silhouette_score}</div>
<div class="card"><b>Noise</b><br>{clustering_result.noise_count}</div>
<div class="card"><b>Sample</b><br>{'да' if embedding_result.sampled or clustering_result.sampled else 'нет'}</div>
</div>
<section><h2>PCA / UMAP / t-SNE</h2>{embeddings_html}
<p>PCA показывает линейную структуру, UMAP и t-SNE помогают увидеть локальные группы. Выводы нужно проверять бизнес-контекстом.</p></section>
<section><h2>Clustering</h2>{clusters_html}</section>
<section><h2>Cluster Explanation</h2>{explanation_html or '<p>Нет кластеров для объяснения.</p>'}</section>
<section><h2>Data Preview</h2><p>Использованные признаки: {', '.join(embedding_result.used_columns)}</p>{df.head(20).to_html(index=False)}</section>
</body></html>
"""
    path.write_text(html, encoding="utf-8")
    return str(path)


def _embedding_figure(result: EmbeddingComparisonResult) -> go.Figure:
    fig = make_subplots(rows=1, cols=3, subplot_titles=("PCA", "UMAP", "t-SNE"))
    _add_scatter(fig, result.pca_embedding, "PCA", 1)
    _add_scatter(fig, result.umap_embedding, "UMAP", 2)
    if result.tsne_embedding is not None:
        _add_scatter(fig, result.tsne_embedding, "t-SNE", 3)
    fig.update_layout(height=480, showlegend=False)
    return fig


def _cluster_figure(result: ClusteringResult) -> go.Figure:
    embedding = result.embedding_2d
    if embedding is None:
        embedding = result.labels.reshape(-1, 1).repeat(2, axis=1)
    fig = go.Figure(
        go.Scatter(
            x=embedding[:, 0],
            y=embedding[:, 1],
            mode="markers",
            marker={"color": result.labels, "colorscale": "Viridis", "size": 6},
            text=[f"cluster {label}" for label in result.labels],
        )
    )
    fig.update_layout(title=f"Кластеризация: {result.method}", height=520)
    return fig


def _add_scatter(fig: go.Figure, embedding, name: str, col: int) -> None:
    fig.add_trace(go.Scatter(x=embedding[:, 0], y=embedding[:, 1], mode="markers", marker={"size": 5}, name=name), row=1, col=col)

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("pptx")

from analysis.cluster_explanation import ClusterExplanation
from analysis.clustering import ClusteringResult
from analysis.embedding_comparison import EmbeddingComparisonResult
from dashboard.ml_dashboard import generate_ml_dashboard
from reports.pptx_generator import generate_ml_pptx_report


def _objects():
    df = pd.DataFrame({"a": range(12), "b": range(12, 24), "c": range(24, 36)})
    embedding = EmbeddingComparisonResult(
        pca_embedding=np.column_stack([range(12), range(12)]),
        umap_embedding=np.column_stack([range(12), range(12)]),
        tsne_embedding=np.column_stack([range(12), range(12)]),
        used_columns=["a", "b", "c"],
        sampled=False,
        sample_size=12,
        total_rows=12,
        explained_variance_ratio=[0.7, 0.2],
        message="ok",
        warnings=[],
    )
    clustering = ClusteringResult(
        method="KMeans",
        labels=np.array([0] * 6 + [1] * 6),
        n_clusters=2,
        noise_count=0,
        silhouette_score=0.5,
        used_columns=["a", "b", "c"],
        sampled=False,
        sample_size=12,
        total_rows=12,
        embedding_2d=np.column_stack([range(12), range(12)]),
        message="ok",
    )
    explanations = [
        ClusterExplanation(0, 6, 50.0, {"a": -1.0}, "Cluster 0", ["Check cluster 0"]),
        ClusterExplanation(1, 6, 50.0, {"a": 1.0}, "Cluster 1", ["Check cluster 1"]),
    ]
    return df, embedding, clustering, explanations


def test_html_dashboard_is_created(tmp_path):
    df, embedding, clustering, explanations = _objects()
    path = generate_ml_dashboard(df, embedding, clustering, explanations, str(tmp_path / "dashboard.html"))

    assert path.endswith(".html")
    assert "ML" in (tmp_path / "dashboard.html").read_text(encoding="utf-8")


def test_powerpoint_report_is_created(tmp_path):
    df, embedding, clustering, explanations = _objects()
    path = generate_ml_pptx_report(
        df,
        embedding,
        clustering,
        explanations,
        {},
        str(tmp_path / "report.pptx"),
    )

    assert path.endswith(".pptx")
    assert (tmp_path / "report.pptx").exists()

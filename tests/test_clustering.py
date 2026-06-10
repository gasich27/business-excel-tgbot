import numpy as np
import pandas as pd

from analysis import clustering as module


def _cluster_df() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    left = rng.normal(loc=0, scale=0.2, size=(20, 3))
    right = rng.normal(loc=5, scale=0.2, size=(20, 3))
    values = np.vstack([left, right])
    return pd.DataFrame(values, columns=["a", "b", "c"])


def test_kmeans_selects_at_least_two_clusters():
    x = np.vstack([np.zeros((10, 3)), np.ones((10, 3)) * 5])
    result = module.run_kmeans(x)

    assert result.method == "KMeans"
    assert result.n_clusters >= 2
    assert len(result.labels) == 20


def test_dbscan_does_not_crash_on_regular_data():
    x = _cluster_df().to_numpy()
    result = module.run_dbscan(x)

    assert result.method == "DBSCAN"
    assert len(result.labels) == len(x)


def test_build_clustering_analysis_adds_umap_embedding(monkeypatch):
    monkeypatch.setattr(module, "build_umap_embedding", lambda x: x[:, :2])

    result = module.build_clustering_analysis(_cluster_df())

    assert result.labels.shape[0] == 40
    assert result.embedding_2d is not None
    assert result.embedding_2d.shape == (40, 2)
    assert result.used_columns == ["a", "b", "c"]

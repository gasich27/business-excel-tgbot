import numpy as np
import pandas as pd

from analysis import embedding_comparison as module


def _df(rows: int = 30) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "a": np.arange(rows),
            "b": np.arange(rows) * 2,
            "c": np.sin(np.arange(rows)),
            "name": ["item"] * rows,
        }
    )


def test_pca_embedding_returns_two_dimensions():
    x = np.random.default_rng(42).normal(size=(20, 4))
    embedding, ratio = module.build_pca_embedding(x)

    assert embedding.shape == (20, 2)
    assert len(ratio) == 2


def test_embedding_comparison_builds_all_embeddings(monkeypatch):
    monkeypatch.setattr(module, "build_umap_embedding", lambda x: x[:, :2])
    monkeypatch.setattr(module, "build_tsne_embedding", lambda x: x[:, :2] * 0.5)

    result = module.build_embedding_comparison(_df())

    assert result.pca_embedding.shape == (30, 2)
    assert result.umap_embedding.shape == (30, 2)
    assert result.tsne_embedding is not None
    assert result.tsne_embedding.shape == (30, 2)
    assert result.used_columns == ["a", "b", "c"]


def test_embedding_comparison_returns_warning_when_tsne_fails(monkeypatch):
    monkeypatch.setattr(module, "build_umap_embedding", lambda x: x[:, :2])
    monkeypatch.setattr(module, "build_tsne_embedding", lambda x: (_ for _ in ()).throw(RuntimeError("slow")))

    result = module.build_embedding_comparison(_df())

    assert result.tsne_embedding is None
    assert result.warnings

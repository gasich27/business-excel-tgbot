from __future__ import annotations

import sys
import types

import numpy as np
import pandas as pd
import pytest

from analysis.umap_analysis import UmapResult, build_umap_embedding, can_build_umap, prepare_umap_data


class FakeUMAP:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def fit_transform(self, values):
        first = values[:, 0]
        second = values[:, 1] if values.shape[1] > 1 else values[:, 0]
        return np.column_stack([first, second])


@pytest.fixture(autouse=True)
def fake_umap(monkeypatch):
    module = types.SimpleNamespace(UMAP=FakeUMAP)
    monkeypatch.setitem(sys.modules, "umap", module)


def _normal_df(rows: int = 30) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "a": np.arange(rows, dtype=float),
            "b": np.arange(rows, dtype=float) * 2,
            "c": np.sin(np.arange(rows, dtype=float)),
            "category": ["A", "B", "C"] * (rows // 3) + ["A"] * (rows % 3),
        }
    )


def test_umap_builds_on_normal_dataframe() -> None:
    result = build_umap_embedding(_normal_df())
    assert isinstance(result, UmapResult)
    assert result.embedding.shape == (30, 2)
    assert result.used_columns == ["a", "b", "c"]


def test_umap_rejects_two_numeric_columns() -> None:
    df = _normal_df()[["a", "b", "category"]]
    can_build, message = can_build_umap(df)
    assert not can_build
    assert "минимум 3 числовые колонки" in message


def test_umap_rejects_too_few_rows() -> None:
    can_build, message = can_build_umap(_normal_df(5))
    assert not can_build
    assert "минимум 10 строк" in message


def test_missing_values_are_filled_with_median() -> None:
    df = _normal_df()
    df.loc[0, "a"] = np.nan
    prepared, columns = prepare_umap_data(df)
    assert columns == ["a", "b", "c"]
    assert not prepared.isna().any().any()
    assert prepared.loc[0, "a"] == pytest.approx(df["a"].median())


def test_constant_features_are_removed() -> None:
    df = _normal_df()
    df["constant"] = 1
    prepared, columns = prepare_umap_data(df)
    assert "constant" not in columns
    assert "constant" not in prepared.columns


def test_large_dataframe_uses_sample() -> None:
    result = build_umap_embedding(_normal_df(5100))
    assert result.sampled
    assert result.sample_size == 5000
    assert result.total_rows == 5100


def test_umap_result_contains_expected_fields() -> None:
    result = build_umap_embedding(_normal_df())
    assert result.message
    assert result.color_column == "category"
    assert result.color_values is not None
    assert len(result.color_values) == result.sample_size

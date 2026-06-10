import numpy as np
import pandas as pd

from analysis.ml_preprocessing import prepare_numeric_matrix, sample_for_ml, scale_features, validate_ml_data


def test_prepare_numeric_matrix_drops_empty_and_constant_columns():
    df = pd.DataFrame(
        {
            "a": range(12),
            "b": [1] * 12,
            "c": [np.nan] * 12,
            "d": [1, 2, np.nan, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            "label": ["x"] * 12,
        }
    )

    prepared, columns = prepare_numeric_matrix(df)

    assert columns == ["a", "d"]
    assert not prepared.isna().any().any()


def test_validate_ml_data_requires_three_numeric_features_and_ten_rows():
    too_small = pd.DataFrame({"a": [1, 2], "b": [2, 3], "c": [3, 4]})
    valid, _ = validate_ml_data(too_small)
    assert valid is False

    not_enough_features = pd.DataFrame({"a": range(10), "b": range(10)})
    valid, _ = validate_ml_data(not_enough_features)
    assert valid is False


def test_scale_features_and_sampling():
    df = pd.DataFrame({"a": range(6000), "b": range(1, 6001), "c": range(2, 6002)})
    sampled, was_sampled = sample_for_ml(df, max_rows=5000)
    scaled = scale_features(sampled)

    assert was_sampled is True
    assert sampled.shape[0] == 5000
    assert scaled.shape == (5000, 3)

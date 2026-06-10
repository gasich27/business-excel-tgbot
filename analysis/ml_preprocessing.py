from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


def prepare_numeric_matrix(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Prepare numeric features for ML visualizations and clustering."""

    numeric = df.select_dtypes(include="number").copy()
    numeric = numeric.dropna(axis=1, how="all")
    if numeric.empty:
        return numeric, []

    numeric = numeric.apply(pd.to_numeric, errors="coerce")
    numeric = numeric.fillna(numeric.median(numeric_only=True))
    numeric = numeric.dropna(axis=1, how="any")
    variable_columns = [column for column in numeric.columns if numeric[column].nunique(dropna=True) > 1]
    numeric = numeric[variable_columns]
    return numeric, [str(column) for column in numeric.columns]


def sample_for_ml(df: pd.DataFrame, max_rows: int = 5000) -> tuple[pd.DataFrame, bool]:
    """Sample rows for expensive ML algorithms."""

    if len(df) > max_rows:
        return df.sample(n=max_rows, random_state=42), True
    return df, False


def scale_features(df: pd.DataFrame) -> np.ndarray:
    """Scale numeric features with StandardScaler."""

    values = StandardScaler().fit_transform(df)
    if np.isnan(values).any():
        raise ValueError("После масштабирования появились NaN.")
    return values


def validate_ml_data(df: pd.DataFrame) -> tuple[bool, str]:
    """Validate minimum data requirements for ML analysis."""

    if df.empty:
        return False, "Недостаточно числовых данных для ML-анализа: таблица пустая."
    if len(df) < 10:
        return False, "Недостаточно числовых данных для ML-анализа. Нужно минимум 10 строк."
    prepared, columns = prepare_numeric_matrix(df)
    if len(columns) < 3:
        return False, "Недостаточно числовых данных для ML-анализа. Нужно минимум 3 числовые колонки и 10 строк."
    if prepared.empty:
        return False, "Недостаточно числовых данных для ML-анализа: после подготовки не осталось признаков."
    return True, "Данные подходят для ML-анализа."

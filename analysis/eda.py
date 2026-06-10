from io import StringIO
from pathlib import Path

import pandas as pd
from pandas.api.types import is_datetime64_any_dtype, is_numeric_dtype


def analyze_file(path: Path) -> dict:
    dataframe = _read_table(path)
    if dataframe.empty:
        raise ValueError("The uploaded table is empty.")

    dataframe = _normalize_columns(dataframe)
    dataframe = _coerce_date_columns(dataframe)

    numeric_columns = [column for column in dataframe.columns if is_numeric_dtype(dataframe[column])]
    date_columns = [column for column in dataframe.columns if is_datetime64_any_dtype(dataframe[column])]
    categorical_columns = [
        column
        for column in dataframe.columns
        if column not in numeric_columns and column not in date_columns
    ]

    info_buffer = StringIO()
    dataframe.info(buf=info_buffer)

    missing_by_column = dataframe.isna().sum().sort_values(ascending=False)
    numeric_description = dataframe[numeric_columns].describe().round(2) if numeric_columns else pd.DataFrame()

    return {
        "dataframe": dataframe,
        "rows": int(dataframe.shape[0]),
        "columns": int(dataframe.shape[1]),
        "dtypes": {column: str(dtype) for column, dtype in dataframe.dtypes.items()},
        "info": info_buffer.getvalue(),
        "missing_total": int(dataframe.isna().sum().sum()),
        "missing_by_column": missing_by_column,
        "duplicates": int(dataframe.duplicated().sum()),
        "numeric_columns": numeric_columns,
        "date_columns": date_columns,
        "categorical_columns": categorical_columns,
        "numeric_description": numeric_description,
    }


def _read_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path, sep=None, engine="python")
    if suffix == ".xls":
        return pd.read_excel(path, engine="xlrd")
    return pd.read_excel(path, engine="openpyxl")


def _normalize_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    result = dataframe.copy()
    result.columns = [str(column).strip() or f"column_{index + 1}" for index, column in enumerate(result.columns)]
    return result


def _coerce_date_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    result = dataframe.copy()
    for column in result.columns:
        name = column.lower()
        if "date" in name or "дата" in name or "time" in name:
            converted = pd.to_datetime(result[column], errors="coerce", dayfirst=True)
            if converted.notna().sum() >= max(3, int(len(result) * 0.5)):
                result[column] = converted
    return result

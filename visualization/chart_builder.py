from __future__ import annotations

from pathlib import Path

import pandas as pd

from reports.custom_charts_pdf import build_custom_charts_pdf
from visualization.chart_config import ChartConfig, ChartType, Sorting
from visualization.chart_validation import validate_chart_config
from visualization.custom_charts_matplotlib import create_chart_png


def build_custom_chart(dataframe: pd.DataFrame, config: ChartConfig, output_dir: Path) -> Path:
    """Validate, prepare and render a chart in the requested format."""

    validation = validate_chart_config(dataframe, config)
    if not validation.is_valid:
        raise ValueError("\n".join(validation.errors))

    prepared = prepare_chart_data(dataframe, config)
    if prepared.empty:
        raise ValueError("После подготовки данных таблица для графика оказалась пустой.")

    output_dir.mkdir(parents=True, exist_ok=True)
    chart_path = create_chart_png(prepared, config, output_dir)
    if config.output_format == "pdf":
        return build_custom_charts_pdf([(chart_path, config)], output_dir / f"{chart_path.stem}.pdf")
    return chart_path


def prepare_chart_data(dataframe: pd.DataFrame, config: ChartConfig) -> pd.DataFrame:
    """Prepare dataframe according to the chart type and selected options."""

    data = dataframe.copy()
    data = _coerce_dates(data)

    if config.chart_type == ChartType.HEATMAP:
        return prepare_heatmap_data(data, config)
    if config.chart_type == ChartType.PIE:
        return prepare_pie_data(data, config)
    if config.chart_type in {ChartType.HISTOGRAM, ChartType.SCATTER, ChartType.BOXPLOT}:
        return _drop_required_na(data, config)

    aggregated = aggregate_data(data, config)
    sorted_data = sort_chart_data(aggregated, config)
    return limit_top_n(sorted_data, config)


def aggregate_data(dataframe: pd.DataFrame, config: ChartConfig) -> pd.DataFrame:
    """Group by X and aggregate selected Y columns."""

    if not config.x_column or not config.y_columns:
        return dataframe

    data = dataframe[[config.x_column, *config.y_columns]].copy().dropna(subset=[config.x_column])
    for column in config.y_columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    aggregation = config.aggregation or "sum"
    grouped = data.groupby(config.x_column, dropna=True)[config.y_columns].agg(aggregation).reset_index()
    return grouped.dropna(how="all", subset=config.y_columns)


def sort_chart_data(dataframe: pd.DataFrame, config: ChartConfig) -> pd.DataFrame:
    """Apply requested sorting."""

    if dataframe.empty:
        return dataframe
    if config.sorting == Sorting.X_ASC:
        return dataframe.sort_values(config.x_column)
    if config.sorting == Sorting.ASC and config.y_column:
        return dataframe.sort_values(config.y_column, ascending=True)
    if config.sorting == Sorting.DESC and config.y_column:
        return dataframe.sort_values(config.y_column, ascending=False)
    return dataframe


def limit_top_n(dataframe: pd.DataFrame, config: ChartConfig) -> pd.DataFrame:
    """Limit rows to Top N if selected."""

    if config.top_n and config.top_n > 0:
        return dataframe.head(config.top_n)
    return dataframe


def prepare_pie_data(dataframe: pd.DataFrame, config: ChartConfig) -> pd.DataFrame:
    """Aggregate pie data and group tail values into 'Другое'."""

    aggregated = aggregate_data(dataframe, config)
    if config.y_column:
        aggregated = aggregated.sort_values(config.y_column, ascending=False)

    top_n = config.top_n or 10
    if len(aggregated) <= top_n or not config.y_column:
        return aggregated

    top = aggregated.head(top_n).copy()
    other_value = aggregated.iloc[top_n:][config.y_column].sum()
    other = pd.DataFrame([{config.x_column: "Другое", config.y_column: other_value}])
    return pd.concat([top, other], ignore_index=True)


def prepare_heatmap_data(dataframe: pd.DataFrame, config: ChartConfig) -> pd.DataFrame:
    """Return correlation matrix for numeric columns."""

    excluded = set(config.excluded_columns)
    numeric = dataframe.drop(columns=[column for column in excluded if column in dataframe], errors="ignore")
    numeric = numeric.apply(pd.to_numeric, errors="coerce").select_dtypes(include="number")
    return numeric.corr(numeric_only=True).dropna(how="all").dropna(axis=1, how="all")


def _drop_required_na(dataframe: pd.DataFrame, config: ChartConfig) -> pd.DataFrame:
    columns = list(dict.fromkeys(column for column in [config.x_column, *config.y_columns, config.hue, config.size] if column))
    data = dataframe[columns].copy() if columns else dataframe.copy()
    for column in config.y_columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    if config.x_column and config.chart_type == ChartType.SCATTER:
        data[config.x_column] = pd.to_numeric(data[config.x_column], errors="coerce")
    if config.size:
        data[config.size] = pd.to_numeric(data[config.size], errors="coerce")
    return data.dropna(subset=[column for column in [config.x_column, config.y_column] if column])


def _coerce_dates(dataframe: pd.DataFrame) -> pd.DataFrame:
    result = dataframe.copy()
    for column in result.columns:
        lowered = str(column).lower()
        if "date" in lowered or "дата" in lowered or "time" in lowered:
            converted = pd.to_datetime(result[column], errors="coerce", dayfirst=True)
            if converted.notna().sum() >= max(3, int(len(result) * 0.3)):
                result[column] = converted
    return result

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


plt.rcParams["figure.figsize"] = (10, 6)
plt.rcParams["axes.grid"] = True
plt.rcParams["font.family"] = "DejaVu Sans"


def build_charts(dataframe: pd.DataFrame, analysis: dict, output_dir: Path) -> list[Path]:
    chart_dir = output_dir / "charts"
    chart_dir.mkdir(parents=True, exist_ok=True)

    charts: list[Path] = []
    charts.extend(_numeric_histograms(dataframe, analysis["numeric_columns"], chart_dir))
    charts.extend(_category_charts(dataframe, analysis["categorical_columns"], chart_dir))
    charts.extend(_time_series(dataframe, analysis["date_columns"], analysis["numeric_columns"], chart_dir))
    charts.extend(_correlation_heatmap(dataframe, analysis["numeric_columns"], chart_dir))
    charts.extend(_boxplot(dataframe, analysis["numeric_columns"], chart_dir))
    return charts


def _numeric_histograms(dataframe: pd.DataFrame, numeric_columns: list[str], chart_dir: Path) -> list[Path]:
    charts = []
    for index, column in enumerate(numeric_columns[:4], start=1):
        series = dataframe[column].dropna()
        if series.empty:
            continue
        fig, ax = plt.subplots()
        ax.hist(series, bins=30, color="#386cb0", edgecolor="white")
        ax.set_title(f"Распределение: {column}")
        ax.set_xlabel(column)
        ax.set_ylabel("Количество")
        charts.append(_save(fig, chart_dir / f"hist_{index}_{_safe_name(column)}.png"))
    return charts


def _category_charts(dataframe: pd.DataFrame, categorical_columns: list[str], chart_dir: Path) -> list[Path]:
    charts = []
    for index, column in enumerate(categorical_columns[:3], start=1):
        top_values = dataframe[column].astype(str).value_counts().head(10)
        if top_values.empty:
            continue
        fig, ax = plt.subplots()
        top_values.sort_values().plot(kind="barh", ax=ax, color="#7fc97f")
        ax.set_title(f"Топ-10 значений: {column}")
        ax.set_xlabel("Количество")
        charts.append(_save(fig, chart_dir / f"top_{index}_{_safe_name(column)}.png"))
    return charts


def _time_series(
    dataframe: pd.DataFrame,
    date_columns: list[str],
    numeric_columns: list[str],
    chart_dir: Path,
) -> list[Path]:
    if not date_columns or not numeric_columns:
        return []

    date_column = date_columns[0]
    value_column = _choose_value_column(dataframe, numeric_columns)
    grouped = (
        dataframe[[date_column, value_column]]
        .dropna()
        .set_index(date_column)
        .sort_index()
        .resample("D")[value_column]
        .sum()
    )
    if grouped.empty:
        return []

    fig, ax = plt.subplots()
    grouped.plot(ax=ax, color="#fdc086")
    ax.set_title(f"Динамика по дням: {value_column}")
    ax.set_xlabel("Дата")
    ax.set_ylabel(value_column)
    return [_save(fig, chart_dir / "sales_by_day.png")]


def _correlation_heatmap(dataframe: pd.DataFrame, numeric_columns: list[str], chart_dir: Path) -> list[Path]:
    if len(numeric_columns) < 2:
        return []

    corr = dataframe[numeric_columns].corr(numeric_only=True)
    fig, ax = plt.subplots(figsize=(9, 7))
    image = ax.imshow(corr, cmap="coolwarm", vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr.columns)), corr.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(corr.index)), corr.index)
    ax.set_title("Корреляционная матрица")
    fig.colorbar(image, ax=ax, shrink=0.8)
    return [_save(fig, chart_dir / "correlation_heatmap.png")]


def _boxplot(dataframe: pd.DataFrame, numeric_columns: list[str], chart_dir: Path) -> list[Path]:
    if not numeric_columns:
        return []

    fig, ax = plt.subplots()
    dataframe[numeric_columns[:8]].plot(kind="box", ax=ax)
    ax.set_title("Boxplot числовых признаков")
    ax.tick_params(axis="x", rotation=45)
    return [_save(fig, chart_dir / "numeric_boxplot.png")]


def _choose_value_column(dataframe: pd.DataFrame, numeric_columns: list[str]) -> str:
    preferred_names = ("выруч", "revenue", "sales", "сумм", "amount", "price")
    for column in numeric_columns:
        lowered = column.lower()
        if any(name in lowered for name in preferred_names):
            return column
    return numeric_columns[0]


def _save(fig: plt.Figure, path: Path) -> Path:
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def _safe_name(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value).strip("_").lower()[:40] or "column"

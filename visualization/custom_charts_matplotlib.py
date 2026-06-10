from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from visualization.chart_config import CHART_TYPE_TITLES, ChartConfig, ChartType


plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["axes.grid"] = True


def create_chart_png(dataframe: pd.DataFrame, config: ChartConfig, output_dir: Path) -> Path:
    """Dispatch PNG chart rendering by chart type."""

    dispatch = {
        ChartType.LINE.value: create_line_chart,
        ChartType.BAR.value: create_bar_chart,
        ChartType.HORIZONTAL_BAR.value: create_horizontal_bar_chart,
        ChartType.HISTOGRAM.value: create_histogram,
        ChartType.PIE.value: create_pie_chart,
        ChartType.SCATTER.value: create_scatter_plot,
        ChartType.BOXPLOT.value: create_boxplot,
        ChartType.HEATMAP.value: create_heatmap,
        ChartType.AREA.value: create_area_chart,
        ChartType.MULTI.value: create_multi_line_chart,
        ChartType.COMBO.value: create_combo_chart,
    }
    return dispatch[config.chart_type](dataframe, config, output_dir)


def create_line_chart(dataframe: pd.DataFrame, config: ChartConfig, output_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(11, 6))
    for column in config.y_columns:
        ax.plot(dataframe[config.x_column], dataframe[column], marker="o", label=column)
    _finish_axes(ax, config, ylabel=", ".join(config.y_columns))
    ax.legend()
    return _save(fig, output_dir / "custom_line.png")


def create_bar_chart(dataframe: pd.DataFrame, config: ChartConfig, output_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(11, 6))
    dataframe.plot(kind="bar", x=config.x_column, y=config.y_columns, ax=ax)
    _finish_axes(ax, config, ylabel=", ".join(config.y_columns))
    return _save(fig, output_dir / "custom_bar.png")


def create_horizontal_bar_chart(dataframe: pd.DataFrame, config: ChartConfig, output_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(11, 7))
    dataframe.plot(kind="barh", x=config.x_column, y=config.y_columns, ax=ax)
    _finish_axes(ax, config, xlabel=", ".join(config.y_columns), ylabel=config.x_column)
    return _save(fig, output_dir / "custom_horizontal_bar.png")


def create_histogram(dataframe: pd.DataFrame, config: ChartConfig, output_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(dataframe[config.y_column].dropna(), bins=config.bins or 30, color="#4c78a8", edgecolor="white")
    _finish_axes(ax, config, xlabel=config.y_column, ylabel="Количество")
    return _save(fig, output_dir / "custom_histogram.png")


def create_pie_chart(dataframe: pd.DataFrame, config: ChartConfig, output_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(9, 9))
    ax.pie(dataframe[config.y_column], labels=dataframe[config.x_column].astype(str), autopct="%1.1f%%", startangle=90)
    ax.set_title(_title(config))
    return _save(fig, output_dir / "custom_pie.png")


def create_scatter_plot(dataframe: pd.DataFrame, config: ChartConfig, output_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(10, 6))
    if config.hue and config.hue in dataframe:
        for name, group in dataframe.groupby(config.hue):
            ax.scatter(group[config.x_column], group[config.y_column], label=str(name), alpha=0.75)
        ax.legend()
    else:
        sizes = dataframe[config.size] if config.size and config.size in dataframe else None
        ax.scatter(dataframe[config.x_column], dataframe[config.y_column], s=sizes, alpha=0.75, color="#4c78a8")
    _finish_axes(ax, config, xlabel=config.x_column, ylabel=config.y_column)
    return _save(fig, output_dir / "custom_scatter.png")


def create_boxplot(dataframe: pd.DataFrame, config: ChartConfig, output_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(10, 6))
    if config.x_column and config.x_column in dataframe and config.x_column != config.y_column:
        dataframe.boxplot(column=config.y_column, by=config.x_column, ax=ax, rot=45)
        fig.suptitle("")
    else:
        dataframe[[config.y_column]].plot(kind="box", ax=ax)
    _finish_axes(ax, config, ylabel=config.y_column)
    return _save(fig, output_dir / "custom_boxplot.png")


def create_heatmap(dataframe: pd.DataFrame, config: ChartConfig, output_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(10, 8))
    image = ax.imshow(dataframe, cmap="coolwarm", vmin=-1, vmax=1)
    ax.set_xticks(range(len(dataframe.columns)), dataframe.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(dataframe.index)), dataframe.index)
    ax.set_title(_title(config))
    fig.colorbar(image, ax=ax, shrink=0.8)
    return _save(fig, output_dir / "custom_heatmap.png")


def create_area_chart(dataframe: pd.DataFrame, config: ChartConfig, output_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.stackplot(dataframe[config.x_column], *[dataframe[column] for column in config.y_columns], labels=config.y_columns, alpha=0.75)
    _finish_axes(ax, config, ylabel=", ".join(config.y_columns))
    ax.legend()
    return _save(fig, output_dir / "custom_area.png")


def create_multi_line_chart(dataframe: pd.DataFrame, config: ChartConfig, output_dir: Path) -> Path:
    return create_line_chart(dataframe, config, output_dir)


def create_combo_chart(dataframe: pd.DataFrame, config: ChartConfig, output_dir: Path) -> Path:
    fig, ax1 = plt.subplots(figsize=(11, 6))
    y1 = config.y_columns[0]
    y2 = config.y_columns[1] if len(config.y_columns) > 1 else config.y_columns[0]
    _draw_combo_series(ax1, dataframe, config.x_column, y1, config.y1_chart_type or "bar", "#4c78a8", label=y1)
    ax1.set_ylabel(y1)
    target_axis = ax1.twinx() if config.use_secondary_y else ax1
    _draw_combo_series(target_axis, dataframe, config.x_column, y2, config.y2_chart_type or "line", "#f58518", label=y2)
    target_axis.set_ylabel(y2)
    ax1.set_title(_title(config))
    ax1.tick_params(axis="x", rotation=45)
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = target_axis.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2)
    return _save(fig, output_dir / "custom_combo.png")


def _draw_combo_series(ax, dataframe: pd.DataFrame, x_column: str, y_column: str, chart_type: str, color: str, label: str) -> None:
    if chart_type == "line":
        ax.plot(dataframe[x_column], dataframe[y_column], marker="o", color=color, label=label)
    else:
        ax.bar(dataframe[x_column], dataframe[y_column], color=color, alpha=0.65, label=label)


def _finish_axes(ax, config: ChartConfig, xlabel: str | None = None, ylabel: str | None = None) -> None:
    ax.set_title(_title(config))
    ax.set_xlabel(xlabel or config.x_column or "")
    ax.set_ylabel(ylabel or "")
    ax.tick_params(axis="x", rotation=45)


def _title(config: ChartConfig) -> str:
    return config.title or CHART_TYPE_TITLES.get(config.chart_type, "График")


def _save(fig: plt.Figure, path: Path) -> Path:
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from visualization.chart_config import CHART_TYPE_TITLES, ChartConfig, ChartType


def create_chart_html(dataframe: pd.DataFrame, config: ChartConfig, output_dir: Path) -> Path:
    """Dispatch HTML chart rendering by chart type."""

    dispatch = {
        ChartType.LINE.value: create_line_chart_html,
        ChartType.BAR.value: create_bar_chart_html,
        ChartType.HORIZONTAL_BAR.value: create_horizontal_bar_chart_html,
        ChartType.HISTOGRAM.value: create_histogram_html,
        ChartType.PIE.value: create_pie_chart_html,
        ChartType.SCATTER.value: create_scatter_plot_html,
        ChartType.BOXPLOT.value: create_boxplot_html,
        ChartType.HEATMAP.value: create_heatmap_html,
        ChartType.AREA.value: create_area_chart_html,
        ChartType.MULTI.value: create_multi_line_chart_html,
        ChartType.COMBO.value: create_combo_chart_html,
    }
    return dispatch[config.chart_type](dataframe, config, output_dir)


def create_line_chart_html(dataframe: pd.DataFrame, config: ChartConfig, output_dir: Path) -> Path:
    fig = px.line(dataframe, x=config.x_column, y=config.y_columns, markers=True, title=_title(config))
    return _save(fig, output_dir / "custom_line.html")


def create_bar_chart_html(dataframe: pd.DataFrame, config: ChartConfig, output_dir: Path) -> Path:
    fig = px.bar(dataframe, x=config.x_column, y=config.y_columns, title=_title(config))
    return _save(fig, output_dir / "custom_bar.html")


def create_horizontal_bar_chart_html(dataframe: pd.DataFrame, config: ChartConfig, output_dir: Path) -> Path:
    fig = px.bar(dataframe, x=config.y_columns, y=config.x_column, orientation="h", title=_title(config))
    return _save(fig, output_dir / "custom_horizontal_bar.html")


def create_histogram_html(dataframe: pd.DataFrame, config: ChartConfig, output_dir: Path) -> Path:
    fig = px.histogram(dataframe, x=config.y_column, nbins=config.bins or 30, title=_title(config))
    return _save(fig, output_dir / "custom_histogram.html")


def create_pie_chart_html(dataframe: pd.DataFrame, config: ChartConfig, output_dir: Path) -> Path:
    fig = px.pie(dataframe, names=config.x_column, values=config.y_column, title=_title(config))
    return _save(fig, output_dir / "custom_pie.html")


def create_scatter_plot_html(dataframe: pd.DataFrame, config: ChartConfig, output_dir: Path) -> Path:
    fig = px.scatter(dataframe, x=config.x_column, y=config.y_column, color=config.hue, size=config.size, title=_title(config))
    return _save(fig, output_dir / "custom_scatter.html")


def create_boxplot_html(dataframe: pd.DataFrame, config: ChartConfig, output_dir: Path) -> Path:
    fig = px.box(dataframe, x=config.x_column if config.x_column != config.y_column else None, y=config.y_column, title=_title(config))
    return _save(fig, output_dir / "custom_boxplot.html")


def create_heatmap_html(dataframe: pd.DataFrame, config: ChartConfig, output_dir: Path) -> Path:
    fig = px.imshow(dataframe, text_auto=".2f", color_continuous_scale="RdBu_r", zmin=-1, zmax=1, title=_title(config))
    return _save(fig, output_dir / "custom_heatmap.html")


def create_area_chart_html(dataframe: pd.DataFrame, config: ChartConfig, output_dir: Path) -> Path:
    fig = px.area(dataframe, x=config.x_column, y=config.y_columns, title=_title(config))
    return _save(fig, output_dir / "custom_area.html")


def create_multi_line_chart_html(dataframe: pd.DataFrame, config: ChartConfig, output_dir: Path) -> Path:
    return create_line_chart_html(dataframe, config, output_dir)


def create_combo_chart_html(dataframe: pd.DataFrame, config: ChartConfig, output_dir: Path) -> Path:
    fig = go.Figure()
    y1 = config.y_columns[0]
    y2 = config.y_columns[1] if len(config.y_columns) > 1 else config.y_columns[0]
    _add_combo_trace(fig, dataframe, config.x_column, y1, config.y1_chart_type or "bar", "y", y1)
    _add_combo_trace(fig, dataframe, config.x_column, y2, config.y2_chart_type or "line", "y2" if config.use_secondary_y else "y", y2)
    fig.update_layout(title=_title(config), xaxis_title=config.x_column, yaxis_title=y1)
    if config.use_secondary_y:
        fig.update_layout(yaxis2={"title": y2, "overlaying": "y", "side": "right"})
    return _save(fig, output_dir / "custom_combo.html")


def _add_combo_trace(fig: go.Figure, dataframe: pd.DataFrame, x_column: str, y_column: str, chart_type: str, axis: str, name: str) -> None:
    if chart_type == "line":
        fig.add_trace(go.Scatter(x=dataframe[x_column], y=dataframe[y_column], mode="lines+markers", name=name, yaxis=axis))
    else:
        fig.add_trace(go.Bar(x=dataframe[x_column], y=dataframe[y_column], name=name, yaxis=axis, opacity=0.7))


def _title(config: ChartConfig) -> str:
    return config.title or CHART_TYPE_TITLES.get(config.chart_type, "График")


def _save(fig: go.Figure, path: Path) -> Path:
    fig.write_html(path, include_plotlyjs="cdn")
    return path

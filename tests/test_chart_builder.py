from pathlib import Path

import pandas as pd
import pytest

from visualization.chart_builder import aggregate_data, build_custom_chart, prepare_heatmap_data, prepare_pie_data
from visualization.chart_config import ChartConfig
from visualization.chart_validation import validate_chart_config


@pytest.fixture()
def sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=8, freq="D"),
            "category": ["A", "A", "B", "B", "C", "C", "D", "D"],
            "product": ["p1", "p2", "p1", "p3", "p2", "p4", "p1", "p5"],
            "revenue": [100, 150, 200, 50, 80, 60, 300, 20],
            "quantity": [1, 2, 4, 1, 1, 2, 3, 1],
            "price": [100, 75, 50, 50, 80, 30, 100, 20],
        }
    )


def test_chart_config_defaults() -> None:
    config = ChartConfig(chart_type="line")
    assert config.output_format == "png"
    assert config.y_columns == []
    assert config.y_column is None


def test_validation_rejects_wrong_column(sample_df: pd.DataFrame) -> None:
    config = ChartConfig(chart_type="bar", x_column="missing", y_columns=["revenue"], aggregation="sum")
    result = validate_chart_config(sample_df, config)
    assert not result.is_valid
    assert "не найдена" in "\n".join(result.errors)


def test_validation_rejects_empty_dataframe() -> None:
    config = ChartConfig(chart_type="line", x_column="date", y_columns=["revenue"])
    result = validate_chart_config(pd.DataFrame(), config)
    assert not result.is_valid


def test_aggregate_data_sum(sample_df: pd.DataFrame) -> None:
    config = ChartConfig(chart_type="bar", x_column="category", y_columns=["revenue"], aggregation="sum")
    result = aggregate_data(sample_df, config)
    assert result.loc[result["category"] == "A", "revenue"].iloc[0] == 250


def test_line_chart_png(sample_df: pd.DataFrame, tmp_path: Path) -> None:
    config = ChartConfig(chart_type="line", x_column="date", y_columns=["revenue"], aggregation="sum")
    output = build_custom_chart(sample_df, config, tmp_path)
    assert output.exists()
    assert output.suffix == ".png"


def test_bar_chart_png(sample_df: pd.DataFrame, tmp_path: Path) -> None:
    config = ChartConfig(chart_type="bar", x_column="category", y_columns=["revenue"], aggregation="sum", top_n=3)
    output = build_custom_chart(sample_df, config, tmp_path)
    assert output.exists()
    assert output.name == "custom_bar.png"


def test_line_chart_pdf(sample_df: pd.DataFrame, tmp_path: Path) -> None:
    config = ChartConfig(
        chart_type="line",
        x_column="date",
        y_columns=["revenue"],
        aggregation="sum",
        output_format="pdf",
    )
    output = build_custom_chart(sample_df, config, tmp_path)
    assert output.exists()
    assert output.suffix == ".pdf"


def test_pie_chart_groups_other(sample_df: pd.DataFrame) -> None:
    config = ChartConfig(chart_type="pie", x_column="product", y_columns=["revenue"], aggregation="sum", top_n=2)
    result = prepare_pie_data(sample_df, config)
    assert "Другое" in result["product"].tolist()


def test_heatmap_requires_two_numeric_columns(sample_df: pd.DataFrame) -> None:
    config = ChartConfig(chart_type="heatmap", excluded_columns=["quantity", "price"])
    result = prepare_heatmap_data(sample_df, config)
    assert "revenue" in result.columns


def test_heatmap_png(sample_df: pd.DataFrame, tmp_path: Path) -> None:
    config = ChartConfig(chart_type="heatmap")
    output = build_custom_chart(sample_df, config, tmp_path)
    assert output.exists()
    assert output.name == "custom_heatmap.png"

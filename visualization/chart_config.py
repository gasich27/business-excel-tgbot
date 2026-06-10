from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ChartType(StrEnum):
    LINE = "line"
    BAR = "bar"
    HORIZONTAL_BAR = "horizontal_bar"
    HISTOGRAM = "histogram"
    PIE = "pie"
    SCATTER = "scatter"
    BOXPLOT = "boxplot"
    HEATMAP = "heatmap"
    AREA = "area"
    MULTI = "multi"
    COMBO = "combo"


class Aggregation(StrEnum):
    SUM = "sum"
    MEAN = "mean"
    MEDIAN = "median"
    COUNT = "count"
    MIN = "min"
    MAX = "max"


class Sorting(StrEnum):
    NONE = "none"
    ASC = "asc"
    DESC = "desc"
    X_ASC = "x_asc"


class OutputFormat(StrEnum):
    PNG = "png"
    PDF = "pdf"


@dataclass
class ChartConfig:
    """User-selected parameters for building a custom chart."""

    chart_type: str
    x_column: str | None = None
    y_columns: list[str] = field(default_factory=list)
    aggregation: str | None = None
    sorting: str | None = None
    top_n: int | None = None
    bins: int | None = None
    hue: str | None = None
    size: str | None = None
    output_format: str = "png"
    use_secondary_y: bool = False
    title: str | None = None
    y1_chart_type: str | None = None
    y2_chart_type: str | None = None
    excluded_columns: list[str] = field(default_factory=list)

    @property
    def y_column(self) -> str | None:
        return self.y_columns[0] if self.y_columns else None


CHART_TYPE_TITLES: dict[str, str] = {
    ChartType.LINE.value: "\u041b\u0438\u043d\u0435\u0439\u043d\u044b\u0439",
    ChartType.BAR.value: "\u0421\u0442\u043e\u043b\u0431\u0447\u0430\u0442\u044b\u0439",
    ChartType.HORIZONTAL_BAR.value: "\u0413\u043e\u0440\u0438\u0437\u043e\u043d\u0442\u0430\u043b\u044c\u043d\u044b\u0439 bar",
    ChartType.HISTOGRAM.value: "\u0413\u0438\u0441\u0442\u043e\u0433\u0440\u0430\u043c\u043c\u0430",
    ChartType.PIE.value: "\u041a\u0440\u0443\u0433\u043e\u0432\u0430\u044f",
    ChartType.SCATTER.value: "Scatter",
    ChartType.BOXPLOT.value: "Boxplot",
    ChartType.HEATMAP.value: "Heatmap",
    ChartType.AREA.value: "Area",
    ChartType.MULTI.value: "\u041c\u0443\u043b\u044c\u0442\u0438\u0433\u0440\u0430\u0444\u0438\u043a",
    ChartType.COMBO.value: "\u041a\u043e\u043c\u0431\u043e-\u0433\u0440\u0430\u0444\u0438\u043a",
}

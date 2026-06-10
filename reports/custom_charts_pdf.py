from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer

from reports.pdf_generator import _register_font, _styles, _table
from visualization.chart_config import ChartConfig


def build_custom_charts_pdf(items: list[tuple[Path, ChartConfig]], output_path: Path) -> Path:
    """Build a PDF report from user-selected PNG charts."""

    font_name = _register_font()
    styles = _styles(font_name)
    doc = SimpleDocTemplate(str(output_path), pagesize=A4)
    story = [Paragraph("Пользовательские графики", styles["Title"]), Spacer(1, 0.6 * cm)]

    for index, (chart_path, config) in enumerate(items, start=1):
        story.append(Paragraph(f"График {index}: {config.title or config.chart_type}", styles["Heading2"]))
        story.append(
            _table(
                [
                    ["Тип", config.chart_type],
                    ["X", config.x_column or "-"],
                    ["Y", ", ".join(config.y_columns) or "-"],
                    ["Агрегация", config.aggregation or "-"],
                    ["Сортировка", config.sorting or "-"],
                    ["Top N", config.top_n or "-"],
                ],
                font_name,
            )
        )
        story.append(Spacer(1, 0.4 * cm))
        if chart_path.suffix.lower() == ".png":
            story.append(Image(str(chart_path), width=16 * cm, height=9.5 * cm, kind="proportional"))
        else:
            story.append(Paragraph(f"Файл графика приложен отдельно: {chart_path.name}", styles["BodyText"]))
        if index != len(items):
            story.append(PageBreak())

    doc.build(story)
    return output_path

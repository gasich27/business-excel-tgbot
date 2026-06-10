from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_pdf_report(analysis: dict, chart_paths: list[Path], output_path: Path) -> Path:
    font_name = _register_font()
    styles = _styles(font_name)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=1.6 * cm,
        leftMargin=1.6 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
    )

    story = [
        Paragraph("АНАЛИЗ ДАННЫХ", styles["Title"]),
        Spacer(1, 0.6 * cm),
        Paragraph("1. Общая информация", styles["Heading2"]),
        _table(
            [
                ["Строк", analysis["rows"]],
                ["Столбцов", analysis["columns"]],
                ["Пропусков", analysis["missing_total"]],
                ["Дубликатов", analysis["duplicates"]],
            ],
            font_name,
        ),
        Spacer(1, 0.4 * cm),
        Paragraph("2. Типы столбцов", styles["Heading2"]),
        _table(
            [
                ["Даты", ", ".join(analysis["date_columns"]) or "-"],
                ["Числовые", ", ".join(analysis["numeric_columns"]) or "-"],
                ["Категориальные", ", ".join(analysis["categorical_columns"]) or "-"],
            ],
            font_name,
        ),
        Spacer(1, 0.4 * cm),
        Paragraph("3. Пропуски", styles["Heading2"]),
        _missing_table(analysis, font_name),
        Spacer(1, 0.4 * cm),
        Paragraph("4. Статистические показатели", styles["Heading2"]),
        _stats_table(analysis, font_name),
        PageBreak(),
        Paragraph("5. Графики", styles["Heading2"]),
    ]

    for chart_path in chart_paths:
        story.append(Paragraph(chart_path.stem.replace("_", " ").title(), styles["Heading3"]))
        story.append(Image(str(chart_path), width=16 * cm, height=9.5 * cm, kind="proportional"))
        story.append(Spacer(1, 0.4 * cm))

    _append_umap_section(story, analysis, font_name, styles)
    _append_business_sections(story, analysis, font_name, styles)

    story.extend(
        [
            PageBreak(),
            Paragraph("6. Выводы и рекомендации", styles["Heading2"]),
        ]
    )
    for insight in analysis.get("insights", []):
        story.append(Paragraph(f"• {insight}", styles["BodyText"]))
        story.append(Spacer(1, 0.16 * cm))

    doc.build(story)
    return output_path


def _append_business_sections(story: list, analysis: dict, font_name: str, styles: dict) -> None:
    business_result = analysis.get("business_result")
    if not business_result:
        return

    story.append(PageBreak())
    story.append(Paragraph("7. Основные KPI", styles["Heading2"]))
    if business_result.kpis:
        story.append(_table([[key, value] for key, value in business_result.kpis.items()], font_name))
    else:
        story.append(Paragraph("Специализированные KPI не рассчитаны для этого режима.", styles["BodyText"]))

    if business_result.tables:
        story.append(Spacer(1, 0.4 * cm))
        story.append(Paragraph("8. Результаты специализированного анализа", styles["Heading2"]))
        for title, table_data in business_result.tables.items():
            story.append(Paragraph(str(title), styles["Heading3"]))
            story.append(_dataframe_table(table_data, font_name))
            story.append(Spacer(1, 0.3 * cm))

    anomalies = analysis.get("anomalies") or {}
    anomaly_recommendations = anomalies.get("recommendations") or []
    if anomaly_recommendations:
        story.append(Spacer(1, 0.4 * cm))
        story.append(Paragraph("9. Найденные аномалии", styles["Heading2"]))
        for item in anomaly_recommendations:
            story.append(Paragraph(f"• {item}", styles["BodyText"]))

    if business_result.recommendations:
        story.append(Spacer(1, 0.4 * cm))
        story.append(Paragraph("10. Бизнес-рекомендации", styles["Heading2"]))
        for item in business_result.recommendations:
            story.append(Paragraph(f"• {item}", styles["BodyText"]))
            story.append(Spacer(1, 0.14 * cm))


def _append_umap_section(story: list, analysis: dict, font_name: str, styles: dict) -> None:
    umap = analysis.get("umap")
    if not umap or umap.get("error"):
        return

    story.append(PageBreak())
    story.append(Paragraph("UMAP-визуализация структуры данных", styles["Heading2"]))
    story.append(
        Paragraph(
            "UMAP сжимает многомерные числовые признаки до 2D-карты. Близкие точки похожи по использованным числовым признакам.",
            styles["BodyText"],
        )
    )
    story.append(Spacer(1, 0.3 * cm))
    path = Path(umap["path"])
    if path.exists():
        story.append(Image(str(path), width=16 * cm, height=10 * cm, kind="proportional"))
        story.append(Spacer(1, 0.3 * cm))
    story.append(
        _table(
            [
                ["Использовано строк", f"{umap['sample_size']} из {umap['total_rows']}"],
                ["Sample", "да" if umap["sampled"] else "нет"],
                ["Признаки", ", ".join(umap["used_columns"])],
            ],
            font_name,
        )
    )
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        Paragraph(
            "Важно: UMAP является методом визуализации и не доказывает наличие кластеров сам по себе.",
            styles["BodyText"],
        )
    )


def _register_font() -> str:
    candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/calibri.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for path in candidates:
        if path.exists():
            pdfmetrics.registerFont(TTFont("ReportFont", str(path)))
            return "ReportFont"
    return "Helvetica"


def _styles(font_name: str) -> dict:
    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = font_name
    styles["Title"].fontSize = 24
    styles["Title"].leading = 30
    styles["Heading2"].fontSize = 15
    styles["Heading2"].leading = 20
    styles["Heading3"].fontSize = 12
    styles["Heading3"].leading = 16
    styles["BodyText"].fontSize = 10
    styles["BodyText"].leading = 14
    return styles


def _table(rows: list[list[object]], font_name: str) -> Table:
    table = Table(rows, colWidths=[5 * cm, 11 * cm])
    table.setStyle(_table_style(font_name))
    return table


def _missing_table(analysis: dict, font_name: str) -> Table:
    rows = [["Столбец", "Пропуски"]]
    for column, value in analysis["missing_by_column"].head(15).items():
        rows.append([column, int(value)])
    return _table(rows, font_name)


def _stats_table(analysis: dict, font_name: str) -> Table:
    description = analysis["numeric_description"]
    if description.empty:
        return _table([["Числовые столбцы", "Не найдены"]], font_name)

    rows = [["Показатель", *[str(column) for column in description.columns[:5]]]]
    for index, values in description.iloc[:, :5].iterrows():
        rows.append([str(index), *[f"{value:.2f}" for value in values]])

    table = Table(rows, repeatRows=1)
    table.setStyle(_table_style(font_name))
    return table


def _dataframe_table(table_data, font_name: str) -> Table:
    if hasattr(table_data, "head"):
        dataframe = table_data.head(12).copy()
        rows = [[str(column) for column in dataframe.columns]]
        for row in dataframe.itertuples(index=False):
            rows.append([_short_cell(value) for value in row])
        table = Table(rows, repeatRows=1)
        table.setStyle(_table_style(font_name))
        return table
    if isinstance(table_data, list):
        return _table([[_short_cell(item)] for item in table_data[:12]], font_name)
    return _table([["Значение", _short_cell(table_data)]], font_name)


def _short_cell(value: object) -> str:
    text = str(value)
    return text[:80] + "..." if len(text) > 80 else text


def _table_style(font_name: str) -> TableStyle:
    return TableStyle(
        [
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8edf3")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1f2933")),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#c9d1d9")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("LEADING", (0, 0), (-1, -1), 10),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ]
    )

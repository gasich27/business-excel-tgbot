from __future__ import annotations

from pathlib import Path

from analysis.charts import build_charts
from analysis.eda import analyze_file
from analysis.insights import build_insights
from analysis.umap_analysis import build_umap_embedding
from business.anomaly_detection import detect_anomalies
from business.column_detection import detect_business_columns
from business.comparison_analysis import compare_reports
from business.customer_analysis import analyze_customers
from business.forecasting import forecast_sales
from business.inventory_analysis import analyze_inventory
from business.marketplace_analysis import analyze_marketplace
from business.models import AnalysisMode, BusinessAnalysisResult
from business.sales_analysis import analyze_sales
from reports.pdf_generator import build_pdf_report
from visualization.umap_plot import create_umap_plot


def build_analysis_report(file_path: Path, work_dir: Path, mode: AnalysisMode) -> tuple[dict, list[Path], Path]:
    analysis = analyze_file(file_path)
    dataframe = analysis["dataframe"]
    columns = detect_business_columns(dataframe)
    analysis["business_columns"] = columns

    base_charts = build_charts(dataframe, analysis, work_dir)
    base_insights = build_insights(analysis)
    business_result = _run_mode(mode, dataframe, columns, work_dir)
    anomaly_result = detect_anomalies(dataframe, columns, work_dir)
    umap_info = _build_umap_section(dataframe, work_dir)

    analysis["analysis_mode"] = mode.value
    analysis["insights"] = [*base_insights, *business_result.insights]
    analysis["business_result"] = business_result
    analysis["anomalies"] = anomaly_result
    analysis["umap"] = umap_info

    charts = [*base_charts, *business_result.chart_paths, *anomaly_result.get("chart_paths", [])]
    pdf_path = build_pdf_report(analysis, charts, work_dir / "report.pdf")
    return analysis, charts, pdf_path


def _build_umap_section(dataframe, work_dir: Path) -> dict:
    try:
        result = build_umap_embedding(dataframe)
        path = work_dir / "umap_report.png"
        create_umap_plot(result, str(path))
        return {
            "path": path,
            "used_columns": result.used_columns,
            "sample_size": result.sample_size,
            "total_rows": result.total_rows,
            "sampled": result.sampled,
            "message": result.message,
        }
    except Exception as exc:
        return {"error": str(exc)}


def build_comparison_report(first_path: Path, second_path: Path, work_dir: Path) -> tuple[dict, list[Path], Path]:
    first_analysis = analyze_file(first_path)
    second_analysis = analyze_file(second_path)
    business_result = compare_reports(first_analysis["dataframe"], second_analysis["dataframe"], work_dir)

    analysis = {
        "dataframe": first_analysis["dataframe"],
        "rows": first_analysis["rows"],
        "columns": first_analysis["columns"],
        "dtypes": first_analysis["dtypes"],
        "missing_total": first_analysis["missing_total"],
        "missing_by_column": first_analysis["missing_by_column"],
        "duplicates": first_analysis["duplicates"],
        "numeric_columns": first_analysis["numeric_columns"],
        "date_columns": first_analysis["date_columns"],
        "categorical_columns": first_analysis["categorical_columns"],
        "numeric_description": first_analysis["numeric_description"],
        "analysis_mode": AnalysisMode.COMPARISON.value,
        "business_columns": detect_business_columns(first_analysis["dataframe"]),
        "business_result": business_result,
        "insights": business_result.insights,
        "anomalies": {"rows": [], "sales": [], "recommendations": [], "chart_paths": []},
    }
    charts = business_result.chart_paths
    pdf_path = build_pdf_report(analysis, charts, work_dir / "comparison_report.pdf")
    return analysis, charts, pdf_path


def _run_mode(mode: AnalysisMode, dataframe, columns: dict[str, str], work_dir: Path) -> BusinessAnalysisResult:
    if mode == AnalysisMode.SALES:
        return analyze_sales(dataframe, columns, work_dir)
    if mode == AnalysisMode.MARKETPLACE:
        return analyze_marketplace(dataframe, columns, work_dir)
    if mode == AnalysisMode.INVENTORY:
        return analyze_inventory(dataframe, columns, work_dir)
    if mode == AnalysisMode.CUSTOMERS:
        return analyze_customers(dataframe, columns, work_dir)
    if mode == AnalysisMode.FORECAST:
        return forecast_sales(dataframe, columns, work_dir)

    return BusinessAnalysisResult(
        mode=AnalysisMode.UNIVERSAL,
        title="Универсальный анализ",
        recommendations=["Используйте специализированный режим, если хотите получить отраслевые KPI и рекомендации."],
    )

from __future__ import annotations

from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

from business.business_insights import generate_business_insights
from business.common import ensure_chart_dir, format_money, save_figure, to_datetime, to_number
from business.models import AnalysisMode, BusinessAnalysisResult


def analyze_sales(dataframe: pd.DataFrame, columns: dict[str, str], work_dir: Path) -> BusinessAnalysisResult:
    revenue_column = columns.get("revenue")
    date_column = columns.get("date")
    product_column = columns.get("product")
    category_column = columns.get("category")
    order_column = columns.get("order_id")

    if not revenue_column:
        return BusinessAnalysisResult(
            mode=AnalysisMode.SALES,
            title="Анализ продаж",
            recommendations=["Не найден столбец выручки. Добавьте колонку revenue/sales/выручка для полноценного анализа продаж."],
            metadata={"missing_required_columns": ["revenue"]},
        )

    revenue = to_number(dataframe[revenue_column]).fillna(0)
    orders = dataframe[order_column].nunique() if order_column else len(dataframe)
    total_revenue = float(revenue.sum())
    average_check = total_revenue / orders if orders else 0
    median_check = float(revenue[revenue > 0].median()) if (revenue > 0).any() else 0

    result = BusinessAnalysisResult(
        mode=AnalysisMode.SALES,
        title="Анализ продаж",
        kpis={
            "Общая выручка": format_money(total_revenue),
            "Количество заказов": int(orders),
            "Средний чек": format_money(average_check),
            "Медианный чек": format_money(median_check),
        },
        insights=generate_business_insights(dataframe, columns),
    )

    chart_dir = ensure_chart_dir(work_dir)
    if product_column:
        top_products = dataframe.assign(_revenue=revenue).groupby(product_column)["_revenue"].sum().sort_values(ascending=False).head(10)
        result.tables["Топ-10 товаров"] = top_products.reset_index(name="Выручка")
        result.chart_paths.append(_barh_chart(top_products, "Топ-10 товаров по выручке", chart_dir / "sales_top_products.png"))

    if category_column:
        top_categories = dataframe.assign(_revenue=revenue).groupby(category_column)["_revenue"].sum().sort_values(ascending=False).head(10)
        result.tables["Топ-10 категорий"] = top_categories.reset_index(name="Выручка")
        result.chart_paths.append(_barh_chart(top_categories, "Топ-10 категорий по выручке", chart_dir / "sales_top_categories.png"))

    if date_column:
        timeline = _timeline(dataframe, date_column, revenue)
        if not timeline.empty:
            daily = timeline.resample("D")["revenue"].sum()
            monthly = timeline.resample("ME")["revenue"].sum()
            result.tables["Продажи по дням"] = daily.reset_index()
            result.tables["Продажи по месяцам"] = monthly.reset_index()
            result.chart_paths.append(_line_chart(daily, "Продажи по дням", chart_dir / "sales_by_day.png"))
            result.chart_paths.append(_line_chart(monthly, "Продажи по месяцам", chart_dir / "sales_by_month.png"))

    result.recommendations = _sales_recommendations(result)
    return result


def _timeline(dataframe: pd.DataFrame, date_column: str, revenue: pd.Series) -> pd.DataFrame:
    return (
        pd.DataFrame({"date": to_datetime(dataframe[date_column]), "revenue": revenue})
        .dropna()
        .set_index("date")
        .sort_index()
    )


def _barh_chart(series: pd.Series, title: str, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(10, 6))
    series.sort_values().plot(kind="barh", ax=ax, color="#4c78a8")
    ax.set_title(title)
    ax.set_xlabel("Выручка")
    return save_figure(fig, path)


def _line_chart(series: pd.Series, title: str, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(10, 5))
    series.plot(ax=ax, color="#f58518", marker="o")
    ax.set_title(title)
    ax.set_xlabel("Дата")
    ax.set_ylabel("Выручка")
    return save_figure(fig, path)


def _sales_recommendations(result: BusinessAnalysisResult) -> list[str]:
    recommendations = ["Контролируйте вклад топ-товаров и категорий, чтобы снижать зависимость от единичных позиций."]
    if "Продажи по дням" in result.tables:
        recommendations.append("Используйте дневную динамику для планирования закупок, промо и нагрузки на операционные команды.")
    return recommendations

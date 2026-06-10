from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from business.column_detection import detect_business_columns
from business.common import ensure_chart_dir, format_money, format_percent, percent_change, save_figure, to_number
from business.models import AnalysisMode, BusinessAnalysisResult


def compare_reports(first: pd.DataFrame, second: pd.DataFrame, work_dir: Path) -> BusinessAnalysisResult:
    first_columns = detect_business_columns(first)
    second_columns = detect_business_columns(second)
    revenue_1 = _revenue(first, first_columns)
    revenue_2 = _revenue(second, second_columns)
    orders_1 = _orders(first, first_columns)
    orders_2 = _orders(second, second_columns)
    average_1 = revenue_1 / orders_1 if orders_1 else 0
    average_2 = revenue_2 / orders_2 if orders_2 else 0

    result = BusinessAnalysisResult(
        mode=AnalysisMode.COMPARISON,
        title="Сравнение двух отчетов",
        kpis={
            "Изменение выручки": format_percent(percent_change(revenue_2, revenue_1)),
            "Изменение заказов": format_percent(percent_change(orders_2, orders_1)),
            "Изменение среднего чека": format_percent(percent_change(average_2, average_1)),
            "Выручка 1": format_money(revenue_1),
            "Выручка 2": format_money(revenue_2),
        },
        insights=[_summary("выручка", revenue_1, revenue_2), _summary("количество заказов", orders_1, orders_2)],
    )

    chart_dir = ensure_chart_dir(work_dir)
    result.chart_paths.append(_kpi_chart({"Отчет 1": revenue_1, "Отчет 2": revenue_2}, "Сравнение выручки", chart_dir / "comparison_revenue.png"))

    category_table = _compare_dimension(first, second, first_columns, second_columns, "category")
    if not category_table.empty:
        result.tables["Изменение продаж по категориям"] = category_table
        result.chart_paths.append(_dimension_chart(category_table.head(10), "Изменение по категориям", chart_dir / "comparison_categories.png"))

    product_table = _compare_dimension(first, second, first_columns, second_columns, "product")
    if not product_table.empty:
        result.tables["Изменение продаж по товарам"] = product_table
        result.chart_paths.append(_dimension_chart(product_table.head(10), "Изменение по товарам", chart_dir / "comparison_products.png"))

    result.recommendations = ["Проверьте позиции с максимальным отрицательным изменением: они сильнее всего влияют на просадку результата."]
    return result


def _revenue(dataframe: pd.DataFrame, columns: dict[str, str]) -> float:
    revenue_column = columns.get("revenue")
    if not revenue_column:
        return 0
    return float(to_number(dataframe[revenue_column]).fillna(0).sum())


def _orders(dataframe: pd.DataFrame, columns: dict[str, str]) -> int:
    order_column = columns.get("order_id")
    return int(dataframe[order_column].nunique()) if order_column else len(dataframe)


def _summary(label: str, first: float, second: float) -> str:
    change = percent_change(second, first)
    if change is None:
        return f"Нельзя корректно рассчитать изменение показателя «{label}»: в первом отчете значение равно нулю."
    direction = "вырос" if change >= 0 else "снизился"
    return f"Показатель «{label}» {direction} на {abs(change):.1f}%."


def _compare_dimension(
    first: pd.DataFrame,
    second: pd.DataFrame,
    first_columns: dict[str, str],
    second_columns: dict[str, str],
    role: str,
) -> pd.DataFrame:
    first_dimension = first_columns.get(role)
    second_dimension = second_columns.get(role)
    first_revenue = first_columns.get("revenue")
    second_revenue = second_columns.get("revenue")
    if not first_dimension or not second_dimension or not first_revenue or not second_revenue:
        return pd.DataFrame()

    left = first.assign(_revenue=to_number(first[first_revenue]).fillna(0)).groupby(first_dimension)["_revenue"].sum()
    right = second.assign(_revenue=to_number(second[second_revenue]).fillna(0)).groupby(second_dimension)["_revenue"].sum()
    table = pd.DataFrame({"Отчет 1": left, "Отчет 2": right}).fillna(0)
    table["Изменение"] = table["Отчет 2"] - table["Отчет 1"]
    table["Изменение, %"] = table.apply(lambda row: percent_change(row["Отчет 2"], row["Отчет 1"]), axis=1)
    return table.sort_values("Изменение", ascending=False).reset_index(names="Позиция")


def _kpi_chart(values: dict[str, float], title: str, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar(values.keys(), values.values(), color=["#4c78a8", "#f58518"])
    ax.set_title(title)
    return save_figure(fig, path)


def _dimension_chart(table: pd.DataFrame, title: str, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(table["Позиция"].astype(str), table["Изменение"], color="#e45756")
    ax.set_title(title)
    ax.set_xlabel("Изменение выручки")
    return save_figure(fig, path)

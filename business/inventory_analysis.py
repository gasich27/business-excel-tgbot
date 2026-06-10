from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from business.common import ensure_chart_dir, format_money, save_figure, to_number
from business.models import AnalysisMode, BusinessAnalysisResult


def analyze_inventory(dataframe: pd.DataFrame, columns: dict[str, str], work_dir: Path) -> BusinessAnalysisResult:
    stock_column = columns.get("stock")
    product_column = columns.get("product")
    quantity_column = columns.get("quantity")

    if not stock_column or not product_column:
        return BusinessAnalysisResult(
            mode=AnalysisMode.INVENTORY,
            title="Анализ складских остатков",
            recommendations=["Для анализа склада нужны столбцы товара и остатка: product/товар и stock/остаток."],
            metadata={"missing_required_columns": ["product", "stock"]},
        )

    stock = to_number(dataframe[stock_column]).fillna(0)
    grouped_stock = dataframe.assign(_stock=stock).groupby(product_column)["_stock"].sum().sort_values(ascending=False)
    low_stock = grouped_stock[grouped_stock <= max(grouped_stock.median() * 0.25, 1)].sort_values().head(20)

    result = BusinessAnalysisResult(
        mode=AnalysisMode.INVENTORY,
        title="Анализ складских остатков",
        kpis={
            "Текущие остатки": format_money(float(grouped_stock.sum())),
            "Товаров с низким запасом": int(len(low_stock)),
        },
        tables={
            "Текущие остатки": grouped_stock.reset_index(name="Остаток").head(30),
            "Товары с низким запасом": low_stock.reset_index(name="Остаток"),
        },
        insights=["Низкий запас рассчитан относительно медианного остатка по товарам."],
        recommendations=["Сформируйте заявку на пополнение товаров с низким запасом, особенно если они входят в топ продаж."],
    )

    if quantity_column:
        sales = dataframe.assign(_qty=to_number(dataframe[quantity_column]).fillna(0)).groupby(product_column)["_qty"].sum().sort_values(ascending=False)
        result.tables["Наиболее продаваемые товары"] = sales.head(10).reset_index(name="Продано")
        result.tables["Наименее продаваемые товары"] = sales.tail(10).reset_index(name="Продано")

    chart_dir = ensure_chart_dir(work_dir)
    result.chart_paths.append(_barh_chart(grouped_stock.head(15).sort_values(), "Остатки по товарам", chart_dir / "inventory_stock.png"))
    if not low_stock.empty:
        result.chart_paths.append(_barh_chart(low_stock.sort_values(), "Товары с низким запасом", chart_dir / "inventory_low_stock.png"))
    return result


def _barh_chart(series: pd.Series, title: str, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(10, 6))
    series.plot(kind="barh", ax=ax, color="#72b7b2")
    ax.set_title(title)
    return save_figure(fig, path)

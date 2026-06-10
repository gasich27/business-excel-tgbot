from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from business.common import ensure_chart_dir, format_money, save_figure, to_number
from business.models import AnalysisMode, BusinessAnalysisResult


def analyze_customers(dataframe: pd.DataFrame, columns: dict[str, str], work_dir: Path) -> BusinessAnalysisResult:
    customer_column = columns.get("customer")
    revenue_column = columns.get("revenue")
    order_column = columns.get("order_id")

    if not customer_column or not revenue_column:
        return BusinessAnalysisResult(
            mode=AnalysisMode.CUSTOMERS,
            title="Анализ клиентской базы",
            recommendations=["Для анализа клиентов нужны столбцы клиента и выручки: customer/клиент и revenue/выручка."],
            metadata={"missing_required_columns": ["customer", "revenue"]},
        )

    revenue = to_number(dataframe[revenue_column]).fillna(0)
    customer_revenue = dataframe.assign(_revenue=revenue).groupby(customer_column)["_revenue"].sum().sort_values(ascending=False)
    customer_orders = dataframe.groupby(customer_column)[order_column].nunique() if order_column else dataframe.groupby(customer_column).size()
    repeat_customers = int((customer_orders > 1).sum())
    average_check = float(revenue.sum() / max(customer_orders.sum(), 1))
    high_ltv_threshold = customer_revenue.quantile(0.9) if len(customer_revenue) else 0
    high_ltv = customer_revenue[customer_revenue >= high_ltv_threshold]

    result = BusinessAnalysisResult(
        mode=AnalysisMode.CUSTOMERS,
        title="Анализ клиентской базы",
        kpis={
            "Количество клиентов": int(customer_revenue.size),
            "Средний чек": format_money(average_check),
            "Повторные покупатели": repeat_customers,
        },
        tables={
            "Топ клиентов по выручке": customer_revenue.head(10).reset_index(name="Выручка"),
            "Клиенты с высоким LTV": high_ltv.reset_index(name="LTV").head(30),
        },
        insights=["Клиенты с высоким LTV определены как верхние 10% по накопленной выручке."],
        recommendations=["Запустите отдельные удерживающие коммуникации для клиентов с высоким LTV и повторными покупками."],
    )

    chart_dir = ensure_chart_dir(work_dir)
    result.chart_paths.append(_barh_chart(customer_revenue.head(10).sort_values(), "Топ клиентов по выручке", chart_dir / "customer_top_revenue.png"))
    return result


def _barh_chart(series: pd.Series, title: str, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(10, 6))
    series.plot(kind="barh", ax=ax, color="#54a24b")
    ax.set_title(title)
    ax.set_xlabel("Выручка")
    return save_figure(fig, path)

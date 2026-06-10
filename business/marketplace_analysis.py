from __future__ import annotations

from pathlib import Path

import pandas as pd

from business.common import format_money, to_number
from business.models import AnalysisMode, BusinessAnalysisResult
from business.sales_analysis import analyze_sales


def analyze_marketplace(dataframe: pd.DataFrame, columns: dict[str, str], work_dir: Path) -> BusinessAnalysisResult:
    result = analyze_sales(dataframe, columns, work_dir)
    result.mode = AnalysisMode.MARKETPLACE
    result.title = "Анализ маркетплейса"

    revenue = to_number(dataframe[columns["revenue"]]).fillna(0) if columns.get("revenue") else pd.Series(dtype=float)
    commission = to_number(dataframe[columns["commission"]]).fillna(0) if columns.get("commission") else pd.Series(0, index=dataframe.index)
    returns = _returns_amount(dataframe, columns)
    profit = revenue - commission - returns

    result.kpis.update(
        {
            "Возвраты": format_money(float(returns.sum())),
            "Комиссии": format_money(float(commission.sum())),
            "Прибыль": format_money(float(profit.sum())),
        }
    )

    product_column = columns.get("product")
    if product_column and not revenue.empty:
        product_revenue = dataframe.assign(_revenue=revenue).groupby(product_column)["_revenue"].sum().sort_values(ascending=False)
        result.tables["Товары с низкими продажами"] = product_revenue.tail(10).reset_index(name="Выручка")
        main_share = product_revenue.cumsum() / max(product_revenue.sum(), 1)
        result.tables["Товары основной выручки"] = product_revenue[main_share <= 0.8].reset_index(name="Выручка")

    result.recommendations.extend(
        [
            "Проверьте товары с низкими продажами: для них нужны промо, изменение цены или вывод из ассортимента.",
            "Следите за комиссией и возвратами: они напрямую уменьшают прибыль даже при росте выручки.",
        ]
    )
    return result


def _returns_amount(dataframe: pd.DataFrame, columns: dict[str, str]) -> pd.Series:
    returns_column = columns.get("returns")
    revenue_column = columns.get("revenue")
    if not returns_column:
        return pd.Series(0, index=dataframe.index)

    returns = dataframe[returns_column]
    if pd.api.types.is_bool_dtype(returns):
        revenue = to_number(dataframe[revenue_column]).fillna(0) if revenue_column else pd.Series(0, index=dataframe.index)
        return revenue.where(returns, 0)
    return to_number(returns).fillna(0).abs()

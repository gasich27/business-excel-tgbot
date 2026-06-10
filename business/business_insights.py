from __future__ import annotations

import pandas as pd

from business.common import to_datetime, to_number


def generate_business_insights(dataframe: pd.DataFrame, columns: dict[str, str]) -> list[str]:
    insights: list[str] = []
    insights.extend(_missing_data_insights(dataframe))
    insights.extend(_category_dependency_insights(dataframe, columns))
    insights.extend(_product_dependency_insights(dataframe, columns))
    insights.extend(_sales_trend_insights(dataframe, columns))

    if not insights:
        insights.append("Данные не содержат явных бизнес-рисков по базовым правилам.")

    return insights


def _missing_data_insights(dataframe: pd.DataFrame) -> list[str]:
    total_cells = max(dataframe.shape[0] * dataframe.shape[1], 1)
    missing_share = dataframe.isna().sum().sum() / total_cells
    if missing_share > 0.1:
        return ["Обнаружено значительное количество пропущенных данных. Перед принятием решений стоит проверить качество выгрузки."]
    if missing_share > 0:
        return ["В данных есть пропуски. Они не выглядят критичными, но могут влиять на точность расчетов."]
    return []


def _category_dependency_insights(dataframe: pd.DataFrame, columns: dict[str, str]) -> list[str]:
    category_column = columns.get("category")
    revenue_column = columns.get("revenue")
    if not category_column:
        return []

    if revenue_column:
        grouped = dataframe.groupby(category_column, dropna=True)[revenue_column].apply(lambda value: to_number(value).sum())
        total = grouped.sum()
        if total > 0 and grouped.max() / total > 0.5:
            return ["Компания сильно зависит от одной категории товаров. Это повышает риск просадки при изменении спроса."]
    else:
        share = dataframe[category_column].astype(str).value_counts(normalize=True).head(1)
        if not share.empty and share.iloc[0] > 0.5:
            return ["Более половины записей относится к одной категории. Стоит проверить диверсификацию ассортимента."]
    return []


def _product_dependency_insights(dataframe: pd.DataFrame, columns: dict[str, str]) -> list[str]:
    product_column = columns.get("product")
    revenue_column = columns.get("revenue")
    if not product_column or not revenue_column:
        return []

    grouped = dataframe.groupby(product_column, dropna=True)[revenue_column].apply(lambda value: to_number(value).sum())
    total = grouped.sum()
    if total > 0 and grouped.max() / total > 0.4:
        return ["Высокая зависимость от одного товара: один продукт приносит более 40% выручки."]
    return []


def _sales_trend_insights(dataframe: pd.DataFrame, columns: dict[str, str]) -> list[str]:
    date_column = columns.get("date")
    revenue_column = columns.get("revenue")
    if not date_column or not revenue_column:
        return []

    series = (
        pd.DataFrame(
            {
                "date": to_datetime(dataframe[date_column]),
                "revenue": to_number(dataframe[revenue_column]),
            }
        )
        .dropna()
        .set_index("date")
        .sort_index()
        .resample("D")["revenue"]
        .sum()
    )
    if len(series) < 4:
        return []

    midpoint = len(series) // 2
    first_half = series.iloc[:midpoint].mean()
    second_half = series.iloc[midpoint:].mean()
    if second_half > first_half * 1.05:
        return ["Наблюдается положительная динамика продаж. Последний период в среднем сильнее предыдущего."]
    if second_half < first_half * 0.95:
        return ["Зафиксировано снижение продаж. Нужна проверка причин падения спроса или доступности товара."]
    return ["Продажи выглядят стабильными: существенного роста или падения по периоду не видно."]

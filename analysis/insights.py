import pandas as pd


def build_insights(analysis: dict) -> list[str]:
    dataframe: pd.DataFrame = analysis["dataframe"]
    insights: list[str] = []

    rows = analysis["rows"]
    missing_total = analysis["missing_total"]
    total_cells = max(rows * analysis["columns"], 1)
    missing_percent = missing_total / total_cells * 100
    if missing_total:
        insights.append(
            f"Обнаружено {missing_total} пропущенных значений ({missing_percent:.1f}% от всех ячеек)."
        )

    for column, count in analysis["missing_by_column"].head(5).items():
        if count:
            percent = count / max(rows, 1) * 100
            insights.append(f"В столбце «{column}» пропущено {int(count)} значений ({percent:.1f}%).")

    duplicates = analysis["duplicates"]
    if duplicates:
        insights.append(f"Найдено {duplicates} полностью повторяющихся строк.")

    insights.extend(_category_insights(dataframe, analysis["categorical_columns"], analysis["numeric_columns"]))
    insights.extend(_numeric_insights(dataframe, analysis["numeric_columns"]))
    insights.extend(_correlation_insights(dataframe, analysis["numeric_columns"]))

    if not insights:
        insights.append("Критичных проблем не найдено: данные выглядят пригодными для дальнейшего анализа.")

    return insights[:12]


def _category_insights(dataframe: pd.DataFrame, categorical_columns: list[str], numeric_columns: list[str]) -> list[str]:
    insights = []
    value_column = _choose_value_column(numeric_columns)
    for column in categorical_columns[:3]:
        distribution = dataframe[column].astype(str).value_counts(normalize=True).head(1)
        if not distribution.empty:
            name = distribution.index[0]
            share = distribution.iloc[0] * 100
            insights.append(f"Самое частое значение в «{column}» — «{name}» ({share:.1f}% строк).")

        if value_column and column in dataframe and value_column in dataframe:
            grouped = dataframe.groupby(column, dropna=True)[value_column].sum().sort_values(ascending=False)
            total = grouped.sum()
            if total:
                top_name = grouped.index[0]
                top_share = grouped.iloc[0] / total * 100
                insights.append(
                    f"«{top_name}» дает {top_share:.1f}% суммы по показателю «{value_column}»."
                )
                break
    return insights


def _numeric_insights(dataframe: pd.DataFrame, numeric_columns: list[str]) -> list[str]:
    insights = []
    for column in numeric_columns[:6]:
        series = dataframe[column].dropna()
        if len(series) < 3:
            continue
        skewness = series.skew()
        if skewness > 1:
            insights.append(f"Распределение «{column}» смещено вправо: есть крупные значения или выбросы.")
        elif skewness < -1:
            insights.append(f"Распределение «{column}» смещено влево: есть необычно малые значения.")
    return insights


def _correlation_insights(dataframe: pd.DataFrame, numeric_columns: list[str]) -> list[str]:
    if len(numeric_columns) < 2:
        return []

    corr = dataframe[numeric_columns].corr(numeric_only=True).abs()
    insights = []
    for left_index, left in enumerate(corr.columns):
        for right_index, right in enumerate(corr.columns):
            if left_index >= right_index:
                continue
            value = corr.loc[left, right]
            if pd.notna(value) and value >= 0.8:
                insights.append(f"Показатели «{left}» и «{right}» сильно связаны (корреляция {value:.2f}).")
    return insights[:3]


def _choose_value_column(numeric_columns: list[str]) -> str | None:
    if not numeric_columns:
        return None
    preferred_names = ("выруч", "revenue", "sales", "сумм", "amount", "price")
    for column in numeric_columns:
        lowered = column.lower()
        if any(name in lowered for name in preferred_names):
            return column
    return numeric_columns[0]

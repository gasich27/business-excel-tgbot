from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from business.common import ensure_chart_dir, safe_filename, save_figure, to_datetime, to_number


def detect_anomalies(dataframe: pd.DataFrame, columns: dict[str, str], work_dir: Path) -> dict:
    numeric_columns = [column for column in dataframe.columns if pd.api.types.is_numeric_dtype(dataframe[column])]
    anomalies = pd.DataFrame()
    recommendations: list[str] = []
    chart_paths: list[Path] = []

    if numeric_columns:
        anomalies = _isolation_forest(dataframe, numeric_columns)
        if not anomalies.empty:
            recommendations.append("Найдены нетипичные числовые значения. Проверьте эти строки на ошибки загрузки, возвраты или разовые крупные сделки.")
            chart_paths.extend(_numeric_anomaly_charts(dataframe, anomalies, numeric_columns, work_dir))

    sales_anomalies = _sales_anomalies(dataframe, columns)
    if not sales_anomalies.empty:
        recommendations.append("В продажах есть дни с аномально высокой или низкой выручкой. Их стоит сверить с акциями, сбоями или остатками.")
        chart_paths.append(_sales_anomaly_chart(sales_anomalies, work_dir))

    return {
        "rows": anomalies.head(30),
        "sales": sales_anomalies,
        "recommendations": recommendations,
        "chart_paths": chart_paths,
    }


def _isolation_forest(dataframe: pd.DataFrame, numeric_columns: list[str]) -> pd.DataFrame:
    try:
        from sklearn.ensemble import IsolationForest
    except ImportError:
        return pd.DataFrame()

    values = dataframe[numeric_columns].apply(pd.to_numeric, errors="coerce").fillna(0)
    if len(values) < 10:
        return pd.DataFrame()

    model = IsolationForest(contamination="auto", random_state=42)
    labels = model.fit_predict(values)
    return dataframe.loc[labels == -1].copy()


def _sales_anomalies(dataframe: pd.DataFrame, columns: dict[str, str]) -> pd.DataFrame:
    date_column = columns.get("date")
    revenue_column = columns.get("revenue")
    if not date_column or not revenue_column:
        return pd.DataFrame()

    daily = (
        pd.DataFrame({"date": to_datetime(dataframe[date_column]), "revenue": to_number(dataframe[revenue_column])})
        .dropna()
        .set_index("date")
        .resample("D")["revenue"]
        .sum()
        .to_frame()
    )
    if len(daily) < 7:
        return pd.DataFrame()

    q1 = daily["revenue"].quantile(0.25)
    q3 = daily["revenue"].quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return daily[(daily["revenue"] < lower) | (daily["revenue"] > upper)].reset_index()


def _numeric_anomaly_charts(dataframe: pd.DataFrame, anomalies: pd.DataFrame, numeric_columns: list[str], work_dir: Path) -> list[Path]:
    chart_dir = ensure_chart_dir(work_dir)
    paths: list[Path] = []
    for column in numeric_columns[:3]:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.scatter(dataframe.index, to_number(dataframe[column]), color="#4c78a8", label="Норма")
        ax.scatter(anomalies.index, to_number(anomalies[column]), color="#e45756", label="Аномалии")
        ax.set_title(f"Аномалии: {column}")
        ax.legend()
        paths.append(save_figure(fig, chart_dir / f"anomalies_{safe_filename(column)}.png"))
    return paths


def _sales_anomaly_chart(sales_anomalies: pd.DataFrame, work_dir: Path) -> Path:
    chart_dir = ensure_chart_dir(work_dir)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.scatter(sales_anomalies["date"], sales_anomalies["revenue"], color="#e45756")
    ax.set_title("Аномальные продажи по дням")
    ax.set_xlabel("Дата")
    ax.set_ylabel("Выручка")
    return save_figure(fig, chart_dir / "sales_anomalies.png")

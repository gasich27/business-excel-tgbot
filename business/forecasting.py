from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from business.common import ensure_chart_dir, format_money, save_figure, to_datetime, to_number
from business.models import AnalysisMode, BusinessAnalysisResult


def forecast_sales(dataframe: pd.DataFrame, columns: dict[str, str], work_dir: Path) -> BusinessAnalysisResult:
    date_column = columns.get("date")
    revenue_column = columns.get("revenue")
    if not date_column or not revenue_column:
        return BusinessAnalysisResult(
            mode=AnalysisMode.FORECAST,
            title="Прогнозирование продаж",
            recommendations=["Для прогноза нужны столбцы даты и выручки: date/дата и revenue/выручка."],
            metadata={"missing_required_columns": ["date", "revenue"]},
        )

    history = (
        pd.DataFrame({"ds": to_datetime(dataframe[date_column]), "y": to_number(dataframe[revenue_column])})
        .dropna()
        .groupby("ds", as_index=False)["y"]
        .sum()
        .sort_values("ds")
    )
    if len(history) < 10:
        return BusinessAnalysisResult(
            mode=AnalysisMode.FORECAST,
            title="Прогнозирование продаж",
            recommendations=["Для устойчивого прогноза нужно минимум 10 дат с продажами."],
        )

    forecast = _prophet_forecast(history)
    method = "Prophet"
    if forecast.empty:
        forecast = _moving_average_forecast(history)
        method = "скользящее среднее"

    chart_dir = ensure_chart_dir(work_dir)
    chart_path = _forecast_chart(history, forecast, chart_dir / "sales_forecast.png")
    horizon = forecast.tail(30)
    result = BusinessAnalysisResult(
        mode=AnalysisMode.FORECAST,
        title="Прогнозирование продаж",
        kpis={
            "Прогноз 7 дней": format_money(float(forecast.head(7)["yhat"].sum())),
            "Прогноз 14 дней": format_money(float(forecast.head(14)["yhat"].sum())),
            "Прогноз 30 дней": format_money(float(horizon["yhat"].sum())),
            "Метод": method,
        },
        tables={"Прогноз продаж": forecast},
        chart_paths=[chart_path],
        insights=[f"Сформирован прогноз продаж на 30 дней методом: {method}."],
        recommendations=["Используйте прогноз для планирования закупок, рекламного бюджета и операционной нагрузки."],
    )
    return result


def _prophet_forecast(history: pd.DataFrame) -> pd.DataFrame:
    try:
        from prophet import Prophet
    except ImportError:
        return pd.DataFrame()

    model = Prophet(daily_seasonality=False, weekly_seasonality=True, yearly_seasonality=False)
    model.fit(history)
    future = model.make_future_dataframe(periods=30)
    forecast = model.predict(future).tail(30)
    return forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]]


def _moving_average_forecast(history: pd.DataFrame) -> pd.DataFrame:
    average = history["y"].tail(7).mean()
    start = history["ds"].max() + pd.Timedelta(days=1)
    dates = pd.date_range(start, periods=30, freq="D")
    return pd.DataFrame({"ds": dates, "yhat": average, "yhat_lower": average * 0.85, "yhat_upper": average * 1.15})


def _forecast_chart(history: pd.DataFrame, forecast: pd.DataFrame, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(history["ds"], history["y"], label="Факт", color="#4c78a8")
    ax.plot(forecast["ds"], forecast["yhat"], label="Прогноз", color="#f58518")
    if {"yhat_lower", "yhat_upper"}.issubset(forecast.columns):
        ax.fill_between(forecast["ds"], forecast["yhat_lower"], forecast["yhat_upper"], color="#f58518", alpha=0.2)
    ax.set_title("Прогноз продаж")
    ax.set_xlabel("Дата")
    ax.set_ylabel("Выручка")
    ax.legend()
    return save_figure(fig, path)

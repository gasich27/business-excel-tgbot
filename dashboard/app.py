from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

import pandas as pd
import plotly.express as px
import streamlit as st

from analysis.eda import analyze_file
from business.anomaly_detection import detect_anomalies
from business.business_insights import generate_business_insights
from business.column_detection import detect_business_columns
from business.common import to_datetime, to_number
from business.forecasting import forecast_sales


st.set_page_config(page_title="Excel Analyst Dashboard", layout="wide")
st.title("Excel Analyst Dashboard")

uploaded_file = st.file_uploader("Загрузите Excel или CSV файл", type=["xlsx", "xls", "csv"])
if not uploaded_file:
    st.stop()

suffix = Path(uploaded_file.name).suffix
with NamedTemporaryFile(delete=False, suffix=suffix) as file:
    file.write(uploaded_file.getvalue())
    source_path = Path(file.name)

analysis = analyze_file(source_path)
dataframe: pd.DataFrame = analysis["dataframe"]
columns = detect_business_columns(dataframe)

st.sidebar.header("Фильтры")
filtered = dataframe.copy()
category_column = columns.get("category")
if category_column:
    categories = sorted(filtered[category_column].dropna().astype(str).unique())
    selected = st.sidebar.multiselect("Категории", categories, default=categories)
    if selected:
        filtered = filtered[filtered[category_column].astype(str).isin(selected)]

date_column = columns.get("date")
if date_column:
    dates = to_datetime(filtered[date_column]).dropna()
    if not dates.empty:
        start, end = st.sidebar.date_input("Период", value=(dates.min().date(), dates.max().date()))
        date_values = to_datetime(filtered[date_column])
        filtered = filtered[(date_values.dt.date >= start) & (date_values.dt.date <= end)]

revenue_column = columns.get("revenue")
order_column = columns.get("order_id")
revenue = to_number(filtered[revenue_column]).fillna(0) if revenue_column else pd.Series(dtype=float)
orders = filtered[order_column].nunique() if order_column else len(filtered)

kpi_1, kpi_2, kpi_3, kpi_4 = st.columns(4)
kpi_1.metric("Строк", len(filtered))
kpi_2.metric("Выручка", f"{revenue.sum():,.0f}" if revenue_column else "-")
kpi_3.metric("Заказы", orders)
kpi_4.metric("Средний чек", f"{revenue.sum() / orders:,.0f}" if revenue_column and orders else "-")

st.subheader("Интерактивные графики")
if date_column and revenue_column:
    timeline = (
        pd.DataFrame({"date": to_datetime(filtered[date_column]), "revenue": revenue})
        .dropna()
        .groupby("date", as_index=False)["revenue"]
        .sum()
    )
    st.plotly_chart(px.line(timeline, x="date", y="revenue", title="Продажи по дням"), use_container_width=True)

product_column = columns.get("product")
if product_column and revenue_column:
    products = filtered.assign(_revenue=revenue).groupby(product_column, as_index=False)["_revenue"].sum().sort_values("_revenue", ascending=False).head(20)
    st.plotly_chart(px.bar(products, x="_revenue", y=product_column, orientation="h", title="Топ товаров"), use_container_width=True)

if category_column and revenue_column:
    categories = filtered.assign(_revenue=revenue).groupby(category_column, as_index=False)["_revenue"].sum().sort_values("_revenue", ascending=False)
    st.plotly_chart(px.pie(categories, names=category_column, values="_revenue", title="Распределение выручки по категориям"), use_container_width=True)

st.subheader("Бизнес-выводы")
for insight in generate_business_insights(filtered, columns):
    st.write(f"- {insight}")

st.subheader("Аномалии")
anomalies = detect_anomalies(filtered, columns, Path(".dashboard_tmp"))
anomaly_rows = anomalies.get("rows")
if hasattr(anomaly_rows, "empty") and not anomaly_rows.empty:
    st.dataframe(anomaly_rows, use_container_width=True)
else:
    st.write("Аномалии не найдены или недостаточно данных для модели.")

st.subheader("Прогнозирование")
forecast = forecast_sales(filtered, columns, Path(".dashboard_tmp"))
forecast_table = forecast.tables.get("Прогноз продаж")
if hasattr(forecast_table, "empty") and not forecast_table.empty:
    st.plotly_chart(px.line(forecast_table, x="ds", y="yhat", title="Прогноз продаж"), use_container_width=True)
    st.dataframe(forecast_table, use_container_width=True)
else:
    for recommendation in forecast.recommendations:
        st.write(f"- {recommendation}")

st.subheader("Данные")
st.dataframe(filtered, use_container_width=True)

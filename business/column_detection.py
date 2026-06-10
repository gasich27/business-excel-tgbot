from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd


ColumnRole = str


@dataclass(frozen=True)
class ColumnPattern:
    role: ColumnRole
    keywords: tuple[str, ...]


PATTERNS: tuple[ColumnPattern, ...] = (
    ColumnPattern("date", ("date", "дата", "order_date", "created_at", "created", "datetime", "time", "day")),
    ColumnPattern("product", ("product", "товар", "sku", "item", "name", "номенклатура", "артикул", "offer")),
    ColumnPattern("price", ("price", "цена", "cost", "unit_price", "retail_price")),
    ColumnPattern("revenue", ("revenue", "sales", "turnover", "выручка", "сумма", "amount", "gmv", "итого")),
    ColumnPattern("quantity", ("quantity", "qty", "количество", "count", "units", "шт", "pcs")),
    ColumnPattern("category", ("category", "категория", "group", "type", "brand", "бренд", "предмет")),
    ColumnPattern("customer", ("customer", "buyer", "клиент", "покупатель", "client", "user", "phone", "email")),
    ColumnPattern("order_id", ("order_id", "order", "заказ", "номер заказа", "id заказа", "receipt")),
    ColumnPattern("commission", ("commission", "комиссия", "fee", "platform_fee", "вознаграждение")),
    ColumnPattern("returns", ("return", "returns", "возврат", "returned", "refund", "отмена")),
    ColumnPattern("profit", ("profit", "прибыль", "margin", "маржа")),
    ColumnPattern("stock", ("stock", "остаток", "остатки", "inventory", "available", "balance", "склад")),
)


def detect_business_columns(dataframe: pd.DataFrame) -> dict[str, str]:
    normalized = {_normalize(column): str(column) for column in dataframe.columns}
    detected: dict[str, str] = {}

    for pattern in PATTERNS:
        best_column = _find_best_match(normalized, pattern.keywords)
        if best_column:
            detected[pattern.role] = best_column

    return detected


def _find_best_match(normalized_columns: dict[str, str], keywords: tuple[str, ...]) -> str | None:
    for keyword in keywords:
        normalized_keyword = _normalize(keyword)
        for normalized_column, original_column in normalized_columns.items():
            if normalized_column == normalized_keyword:
                return original_column

    for keyword in keywords:
        normalized_keyword = _normalize(keyword)
        for normalized_column, original_column in normalized_columns.items():
            if normalized_keyword in normalized_column:
                return original_column

    return None


def _normalize(value: object) -> str:
    return re.sub(r"[^a-zа-я0-9]+", "_", str(value).lower(), flags=re.IGNORECASE).strip("_")

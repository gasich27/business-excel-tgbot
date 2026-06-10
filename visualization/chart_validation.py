from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from visualization.chart_config import ChartConfig, ChartType, OutputFormat


@dataclass(frozen=True)
class ValidationResult:
    is_valid: bool
    errors: list[str]


def validate_chart_config(dataframe: pd.DataFrame, config: ChartConfig) -> ValidationResult:
    """Validate chart parameters and return user-friendly errors."""

    errors: list[str] = []
    if dataframe.empty:
        errors.append("Таблица пустая. Построить график невозможно.")

    if config.output_format not in {item.value for item in OutputFormat}:
        errors.append("Выбран недопустимый формат результата. Доступны PNG и PDF.")

    chart_type = config.chart_type
    if chart_type not in {item.value for item in ChartType}:
        errors.append("Выбран неизвестный тип графика.")
        return ValidationResult(False, errors)

    if chart_type == ChartType.HEATMAP:
        numeric_columns = _numeric_columns(dataframe, excluded=config.excluded_columns)
        if len(numeric_columns) < 2:
            errors.append("Для heatmap нужно минимум две числовые колонки.")
        return ValidationResult(not errors, errors)

    if chart_type in {ChartType.HISTOGRAM, ChartType.BOXPLOT}:
        _require_y(dataframe, config, errors)
        for column in config.y_columns[:1]:
            if column in dataframe and not _is_numeric(dataframe[column]):
                errors.append("Для гистограммы и boxplot нужна числовая колонка.")

    if chart_type in {ChartType.LINE, ChartType.BAR, ChartType.HORIZONTAL_BAR, ChartType.AREA, ChartType.MULTI, ChartType.COMBO}:
        _require_x(dataframe, config, errors)
        _require_y(dataframe, config, errors)
        for column in config.y_columns:
            if column in dataframe and not _is_numeric(dataframe[column]):
                errors.append(f"Колонка Y «{column}» должна быть числовой.")

    if chart_type == ChartType.PIE:
        _require_x(dataframe, config, errors)
        _require_y(dataframe, config, errors)
        if config.x_column in dataframe:
            unique_count = dataframe[config.x_column].nunique(dropna=True)
            if unique_count > 30 and not config.top_n:
                errors.append("Для круговой диаграммы лучше использовать категорию с количеством значений не больше 10-15 или выбрать Top N.")
        if config.y_column in dataframe and not _is_numeric(dataframe[config.y_column]):
            errors.append("Для круговой диаграммы колонка значений должна быть числовой.")

    if chart_type == ChartType.SCATTER:
        _require_x(dataframe, config, errors)
        _require_y(dataframe, config, errors)
        if config.x_column in dataframe and not _is_numeric(dataframe[config.x_column]):
            errors.append("Для scatter plot ось X должна быть числовой.")
        if config.y_column in dataframe and not _is_numeric(dataframe[config.y_column]):
            errors.append("Для scatter plot ось Y должна быть числовой.")
        for optional_column, label in ((config.hue, "hue"), (config.size, "size")):
            if optional_column and optional_column not in dataframe.columns:
                errors.append(f"Колонка {label} не найдена в таблице.")
        if config.size and config.size in dataframe and not _is_numeric(dataframe[config.size]):
            errors.append("Колонка размера точки должна быть числовой.")

    if config.top_n is not None and config.top_n <= 0:
        errors.append("Top N должен быть положительным числом.")
    if config.bins is not None and config.bins <= 0:
        errors.append("Количество bins должно быть положительным числом.")

    return ValidationResult(not errors, errors)


def _require_x(dataframe: pd.DataFrame, config: ChartConfig, errors: list[str]) -> None:
    if not config.x_column:
        errors.append("Выберите колонку для оси X.")
    elif config.x_column not in dataframe.columns:
        errors.append(f"Колонка X «{config.x_column}» не найдена в таблице.")


def _require_y(dataframe: pd.DataFrame, config: ChartConfig, errors: list[str]) -> None:
    if not config.y_columns:
        errors.append("Выберите хотя бы одну колонку Y.")
    for column in config.y_columns:
        if column not in dataframe.columns:
            errors.append(f"Колонка Y «{column}» не найдена в таблице.")


def _is_numeric(series: pd.Series) -> bool:
    converted = pd.to_numeric(series, errors="coerce")
    return pd.api.types.is_numeric_dtype(converted) and converted.notna().any()


def _numeric_columns(dataframe: pd.DataFrame, excluded: list[str]) -> list[str]:
    excluded_set = set(excluded)
    return [
        column
        for column in dataframe.columns
        if column not in excluded_set and _is_numeric(dataframe[column])
    ]

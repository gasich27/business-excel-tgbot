from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class AnalysisMode(StrEnum):
    UNIVERSAL = "universal"
    SALES = "sales"
    MARKETPLACE = "marketplace"
    INVENTORY = "inventory"
    CUSTOMERS = "customers"
    COMPARISON = "comparison"
    FORECAST = "forecast"


@dataclass(frozen=True)
class ModeDefinition:
    mode: AnalysisMode
    title: str
    description: str


@dataclass
class BusinessAnalysisResult:
    mode: AnalysisMode
    title: str
    kpis: dict[str, Any] = field(default_factory=dict)
    tables: dict[str, Any] = field(default_factory=dict)
    insights: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    chart_paths: list[Path] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary_lines(self) -> list[str]:
        lines = [self.title]
        for name, value in self.kpis.items():
            lines.append(f"{name}: {value}")
        return lines


MODE_DEFINITIONS: tuple[ModeDefinition, ...] = (
    ModeDefinition(AnalysisMode.UNIVERSAL, "Универсальный анализ", "EDA, графики и базовые выводы"),
    ModeDefinition(AnalysisMode.SALES, "Анализ продаж", "Выручка, чеки, товары, категории и динамика"),
    ModeDefinition(AnalysisMode.MARKETPLACE, "Wildberries/Ozon", "Комиссии, возвраты, прибыль и топ товаров"),
    ModeDefinition(AnalysisMode.INVENTORY, "Складские остатки", "Остатки, дефицит и рекомендации по закупкам"),
    ModeDefinition(AnalysisMode.CUSTOMERS, "Клиентская база", "Повторные покупки, LTV и топ клиентов"),
    ModeDefinition(AnalysisMode.COMPARISON, "Сравнение двух отчетов", "Динамика KPI между двумя файлами"),
    ModeDefinition(AnalysisMode.FORECAST, "Прогнозирование продаж", "Прогноз на 7, 14 и 30 дней"),
)


def get_mode_definition(mode: AnalysisMode) -> ModeDefinition:
    for definition in MODE_DEFINITIONS:
        if definition.mode == mode:
            return definition
    raise ValueError(f"Unknown analysis mode: {mode}")

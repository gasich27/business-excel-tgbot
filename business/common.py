from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["axes.grid"] = True


def ensure_chart_dir(work_dir: Path, name: str = "business_charts") -> Path:
    chart_dir = work_dir / name
    chart_dir.mkdir(parents=True, exist_ok=True)
    return chart_dir


def format_money(value: float | int | None) -> str:
    if value is None:
        return "-"
    return f"{float(value):,.2f}".replace(",", " ")


def format_percent(value: float | int | None) -> str:
    if value is None:
        return "-"
    return f"{float(value):.1f}%"


def to_number(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def to_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce", dayfirst=True)


def save_figure(fig: plt.Figure, path: Path) -> Path:
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def safe_filename(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value).strip("_").lower()[:60] or "chart"


def dataframe_records(dataframe: pd.DataFrame, limit: int = 20) -> list[dict[str, Any]]:
    return dataframe.head(limit).where(pd.notna(dataframe), None).to_dict(orient="records")


def percent_change(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return (current - previous) / previous * 100

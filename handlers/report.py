from pathlib import Path

from business.analysis_service import build_analysis_report, build_comparison_report
from business.models import AnalysisMode


def build_report(file_path: Path, work_dir: Path, mode: AnalysisMode = AnalysisMode.UNIVERSAL) -> tuple[dict, list[Path], Path]:
    return build_analysis_report(file_path, work_dir, mode)


def build_compare_report(first_path: Path, second_path: Path, work_dir: Path) -> tuple[dict, list[Path], Path]:
    return build_comparison_report(first_path, second_path, work_dir)

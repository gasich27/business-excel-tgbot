from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer

from analysis.cluster_explanation import explain_clusters
from analysis.clustering import build_clustering_analysis, interpret_clustering
from analysis.eda import analyze_file
from analysis.embedding_comparison import build_embedding_comparison, interpret_embedding_comparison
from keyboards.chart_builder_keyboards import analysis_entry_keyboard, main_menu_keyboard, upload_file_keyboard
from reports.pdf_generator import _register_font, _styles
from reports.pptx_generator import generate_ml_pptx_report
from storage.history import HistoryRepository
from utils.ml_cache import get_cache_key, load_cached_result, save_cached_result
from visualization.clustering_plots import create_cluster_plot_png
from visualization.embedding_plots import create_embedding_comparison_png


router = Router()


@router.callback_query(F.data.in_({"file:embedding_comparison", "file:clustering", "file:pptx_report"}))
async def handle_ml_action(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    file_path = data.get("file_path")
    job_dir = data.get("job_dir")
    if not file_path or not job_dir:
        await callback.message.answer("Сначала загрузите файл.", reply_markup=upload_file_keyboard())
        await callback.answer()
        return

    action = callback.data.split(":", 1)[1]
    try:
        if action == "embedding_comparison":
            await _send_embedding(callback, file_path, job_dir, data.get("file_name", "file"))
        elif action == "clustering":
            await _send_clustering(callback, file_path, job_dir, data.get("file_name", "file"))
        elif action == "pptx_report":
            await _send_pptx(callback, file_path, job_dir, data.get("file_name", "file"))
    except ValueError as exc:
        await callback.message.answer(str(exc), reply_markup=analysis_entry_keyboard())
    except Exception:
        await callback.message.answer(
            "Не удалось выполнить ML-анализ. Проверьте данные и попробуйте другой режим.",
            reply_markup=analysis_entry_keyboard(),
        )
        raise
    await callback.answer()


@router.callback_query(F.data.in_({"file:upload_new", "file:main_menu"}))
async def handle_file_navigation(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    if callback.data == "file:upload_new":
        if data.get("job_dir"):
            shutil.rmtree(Path(data["job_dir"]), ignore_errors=True)
        await state.clear()
        await callback.message.answer("Отправьте новый Excel или CSV файл документом.")
    else:
        await callback.message.answer("Главное меню:", reply_markup=main_menu_keyboard())
        await callback.message.answer("Чтобы начать новый анализ, нажмите кнопку загрузки.", reply_markup=upload_file_keyboard())
    await callback.answer()


async def _send_embedding(callback: CallbackQuery, file_path: str, job_dir: str, file_name: str) -> None:
    result = await _cached(file_path, "embedding_comparison", lambda df: build_embedding_comparison(df))
    png = create_embedding_comparison_png(result, str(Path(job_dir) / "embedding_comparison.png"))
    pdf = _image_pdf(Path(png), "PCA / UMAP / t-SNE", Path(job_dir) / "embedding_comparison.pdf")

    await callback.message.answer_photo(FSInputFile(png), caption="PCA / UMAP / t-SNE готово.")
    await callback.message.answer("\n".join(interpret_embedding_comparison(result)))
    sent = await callback.message.answer_document(FSInputFile(pdf), caption="PDF-версия готова.")
    _save_ml_history(callback.from_user.id, file_name, "embedding_comparison", result.message, sent.document.file_id if sent.document else None)
    await _send_file_menu(callback)


async def _send_clustering(callback: CallbackQuery, file_path: str, job_dir: str, file_name: str) -> None:
    analysis = await asyncio.to_thread(analyze_file, Path(file_path))
    result = await _cached(file_path, "clustering", lambda df: build_clustering_analysis(df))
    png = create_cluster_plot_png(result, str(Path(job_dir) / "cluster_plot.png"))
    pdf = _image_pdf(Path(png), "Кластеризация", Path(job_dir) / "cluster_plot.pdf")

    await callback.message.answer_photo(FSInputFile(png), caption="Кластеризация готова.")

    explanations = explain_clusters(analysis["dataframe"], result.labels, result.used_columns)
    explanation_lines = []
    for item in explanations:
        explanation_lines.append(item.description)
        explanation_lines.extend(f"• {rec}" for rec in item.recommendations)

    text_parts = ["\n".join(interpret_clustering(result))]
    if explanation_lines:
        text_parts.append("\n\n".join(explanation_lines))
    await callback.message.answer("\n\n".join(text_parts))

    sent = await callback.message.answer_document(FSInputFile(pdf), caption="PDF-версия кластеризации готова.")
    _save_ml_history(callback.from_user.id, file_name, "clustering", result.message, sent.document.file_id if sent.document else None)
    await _send_file_menu(callback)


async def _send_pptx(callback: CallbackQuery, file_path: str, job_dir: str, file_name: str) -> None:
    await callback.message.answer("Готовлю PowerPoint-отчет...")
    analysis = await asyncio.to_thread(analyze_file, Path(file_path))
    embedding = await _cached(file_path, "embedding_comparison", lambda df: build_embedding_comparison(df))
    clustering = await _cached(file_path, "clustering", lambda df: build_clustering_analysis(df))
    explanations = explain_clusters(analysis["dataframe"], clustering.labels, clustering.used_columns)
    embedding_png = create_embedding_comparison_png(embedding, str(Path(job_dir) / "pptx_embeddings.png"))
    cluster_png = create_cluster_plot_png(clustering, str(Path(job_dir) / "pptx_clusters.png"))
    pptx = generate_ml_pptx_report(
        analysis["dataframe"],
        embedding,
        clustering,
        explanations,
        {"embeddings": embedding_png, "clusters": cluster_png},
        str(Path(job_dir) / "ml_report.pptx"),
    )
    sent = await callback.message.answer_document(FSInputFile(pptx), caption=f"PowerPoint-отчет готов: {file_name}")
    _save_ml_history(callback.from_user.id, file_name, "pptx_report", "PowerPoint ML report", sent.document.file_id if sent.document else None)
    await _send_file_menu(callback)


async def _cached(file_path: str, analysis_type: str, builder):
    key = get_cache_key(file_path, analysis_type)
    cached = load_cached_result(key)
    if cached is not None:
        return cached
    analysis = await asyncio.to_thread(analyze_file, Path(file_path))
    result = await asyncio.to_thread(builder, analysis["dataframe"])
    save_cached_result(key, result)
    return result


async def _send_file_menu(callback: CallbackQuery) -> None:
    await callback.message.answer("Что еще сделать с этим датасетом?", reply_markup=analysis_entry_keyboard())


def _save_ml_history(
    telegram_id: int | None,
    file_name: str,
    analysis_type: str,
    short_summary: str,
    report_file_id: str | None,
) -> None:
    if telegram_id is None:
        return
    HistoryRepository().add(
        telegram_id=telegram_id,
        file_name=file_name,
        analysis_type=analysis_type,
        results={"kpis": {"summary": short_summary}},
        report_file_id=report_file_id,
    )


def _image_pdf(image_path: Path, title: str, output_path: Path) -> str:
    font_name = _register_font()
    styles = _styles(font_name)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(output_path), pagesize=A4)
    story = [
        Paragraph(title, styles["Title"]),
        Spacer(1, 0.5 * cm),
        Image(str(image_path), width=17 * cm, height=11 * cm, kind="proportional"),
    ]
    doc.build(story)
    return str(output_path)

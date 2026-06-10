import asyncio
import shutil
import uuid
from pathlib import Path
from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, Message

from analysis.eda import analyze_file
from analysis.umap_analysis import build_umap_embedding, interpret_umap_result
from business.models import MODE_DEFINITIONS, AnalysisMode
from config import settings
from database.table_history import TableHistoryRepository
from database.umap_history import UmapHistoryRepository
from handlers.report import build_compare_report, build_report
from keyboards.chart_builder_keyboards import UPLOAD_FILE_BUTTON, analysis_entry_keyboard, chart_type_keyboard
from states.chart_builder_states import ChartBuilderStates
from storage.history import HistoryRepository
from visualization.umap_plot import create_umap_plot


router = Router()
SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".csv"}


class UploadStates(StatesGroup):
    waiting_for_file = State()
    waiting_for_entry_choice = State()
    waiting_for_mode = State()
    waiting_for_second_file = State()


@router.callback_query(F.data == "upload:start")
async def ask_for_file_from_inline(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(UploadStates.waiting_for_file)
    await callback.message.answer("Отправьте Excel или CSV файл документом.")
    await callback.answer()


@router.message(F.text == UPLOAD_FILE_BUTTON)
async def ask_for_file_from_reply(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(UploadStates.waiting_for_file)
    await message.answer("Отправьте Excel или CSV файл документом.")


@router.message(F.document, UploadStates.waiting_for_second_file)
async def handle_second_document(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    first_path = Path(data["first_path"])
    job_dir = Path(data["job_dir"])
    second_path = await _save_document(message, job_dir, "second")
    if not second_path:
        return

    status = await message.answer("Второй файл получен. Сравниваю отчеты...")
    try:
        analysis, charts, pdf_path = await asyncio.to_thread(build_compare_report, first_path, second_path, job_dir)
        report_file_id = await _send_results(message, status, analysis, pdf_path)
        _save_history(
            message.from_user.id if message.from_user else None,
            data.get("file_name", "first file"),
            AnalysisMode.COMPARISON,
            analysis,
            report_file_id,
        )
        await state.set_state(UploadStates.waiting_for_entry_choice)
        await message.answer("Можно продолжить работу с первым загруженным файлом.", reply_markup=analysis_entry_keyboard())
    except Exception:
        await status.edit_text(
            "Не удалось сравнить файлы. Проверьте, что оба файла содержат сопоставимые данные."
        )
        raise


@router.message(F.document)
async def handle_document(message: Message, state: FSMContext) -> None:
    job_dir = settings.temp_dir / f"{message.from_user.id if message.from_user else 'user'}_{uuid.uuid4().hex}"
    job_dir.mkdir(parents=True, exist_ok=True)
    input_path = await _save_document(message, job_dir, "input")
    if not input_path:
        shutil.rmtree(job_dir, ignore_errors=True)
        return

    file_name = message.document.file_name if message.document else input_path.name
    if message.from_user and message.document:
        TableHistoryRepository().add(message.from_user.id, file_name, message.document.file_id)

    await state.set_state(UploadStates.waiting_for_entry_choice)
    await state.update_data(file_path=str(input_path), job_dir=str(job_dir), file_name=file_name)
    await _send_umap_preview(message, state, input_path, job_dir, file_name)
    await message.answer("Файл получен. Что сделать с данными?", reply_markup=analysis_entry_keyboard())


@router.callback_query(
    UploadStates.waiting_for_entry_choice,
    F.data.in_({"file:auto_analysis", "file:chart_builder"}),
)
async def handle_entry_choice(callback: CallbackQuery, state: FSMContext) -> None:
    choice = callback.data.split(":", 1)[1]
    data = await state.get_data()
    job_dir = Path(data["job_dir"])
    file_path = Path(data["file_path"])

    if choice == "chart_builder":
        await _switch_uploaded_file_to_chart_builder(callback, state, file_path, job_dir, data)
        await callback.answer()
        return

    await state.set_state(UploadStates.waiting_for_mode)
    await callback.message.edit_text("Выберите режим автоматического анализа:", reply_markup=_mode_keyboard())
    await callback.answer()


@router.callback_query(UploadStates.waiting_for_mode, F.data.startswith("mode:"))
async def handle_mode_selection(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    job_dir = Path(data["job_dir"])
    file_path = Path(data["file_path"])

    mode_value = callback.data.split(":", 1)[1]
    if mode_value == "back":
        await state.set_state(UploadStates.waiting_for_entry_choice)
        await callback.message.edit_text("Файл уже загружен. Выберите действие:", reply_markup=analysis_entry_keyboard())
        await callback.answer()
        return

    mode = AnalysisMode(mode_value)
    if mode == AnalysisMode.COMPARISON:
        await state.update_data(first_path=str(file_path))
        await state.set_state(UploadStates.waiting_for_second_file)
        await callback.message.edit_text("Загрузите второй файл для сравнения.")
        await callback.answer()
        return

    status = await callback.message.edit_text("Режим выбран. Анализирую данные и готовлю PDF-отчет...")
    await callback.answer()
    try:
        analysis, charts, pdf_path = await asyncio.to_thread(build_report, file_path, job_dir, mode)
        report_file_id = await _send_results(callback.message, status, analysis, pdf_path)
        _save_history(callback.from_user.id, data.get("file_name", file_path.name), mode, analysis, report_file_id)
        await state.set_state(UploadStates.waiting_for_entry_choice)
        await callback.message.answer("Что еще сделать с этим датасетом?", reply_markup=analysis_entry_keyboard())
    except Exception:
        await status.edit_text("Не удалось обработать файл. Проверьте структуру данных и попробуйте снова.")
        await state.set_state(UploadStates.waiting_for_entry_choice)
        await callback.message.answer("Можно выбрать другое действие по этому файлу.", reply_markup=analysis_entry_keyboard())
        raise


@router.message()
async def fallback(message: Message) -> None:
    await message.answer(
        "Нажмите «Загрузить файл для анализа» или отправьте .xlsx, .xls, .csv как документ."
    )


async def _save_document(message: Message, job_dir: Path, prefix: str) -> Path | None:
    document = message.document
    if not document or not document.file_name:
        await message.answer("Не удалось прочитать файл. Попробуйте отправить документ еще раз.")
        return None

    source_name = Path(document.file_name)
    extension = source_name.suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        await message.answer("Формат не поддерживается. Отправьте файл .xlsx, .xls или .csv.")
        return None

    max_bytes = settings.max_file_size_mb * 1024 * 1024
    if document.file_size and document.file_size > max_bytes:
        await message.answer(f"Файл слишком большой. Максимальный размер: {settings.max_file_size_mb} МБ.")
        return None

    target_path = job_dir / f"{prefix}{extension}"
    await message.bot.download(document, destination=target_path)
    return target_path


def _mode_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=definition.title, callback_data=f"mode:{definition.mode.value}")]
        for definition in MODE_DEFINITIONS
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="mode:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _switch_uploaded_file_to_chart_builder(
    callback: CallbackQuery,
    state: FSMContext,
    file_path: Path,
    job_dir: Path,
    data: dict[str, Any],
) -> None:
    await callback.message.edit_text("Читаю таблицу для конструктора графиков...")
    analysis = await asyncio.to_thread(analyze_file, file_path)
    columns = list(analysis["dataframe"].columns)
    await state.set_state(ChartBuilderStates.choosing_chart_type)
    await state.update_data(
        file_path=str(file_path),
        job_dir=str(job_dir),
        file_name=data.get("file_name", file_path.name),
        columns=columns,
        numeric_columns=analysis["numeric_columns"],
        config={},
        selected_y=[],
        excluded_columns=[],
        built_charts=[],
        return_to_file_menu=True,
    )
    await callback.message.answer(_columns_text(columns))
    await callback.message.answer("Выберите тип графика:", reply_markup=chart_type_keyboard())


def _columns_text(columns: list[str]) -> str:
    lines = ["Колонки в файле:"]
    lines.extend(f"{index}. {column}" for index, column in enumerate(columns, start=1))
    return "\n".join(lines)


async def _send_umap_preview(message: Message, state: FSMContext, file_path: Path, job_dir: Path, file_name: str) -> None:
    try:
        umap_path, result, _ = await asyncio.to_thread(_build_umap_for_file, file_path, job_dir)
    except Exception as exc:
        await state.update_data(umap_error=str(exc))
        await message.answer(str(exc))
        return

    await state.update_data(
        umap_path=str(umap_path),
        umap_used_columns=result.used_columns,
        umap_sample_size=result.sample_size,
        umap_total_rows=result.total_rows,
        umap_sampled=result.sampled,
    )
    if message.from_user:
        UmapHistoryRepository().add(message.from_user.id, file_name, result)
    await message.answer_photo(
        FSInputFile(umap_path),
        caption="Это UMAP-карта структуры данных. Близкие точки похожи по числовым признакам.",
    )


async def _send_umap_analysis(callback: CallbackQuery, state: FSMContext, file_path: Path, job_dir: Path, data: dict[str, Any]) -> None:
    umap_path = data.get("umap_path")
    if umap_path and Path(umap_path).exists():
        await callback.message.answer_photo(FSInputFile(umap_path), caption="UMAP-карта структуры данных.")
        analysis = await asyncio.to_thread(analyze_file, file_path)
        result = await asyncio.to_thread(build_umap_embedding, analysis["dataframe"])
    else:
        try:
            path, result, _ = await asyncio.to_thread(_build_umap_for_file, file_path, job_dir)
        except Exception as exc:
            await callback.message.answer(str(exc), reply_markup=analysis_entry_keyboard())
            return
        await state.update_data(umap_path=str(path))
        await callback.message.answer_photo(FSInputFile(path), caption="UMAP-карта структуры данных.")

    await callback.message.answer("\n".join(interpret_umap_result(result)), reply_markup=analysis_entry_keyboard())


def _build_umap_for_file(file_path: Path, job_dir: Path) -> tuple[Path, Any, dict]:
    analysis = analyze_file(file_path)
    result = build_umap_embedding(analysis["dataframe"])
    output_path = job_dir / "umap_preview.png"
    create_umap_plot(result, str(output_path))
    return output_path, result, analysis


async def _send_results(message: Message, status_message: Message, analysis: dict, pdf_path: Path) -> str | None:
    business_result = analysis.get("business_result")
    mode_title = business_result.title if business_result else analysis.get("analysis_mode", "analysis")
    await status_message.edit_text(
        "Файл успешно обработан.\n\n"
        f"Режим: {mode_title}\n"
        "Найдено:\n"
        f"• строк: {analysis['rows']}\n"
        f"• столбцов: {analysis['columns']}\n"
        f"• пропусков: {analysis['missing_total']}\n"
        f"• дубликатов: {analysis['duplicates']}\n\n"
        "PDF-отчет сформирован."
    )

    sent_report = await message.answer_document(FSInputFile(pdf_path), caption="Ваш PDF-отчет готов.")
    return sent_report.document.file_id if sent_report.document else None


def _save_history(
    telegram_id: int | None,
    file_name: str,
    mode: AnalysisMode,
    analysis: dict[str, Any],
    report_file_id: str | None = None,
) -> None:
    if telegram_id is None:
        return
    business_result = analysis.get("business_result")
    HistoryRepository().add(
        telegram_id=telegram_id,
        file_name=file_name,
        analysis_type=mode.value,
        results={
            "kpis": business_result.kpis if business_result else {},
            "rows": analysis.get("rows"),
            "columns": analysis.get("columns"),
            "missing_total": analysis.get("missing_total"),
        },
        report_file_id=report_file_id,
    )

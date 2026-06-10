from __future__ import annotations

import asyncio
import shutil
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from analysis.eda import analyze_file
from config import settings
from database.chart_history import ChartHistoryRepository
from database.table_history import TableHistoryRepository
from handlers.upload import UploadStates
from keyboards.chart_builder_keyboards import (
    after_chart_keyboard,
    aggregation_keyboard,
    analysis_entry_keyboard,
    bins_keyboard,
    chart_type_keyboard,
    columns_keyboard,
    combo_type_keyboard,
    confirm_keyboard,
    output_format_keyboard,
    sorting_keyboard,
    top_n_keyboard,
)
from reports.custom_charts_pdf import build_custom_charts_pdf
from states.chart_builder_states import ChartBuilderStates
from visualization.chart_builder import build_custom_chart
from visualization.chart_config import CHART_TYPE_TITLES, ChartConfig, ChartType


router = Router()
SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".csv"}
CHART_BUILDER_TEXT = "📈 Конструктор графиков"
CHART_BUILDER_TEXT_NO_ICON = "Конструктор графиков"
MY_CHARTS_TEXT = "Мои графики"


@router.message(F.text.in_({CHART_BUILDER_TEXT, CHART_BUILDER_TEXT_NO_ICON, "/charts"}))
async def start_chart_builder_text(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(ChartBuilderStates.waiting_for_file)
    await message.answer("Загрузите Excel или CSV файл для конструктора графиков.")


@router.message(F.text == MY_CHARTS_TEXT)
async def show_chart_history_text(message: Message) -> None:
    if not message.from_user:
        await message.answer("Не удалось определить пользователя.")
        return
    items = ChartHistoryRepository().list_recent(message.from_user.id)
    if not items:
        await message.answer("История графиков пока пустая.")
        return
    lines = ["Последние графики:"]
    for item in items:
        lines.append(
            f"{item.created_at}\n"
            f"{item.file_name} | {item.chart_type} | {item.output_format}\n"
            f"X: {item.x_column or '-'} | Y: {item.y_columns or '-'} | agg: {item.aggregation or '-'}"
        )
    await message.answer("\n\n".join(lines))


@router.message(ChartBuilderStates.waiting_for_file, F.document)
async def receive_chart_file(message: Message, state: FSMContext) -> None:
    document = message.document
    if not document or not document.file_name:
        await message.answer("Не удалось прочитать файл. Отправьте документ еще раз.")
        return

    extension = Path(document.file_name).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        await message.answer("Формат не поддерживается. Нужен .xlsx, .xls или .csv.")
        return

    job_dir = settings.temp_dir / f"chart_builder_{message.from_user.id if message.from_user else 'user'}_{uuid.uuid4().hex}"
    job_dir.mkdir(parents=True, exist_ok=True)
    file_path = job_dir / f"input{extension}"
    await message.bot.download(document, destination=file_path)
    if message.from_user:
        TableHistoryRepository().add(message.from_user.id, document.file_name, document.file_id)

    try:
        analysis = await asyncio.to_thread(analyze_file, file_path)
    except Exception:
        shutil.rmtree(job_dir, ignore_errors=True)
        await message.answer("Не удалось прочитать таблицу. Проверьте файл и попробуйте снова.")
        raise

    await state.update_data(
        file_path=str(file_path),
        job_dir=str(job_dir),
        file_name=document.file_name,
        columns=list(analysis["dataframe"].columns),
        numeric_columns=analysis["numeric_columns"],
        config={},
        selected_y=[],
        excluded_columns=[],
        built_charts=[],
        return_to_file_menu=False,
    )
    await state.set_state(ChartBuilderStates.choosing_chart_type)
    data = await state.get_data()
    await message.answer(_columns_text(data["columns"]))
    await message.answer("Выберите тип графика:", reply_markup=chart_type_keyboard())


@router.callback_query(ChartBuilderStates.choosing_chart_type, F.data.startswith("cb:type:"))
async def choose_chart_type(callback: CallbackQuery, state: FSMContext) -> None:
    chart_type = callback.data.rsplit(":", 1)[1]
    await _update_config(state, chart_type=chart_type, title=CHART_TYPE_TITLES.get(chart_type))
    data = await state.get_data()

    if chart_type == ChartType.HEATMAP:
        await state.set_state(ChartBuilderStates.choosing_multiple_y_columns)
        await state.update_data(selection_mode="exclude_heatmap")
        await callback.message.edit_text(
            "Heatmap использует числовые колонки автоматически. Выберите колонки, которые нужно исключить, или нажмите «Готово».",
            reply_markup=columns_keyboard(data["numeric_columns"], "cb:multi", done=True),
        )
    elif chart_type in {ChartType.HISTOGRAM, ChartType.BOXPLOT}:
        await state.set_state(ChartBuilderStates.choosing_y_column)
        await callback.message.edit_text("Выберите числовую колонку:", reply_markup=columns_keyboard(data["numeric_columns"], "cb:y"))
    else:
        await state.set_state(ChartBuilderStates.choosing_x_column)
        await callback.message.edit_text("Выберите колонку X:", reply_markup=columns_keyboard(data["columns"], "cb:x"))
    await callback.answer()


@router.callback_query(F.data == "cb:back")
async def chart_builder_back(callback: CallbackQuery, state: FSMContext) -> None:
    answered = await _go_back(callback, state)
    if not answered:
        await callback.answer()


@router.callback_query(ChartBuilderStates.choosing_x_column, F.data.startswith("cb:x:"))
async def choose_x(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    column = _column_from_callback(callback.data, data["columns"])
    await _update_config(state, x_column=column)
    config = _config(await state.get_data())
    data = await state.get_data()

    if config.chart_type in {ChartType.LINE, ChartType.AREA, ChartType.MULTI}:
        await state.set_state(ChartBuilderStates.choosing_multiple_y_columns)
        await state.update_data(selection_mode="multi_y", selected_y=[])
        await callback.message.edit_text(
            "Выберите одну или несколько Y-колонок:",
            reply_markup=columns_keyboard(data["numeric_columns"], "cb:multi", done=True),
        )
    else:
        await state.set_state(ChartBuilderStates.choosing_y_column)
        await callback.message.edit_text("Выберите колонку Y:", reply_markup=columns_keyboard(data["numeric_columns"], "cb:y"))
    await callback.answer()


@router.callback_query(ChartBuilderStates.choosing_y_column, F.data.startswith("cb:y:"))
async def choose_y(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    column = _column_from_callback(callback.data, data["numeric_columns"])
    config = _config(data)

    if config.chart_type == ChartType.COMBO and len(config.y_columns) == 1:
        await _update_config(state, y_columns=[config.y_columns[0], column])
        await state.set_state(ChartBuilderStates.choosing_aggregation)
        await callback.message.edit_text("Выберите тип отображения Y1:", reply_markup=combo_type_keyboard("y1type"))
    else:
        await _update_config(state, y_columns=[column])
        config = _config(await state.get_data())
        if config.chart_type == ChartType.HISTOGRAM:
            await state.set_state(ChartBuilderStates.choosing_bins)
            await callback.message.edit_text("Выберите количество bins:", reply_markup=bins_keyboard())
        elif config.chart_type == ChartType.BOXPLOT:
            await state.set_state(ChartBuilderStates.choosing_hue)
            await callback.message.edit_text(
                "Выберите группировку для boxplot или пропустите:",
                reply_markup=columns_keyboard(data["columns"], "cb:hue", include_skip=True),
            )
        elif config.chart_type == ChartType.SCATTER:
            await state.set_state(ChartBuilderStates.choosing_hue)
            await callback.message.edit_text(
                "Выберите цветовую группировку hue или пропустите:",
                reply_markup=columns_keyboard(data["columns"], "cb:hue", include_skip=True),
            )
        elif config.chart_type == ChartType.COMBO:
            await callback.message.edit_text("Выберите колонку Y2:", reply_markup=columns_keyboard(data["numeric_columns"], "cb:y"))
        else:
            await state.set_state(ChartBuilderStates.choosing_aggregation)
            await callback.message.edit_text("Выберите агрегацию:", reply_markup=aggregation_keyboard())
    await callback.answer()


@router.callback_query(ChartBuilderStates.choosing_multiple_y_columns, F.data.startswith("cb:multi:"))
async def choose_multiple(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    mode = data.get("selection_mode")
    value = callback.data.rsplit(":", 1)[1]

    if value == "done":
        if mode == "exclude_heatmap":
            await _update_config(state, excluded_columns=data.get("excluded_columns", []))
            await state.set_state(ChartBuilderStates.choosing_output_format)
            await callback.message.edit_text("Выберите формат результата:", reply_markup=output_format_keyboard())
        else:
            selected = data.get("selected_y", [])
            if not selected:
                await callback.answer("Выберите хотя бы одну Y-колонку.", show_alert=True)
                return
            await _update_config(state, y_columns=selected)
            await state.set_state(ChartBuilderStates.choosing_aggregation)
            await callback.message.edit_text("Выберите агрегацию:", reply_markup=aggregation_keyboard())
        await callback.answer()
        return

    column = data["numeric_columns"][int(value)]
    key = "excluded_columns" if mode == "exclude_heatmap" else "selected_y"
    selected = list(data.get(key, []))
    if column in selected:
        selected.remove(column)
    else:
        selected.append(column)
    await state.update_data(**{key: selected})
    await callback.answer(f"Выбрано: {', '.join(selected) or 'ничего'}")


@router.callback_query(ChartBuilderStates.choosing_aggregation, F.data.startswith("cb:y1type:"))
async def choose_combo_y1_type(callback: CallbackQuery, state: FSMContext) -> None:
    await _update_config(state, y1_chart_type=callback.data.rsplit(":", 1)[1])
    await callback.message.edit_text("Выберите тип отображения Y2:", reply_markup=combo_type_keyboard("y2type"))
    await callback.answer()


@router.callback_query(ChartBuilderStates.choosing_aggregation, F.data.startswith("cb:y2type:"))
async def choose_combo_y2_type(callback: CallbackQuery, state: FSMContext) -> None:
    await _update_config(state, y2_chart_type=callback.data.rsplit(":", 1)[1], use_secondary_y=True)
    await callback.message.edit_text("Выберите агрегацию:", reply_markup=aggregation_keyboard())
    await callback.answer()


@router.callback_query(ChartBuilderStates.choosing_aggregation, F.data.startswith("cb:agg:"))
async def choose_aggregation(callback: CallbackQuery, state: FSMContext) -> None:
    await _update_config(state, aggregation=callback.data.rsplit(":", 1)[1])
    config = _config(await state.get_data())
    if config.chart_type in {ChartType.BAR, ChartType.HORIZONTAL_BAR, ChartType.PIE}:
        await state.set_state(ChartBuilderStates.choosing_top_n)
        await callback.message.edit_text("Выберите Top N:", reply_markup=top_n_keyboard())
    else:
        await state.set_state(ChartBuilderStates.choosing_sorting)
        await callback.message.edit_text("Выберите сортировку:", reply_markup=sorting_keyboard(for_x=True))
    await callback.answer()


@router.callback_query(ChartBuilderStates.choosing_top_n, F.data.startswith("cb:top:"))
async def choose_top_n(callback: CallbackQuery, state: FSMContext) -> None:
    top_n = int(callback.data.rsplit(":", 1)[1])
    await _update_config(state, top_n=top_n or None)
    await state.set_state(ChartBuilderStates.choosing_sorting)
    await callback.message.edit_text("Выберите сортировку:", reply_markup=sorting_keyboard())
    await callback.answer()


@router.callback_query(ChartBuilderStates.choosing_bins, F.data.startswith("cb:bins:"))
async def choose_bins(callback: CallbackQuery, state: FSMContext) -> None:
    await _update_config(state, bins=int(callback.data.rsplit(":", 1)[1]))
    await state.set_state(ChartBuilderStates.choosing_output_format)
    await callback.message.edit_text("Выберите формат результата:", reply_markup=output_format_keyboard())
    await callback.answer()


@router.callback_query(ChartBuilderStates.choosing_hue, F.data.startswith("cb:hue:"))
async def choose_hue(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    value = callback.data.rsplit(":", 1)[1]
    config = _config(data)
    column = None if value == "skip" else _column_from_callback(callback.data, data["columns"])
    if config.chart_type == ChartType.BOXPLOT:
        await _update_config(state, x_column=column or config.y_column)
        await state.set_state(ChartBuilderStates.choosing_output_format)
        await callback.message.edit_text("Выберите формат результата:", reply_markup=output_format_keyboard())
    else:
        await _update_config(state, hue=column)
        await state.set_state(ChartBuilderStates.choosing_size)
        await callback.message.edit_text(
            "Выберите колонку размера точки или пропустите:",
            reply_markup=columns_keyboard(data["numeric_columns"], "cb:size", include_skip=True),
        )
    await callback.answer()


@router.callback_query(ChartBuilderStates.choosing_size, F.data.startswith("cb:size:"))
async def choose_size(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    value = callback.data.rsplit(":", 1)[1]
    column = None if value == "skip" else _column_from_callback(callback.data, data["numeric_columns"])
    await _update_config(state, size=column)
    await state.set_state(ChartBuilderStates.choosing_output_format)
    await callback.message.edit_text("Выберите формат результата:", reply_markup=output_format_keyboard())
    await callback.answer()


@router.callback_query(ChartBuilderStates.choosing_sorting, F.data.startswith("cb:sort:"))
async def choose_sorting(callback: CallbackQuery, state: FSMContext) -> None:
    await _update_config(state, sorting=callback.data.rsplit(":", 1)[1])
    await state.set_state(ChartBuilderStates.choosing_output_format)
    await callback.message.edit_text("Выберите формат результата:", reply_markup=output_format_keyboard())
    await callback.answer()


@router.callback_query(ChartBuilderStates.choosing_output_format, F.data.startswith("cb:format:"))
async def choose_output_format(callback: CallbackQuery, state: FSMContext) -> None:
    await _update_config(state, output_format=callback.data.rsplit(":", 1)[1])
    config = _config(await state.get_data())
    await state.set_state(ChartBuilderStates.confirming_chart)
    await callback.message.edit_text(_config_summary(config), reply_markup=confirm_keyboard())
    await callback.answer()


@router.callback_query(ChartBuilderStates.confirming_chart, F.data.startswith("cb:confirm:"))
async def confirm_chart(callback: CallbackQuery, state: FSMContext) -> None:
    action = callback.data.rsplit(":", 1)[1]
    if action == "restart":
        await state.set_state(ChartBuilderStates.choosing_chart_type)
        await callback.message.edit_text("Выберите тип графика:", reply_markup=chart_type_keyboard())
        await callback.answer()
        return

    data = await state.get_data()
    config = _config(data)
    status = await callback.message.edit_text("Строю график...")
    try:
        analysis = await asyncio.to_thread(analyze_file, Path(data["file_path"]))
        output_path = await asyncio.to_thread(build_custom_chart, analysis["dataframe"], config, Path(data["job_dir"]) / "custom_charts")
        telegram_file_id, media_type = await _send_chart(callback.message, output_path)
        if callback.from_user:
            ChartHistoryRepository().add(
                callback.from_user.id,
                data.get("file_name", "file"),
                config,
                telegram_file_id=telegram_file_id,
                media_type=media_type,
            )
        built_charts = list(data.get("built_charts", []))
        built_charts.append({"path": str(output_path), "config": asdict(config)})
        await state.update_data(built_charts=built_charts)
        await state.set_state(ChartBuilderStates.finished)
        await callback.message.answer("Что дальше?", reply_markup=after_chart_keyboard())
    except ValueError as exc:
        await status.edit_text(f"Не удалось построить график:\n{exc}")
    except Exception:
        await status.edit_text("Не удалось построить график из-за внутренней ошибки.")
        raise
    await callback.answer()


@router.callback_query(ChartBuilderStates.finished, F.data.startswith("cb:after:"))
async def after_chart(callback: CallbackQuery, state: FSMContext) -> None:
    action = callback.data.rsplit(":", 1)[1]
    data = await state.get_data()
    if action == "again":
        await _reset_config(state)
        await state.set_state(ChartBuilderStates.choosing_chart_type)
        await callback.message.edit_text("Выберите тип следующего графика:", reply_markup=chart_type_keyboard())
    elif action == "file_menu":
        await _return_to_file_menu(callback, state)
    elif action == "new_file":
        shutil.rmtree(Path(data["job_dir"]), ignore_errors=True)
        await state.clear()
        await state.set_state(ChartBuilderStates.waiting_for_file)
        await callback.message.edit_text("Загрузите новый Excel или CSV файл.")
    elif action == "pdf":
        items = [
            (Path(item["path"]), ChartConfig(**item["config"]))
            for item in data.get("built_charts", [])
            if Path(item["path"]).suffix.lower() == ".png"
        ]
        if not items:
            await callback.answer("В PDF можно добавить только PNG-графики.", show_alert=True)
            return
        pdf_path = Path(data["job_dir"]) / "custom_charts_report.pdf"
        await asyncio.to_thread(build_custom_charts_pdf, items, pdf_path)
        await callback.message.answer_document(FSInputFile(pdf_path), caption="PDF с выбранными графиками готов.")
        await callback.message.answer("Что дальше?", reply_markup=after_chart_keyboard())
    else:
        shutil.rmtree(Path(data["job_dir"]), ignore_errors=True)
        await state.clear()
        await callback.message.edit_text("Готово. Главное меню можно открыть командой /start.")
    await callback.answer()


async def _go_back(callback: CallbackQuery, state: FSMContext) -> bool:
    current_state = await state.get_state()
    data = await state.get_data()
    config = _config(data)

    if current_state == ChartBuilderStates.choosing_chart_type.state:
        if data.get("return_to_file_menu"):
            await _return_to_file_menu(callback, state)
            return False
        await callback.answer("Это первый шаг настройки графика.", show_alert=True)
        return True

    if current_state == ChartBuilderStates.choosing_x_column.state:
        await _reset_config(state)
        await state.set_state(ChartBuilderStates.choosing_chart_type)
        await callback.message.edit_text("Выберите тип графика:", reply_markup=chart_type_keyboard())
        return False

    if current_state == ChartBuilderStates.choosing_y_column.state:
        if config.chart_type in {ChartType.HISTOGRAM, ChartType.BOXPLOT}:
            await state.set_state(ChartBuilderStates.choosing_chart_type)
            await callback.message.edit_text("Выберите тип графика:", reply_markup=chart_type_keyboard())
        else:
            await state.set_state(ChartBuilderStates.choosing_x_column)
            await callback.message.edit_text("Выберите колонку X:", reply_markup=columns_keyboard(data["columns"], "cb:x"))
        return False

    if current_state == ChartBuilderStates.choosing_multiple_y_columns.state:
        if config.chart_type == ChartType.HEATMAP:
            await state.set_state(ChartBuilderStates.choosing_chart_type)
            await callback.message.edit_text("Выберите тип графика:", reply_markup=chart_type_keyboard())
        else:
            await state.update_data(selected_y=[])
            await state.set_state(ChartBuilderStates.choosing_x_column)
            await callback.message.edit_text("Выберите колонку X:", reply_markup=columns_keyboard(data["columns"], "cb:x"))
        return False

    if current_state == ChartBuilderStates.choosing_aggregation.state:
        if config.chart_type in {ChartType.LINE, ChartType.AREA, ChartType.MULTI}:
            await state.set_state(ChartBuilderStates.choosing_multiple_y_columns)
            await callback.message.edit_text(
                "Выберите одну или несколько Y-колонок:",
                reply_markup=columns_keyboard(data["numeric_columns"], "cb:multi", done=True),
            )
        else:
            await state.set_state(ChartBuilderStates.choosing_y_column)
            await callback.message.edit_text("Выберите колонку Y:", reply_markup=columns_keyboard(data["numeric_columns"], "cb:y"))
        return False

    if current_state == ChartBuilderStates.choosing_top_n.state:
        await state.set_state(ChartBuilderStates.choosing_aggregation)
        await callback.message.edit_text("Выберите агрегацию:", reply_markup=aggregation_keyboard())
        return False

    if current_state == ChartBuilderStates.choosing_bins.state:
        await state.set_state(ChartBuilderStates.choosing_y_column)
        await callback.message.edit_text("Выберите числовую колонку:", reply_markup=columns_keyboard(data["numeric_columns"], "cb:y"))
        return False

    if current_state == ChartBuilderStates.choosing_hue.state:
        await state.set_state(ChartBuilderStates.choosing_y_column)
        await callback.message.edit_text("Выберите колонку Y:", reply_markup=columns_keyboard(data["numeric_columns"], "cb:y"))
        return False

    if current_state == ChartBuilderStates.choosing_size.state:
        await state.set_state(ChartBuilderStates.choosing_hue)
        await callback.message.edit_text(
            "Выберите цветовую группировку hue или пропустите:",
            reply_markup=columns_keyboard(data["columns"], "cb:hue", include_skip=True),
        )
        return False

    if current_state == ChartBuilderStates.choosing_sorting.state:
        if config.chart_type in {ChartType.BAR, ChartType.HORIZONTAL_BAR, ChartType.PIE}:
            await state.set_state(ChartBuilderStates.choosing_top_n)
            await callback.message.edit_text("Выберите Top N:", reply_markup=top_n_keyboard())
        else:
            await state.set_state(ChartBuilderStates.choosing_aggregation)
            await callback.message.edit_text("Выберите агрегацию:", reply_markup=aggregation_keyboard())
        return False

    if current_state == ChartBuilderStates.choosing_output_format.state:
        if config.chart_type == ChartType.HISTOGRAM:
            await state.set_state(ChartBuilderStates.choosing_bins)
            await callback.message.edit_text("Выберите количество bins:", reply_markup=bins_keyboard())
        elif config.chart_type == ChartType.BOXPLOT:
            await state.set_state(ChartBuilderStates.choosing_hue)
            await callback.message.edit_text(
                "Выберите группировку для boxplot или пропустите:",
                reply_markup=columns_keyboard(data["columns"], "cb:hue", include_skip=True),
            )
        elif config.chart_type == ChartType.SCATTER:
            await state.set_state(ChartBuilderStates.choosing_size)
            await callback.message.edit_text(
                "Выберите колонку размера точки или пропустите:",
                reply_markup=columns_keyboard(data["numeric_columns"], "cb:size", include_skip=True),
            )
        elif config.chart_type == ChartType.HEATMAP:
            await state.set_state(ChartBuilderStates.choosing_multiple_y_columns)
            await state.update_data(selection_mode="exclude_heatmap")
            await callback.message.edit_text(
                "Выберите колонки, которые нужно исключить, или нажмите «Готово».",
                reply_markup=columns_keyboard(data["numeric_columns"], "cb:multi", done=True),
            )
        else:
            await state.set_state(ChartBuilderStates.choosing_sorting)
            await callback.message.edit_text("Выберите сортировку:", reply_markup=sorting_keyboard(for_x=True))
        return False

    if current_state == ChartBuilderStates.confirming_chart.state:
        await state.set_state(ChartBuilderStates.choosing_output_format)
        await callback.message.edit_text("Выберите формат результата:", reply_markup=output_format_keyboard())
        return False

    await callback.answer("На этом шаге назад вернуться нельзя.", show_alert=True)
    return True


async def _return_to_file_menu(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(UploadStates.waiting_for_entry_choice)
    await state.update_data(
        file_path=data.get("file_path"),
        job_dir=data.get("job_dir"),
        file_name=data.get("file_name"),
        umap_path=data.get("umap_path"),
        umap_used_columns=data.get("umap_used_columns"),
        umap_sample_size=data.get("umap_sample_size"),
        umap_total_rows=data.get("umap_total_rows"),
        umap_sampled=data.get("umap_sampled"),
    )
    await callback.message.edit_text("Что еще сделать с этим датасетом?", reply_markup=analysis_entry_keyboard())


async def _send_chart(message: Message, output_path: Path) -> tuple[str | None, str | None]:
    if output_path.suffix.lower() != ".png":
        sent = await message.answer_document(FSInputFile(output_path), caption="PDF-график готов.")
        return (sent.document.file_id if sent.document else None, "document")
    sent = await message.answer_photo(FSInputFile(output_path), caption="График готов.")
    if sent.photo:
        return (sent.photo[-1].file_id, "photo")
    return (None, "photo")


async def _update_config(state: FSMContext, **updates: Any) -> None:
    data = await state.get_data()
    config = dict(data.get("config", {}))
    config.update(updates)
    await state.update_data(config=config)


async def _reset_config(state: FSMContext) -> None:
    await state.update_data(config={}, selected_y=[], excluded_columns=[])


def _config(data: dict[str, Any]) -> ChartConfig:
    config = dict(data.get("config", {}))
    if "chart_type" not in config:
        config["chart_type"] = ChartType.LINE.value
    return ChartConfig(**config)


def _column_from_callback(callback_data: str, columns: list[str]) -> str:
    index = int(callback_data.rsplit(":", 1)[1])
    return columns[index]


def _columns_text(columns: list[str]) -> str:
    lines = ["Колонки в файле:"]
    lines.extend(f"{index}. {column}" for index, column in enumerate(columns, start=1))
    return "\n".join(lines)


def _config_summary(config: ChartConfig) -> str:
    return (
        "Проверьте параметры графика:\n\n"
        f"Тип: {CHART_TYPE_TITLES.get(config.chart_type, config.chart_type)}\n"
        f"X: {config.x_column or '-'}\n"
        f"Y: {', '.join(config.y_columns) or '-'}\n"
        f"Агрегация: {config.aggregation or '-'}\n"
        f"Сортировка: {config.sorting or '-'}\n"
        f"Top N: {config.top_n or '-'}\n"
        f"Bins: {config.bins or '-'}\n"
        f"Hue: {config.hue or '-'}\n"
        f"Size: {config.size or '-'}\n"
        f"Формат: {config.output_format}"
    )

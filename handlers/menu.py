from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

from database.chart_history import ChartHistoryRepository
from database.table_history import TableHistoryRepository
from handlers.start import send_start_screen
from keyboards.chart_builder_keyboards import BOT_INFO_BUTTON, MY_CHARTS_BUTTON, MY_REPORTS_BUTTON, MY_TABLES_BUTTON
from storage.history import HistoryRepository


router = Router()


@router.message(F.text == MY_TABLES_BUTTON)
async def my_tables(message: Message) -> None:
    if not message.from_user:
        await message.answer("Не удалось определить пользователя.")
        return

    items = TableHistoryRepository().list_recent(message.from_user.id)
    if not items:
        await message.answer("Вы еще не загружали таблицы.")
        return

    sent_count = 0
    for item in items:
        if item.telegram_file_id:
            await message.answer_document(
                item.telegram_file_id,
                caption=f"{item.file_name}\nЗагружено: {item.created_at}",
            )
            sent_count += 1
        else:
            await message.answer(
                f"{item.file_name} ({item.created_at})\n"
                "Файл недоступен для повторной отправки: это старая запись без file_id."
            )

    if sent_count:
        await message.answer(f"Отправлено таблиц: {sent_count}.")


@router.message(F.text == MY_REPORTS_BUTTON)
async def my_reports(message: Message) -> None:
    if not message.from_user:
        await message.answer("Не удалось определить пользователя.")
        return

    items = HistoryRepository().list_recent(message.from_user.id, limit=10)
    if not items:
        await message.answer("У вас пока нет готовых отчетов.")
        return

    sent_count = 0
    for item in items:
        caption = f"{item.file_name} | {item.analysis_type}\n{item.created_at}\n{item.result_summary}"
        if item.report_file_id:
            await message.answer_document(item.report_file_id, caption=caption)
            sent_count += 1
        else:
            await message.answer(
                f"{caption}\nPDF недоступен для повторной отправки: это старая запись без file_id."
            )

    if sent_count:
        await message.answer(f"Отправлено отчетов: {sent_count}.")


@router.message(F.text == MY_CHARTS_BUTTON)
async def my_charts(message: Message) -> None:
    if not message.from_user:
        await message.answer("Не удалось определить пользователя.")
        return

    items = ChartHistoryRepository().list_recent(message.from_user.id)
    if not items:
        await message.answer("История графиков пока пустая.")
        return

    sent_count = 0
    for item in items:
        caption = (
            f"{item.file_name} | {item.chart_type} | {item.output_format}\n"
            f"{item.created_at}\n"
            f"X: {item.x_column or '-'} | Y: {item.y_columns or '-'} | agg: {item.aggregation or '-'}"
        )
        if item.telegram_file_id and item.media_type == "photo":
            await message.answer_photo(item.telegram_file_id, caption=caption)
            sent_count += 1
        elif item.telegram_file_id:
            await message.answer_document(item.telegram_file_id, caption=caption)
            sent_count += 1
        else:
            await message.answer(
                f"{caption}\nГрафик недоступен для повторной отправки: это старая запись без file_id."
            )

    if sent_count:
        await message.answer(f"Отправлено графиков: {sent_count}.")


@router.message(F.text == BOT_INFO_BUTTON)
async def home(message: Message) -> None:
    await send_start_screen(message)

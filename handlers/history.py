from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from storage.history import HistoryRepository


router = Router()


@router.message(Command("history"))
async def history_command(message: Message) -> None:
    if not message.from_user:
        await message.answer("Не удалось определить пользователя.")
        return

    items = HistoryRepository().list_recent(message.from_user.id)
    if not items:
        await message.answer("История анализов пока пуста.")
        return

    lines = ["Последние анализы:"]
    for item in items:
        lines.append(
            f"{item.created_at}\n"
            f"{item.file_name} | {item.analysis_type}\n"
            f"{item.result_summary}"
        )
    await message.answer("\n\n".join(lines))

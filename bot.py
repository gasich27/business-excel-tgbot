import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from handlers import chart_builder_handler, history, menu, ml_analysis_handler, start, upload


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    bot = Bot(token=settings.bot_token)
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_router(start.router)
    dispatcher.include_router(history.router)
    dispatcher.include_router(menu.router)
    dispatcher.include_router(chart_builder_handler.router)
    dispatcher.include_router(ml_analysis_handler.router)
    dispatcher.include_router(upload.router)

    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

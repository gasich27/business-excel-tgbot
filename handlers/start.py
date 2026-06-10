from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from keyboards.chart_builder_keyboards import main_menu_keyboard, upload_file_keyboard


router = Router()

START_DESCRIPTION = (
    "Excel Analyst Bot помогает анализировать Excel/CSV-файлы: строит EDA, бизнес-отчеты, "
    "графики, UMAP-preview, PCA/UMAP/t-SNE и кластеризацию.\n\n"
    "Чтобы начать, загрузите таблицу документом. После загрузки бот покажет UMAP-preview "
    "и предложит выбрать дальнейшее действие."
)


async def send_start_screen(message: Message) -> None:
    await message.answer("Главная", reply_markup=main_menu_keyboard())
    await message.answer(START_DESCRIPTION, reply_markup=upload_file_keyboard())


@router.message(CommandStart())
async def start_command(message: Message) -> None:
    await send_start_screen(message)

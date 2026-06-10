from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from visualization.chart_config import CHART_TYPE_TITLES, Aggregation, OutputFormat, Sorting


CHART_BUILDER_BUTTON = "\U0001f4c8 \u041a\u043e\u043d\u0441\u0442\u0440\u0443\u043a\u0442\u043e\u0440 \u0433\u0440\u0430\u0444\u0438\u043a\u043e\u0432"
MY_TABLES_BUTTON = "\U0001f4c4 \u041c\u043e\u0438 \u0442\u0430\u0431\u043b\u0438\u0446\u044b"
MY_REPORTS_BUTTON = "\U0001f4ca \u041c\u043e\u0438 \u043e\u0442\u0447\u0435\u0442\u044b"
MY_CHARTS_BUTTON = "\u041c\u043e\u0438 \u0433\u0440\u0430\u0444\u0438\u043a\u0438"
HOME_BUTTON = "\U0001f3e0 \u041d\u0430 \u0433\u043b\u0430\u0432\u043d\u0443\u044e"
BOT_INFO_BUTTON = HOME_BUTTON
UPLOAD_FILE_BUTTON = "\U0001f4ce \u0417\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c \u0444\u0430\u0439\u043b \u0434\u043b\u044f \u0430\u043d\u0430\u043b\u0438\u0437\u0430"


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=MY_TABLES_BUTTON), KeyboardButton(text=MY_REPORTS_BUTTON)],
            [KeyboardButton(text=MY_CHARTS_BUTTON), KeyboardButton(text=HOME_BUTTON)],
        ],
        resize_keyboard=True,
    )


def upload_file_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=UPLOAD_FILE_BUTTON, callback_data="upload:start")]
        ]
    )


def analysis_entry_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="\U0001f4ca \u0410\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438\u0435 \u0430\u043d\u0430\u043b\u0438\u0437\u044b",
                    callback_data="file:auto_analysis",
                )
            ],
            [
                InlineKeyboardButton(
                    text="\U0001f4c8 \u041a\u043e\u043d\u0441\u0442\u0440\u0443\u043a\u0442\u043e\u0440 \u0433\u0440\u0430\u0444\u0438\u043a\u043e\u0432",
                    callback_data="file:chart_builder",
                )
            ],
            [InlineKeyboardButton(text="\U0001f9ea PCA / UMAP / t-SNE", callback_data="file:embedding_comparison")],
            [InlineKeyboardButton(text="\U0001f9e9 \u041a\u043b\u0430\u0441\u0442\u0435\u0440\u0438\u0437\u0430\u0446\u0438\u044f", callback_data="file:clustering")],
            [InlineKeyboardButton(text="\U0001f39e PowerPoint-\u043e\u0442\u0447\u0435\u0442", callback_data="file:pptx_report")],
            [
                InlineKeyboardButton(text="\U0001f4e4 \u0417\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c \u0434\u0440\u0443\u0433\u043e\u0439 \u0444\u0430\u0439\u043b", callback_data="file:upload_new"),
                InlineKeyboardButton(text="\U0001f3e0 \u0413\u043b\u0430\u0432\u043d\u043e\u0435 \u043c\u0435\u043d\u044e", callback_data="file:main_menu"),
            ],
        ]
    )


def chart_type_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=title, callback_data=f"cb:type:{chart_type}")]
        for chart_type, title in CHART_TYPE_TITLES.items()
    ]
    rows.append([InlineKeyboardButton(text="\u2b05\ufe0f \u041d\u0430\u0437\u0430\u0434", callback_data="cb:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def columns_keyboard(columns: list[str], prefix: str, include_skip: bool = False, done: bool = False) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=column, callback_data=f"{prefix}:{index}")] for index, column in enumerate(columns)]
    if include_skip:
        rows.append([InlineKeyboardButton(text="\u041f\u0440\u043e\u043f\u0443\u0441\u0442\u0438\u0442\u044c", callback_data=f"{prefix}:skip")])
    if done:
        rows.append([InlineKeyboardButton(text="\u0413\u043e\u0442\u043e\u0432\u043e", callback_data=f"{prefix}:done")])
    rows.append([InlineKeyboardButton(text="\u2b05\ufe0f \u041d\u0430\u0437\u0430\u0434", callback_data="cb:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def aggregation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=item.value, callback_data=f"cb:agg:{item.value}")]
            for item in Aggregation
        ]
        + [[InlineKeyboardButton(text="\u2b05\ufe0f \u041d\u0430\u0437\u0430\u0434", callback_data="cb:back")]]
    )


def sorting_keyboard(for_x: bool = False) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="\u0411\u0435\u0437 \u0441\u043e\u0440\u0442\u0438\u0440\u043e\u0432\u043a\u0438", callback_data=f"cb:sort:{Sorting.NONE.value}")]]
    if for_x:
        rows.append([InlineKeyboardButton(text="\u0421\u043e\u0440\u0442\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u043f\u043e X", callback_data=f"cb:sort:{Sorting.X_ASC.value}")])
    rows.extend(
        [
            [InlineKeyboardButton(text="\u041f\u043e \u0432\u043e\u0437\u0440\u0430\u0441\u0442\u0430\u043d\u0438\u044e", callback_data=f"cb:sort:{Sorting.ASC.value}")],
            [InlineKeyboardButton(text="\u041f\u043e \u0443\u0431\u044b\u0432\u0430\u043d\u0438\u044e", callback_data=f"cb:sort:{Sorting.DESC.value}")],
        ]
    )
    rows.append([InlineKeyboardButton(text="\u2b05\ufe0f \u041d\u0430\u0437\u0430\u0434", callback_data="cb:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def output_format_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="PNG", callback_data=f"cb:format:{OutputFormat.PNG.value}"),
                InlineKeyboardButton(text="PDF", callback_data=f"cb:format:{OutputFormat.PDF.value}"),
            ],
            [InlineKeyboardButton(text="\u2b05\ufe0f \u041d\u0430\u0437\u0430\u0434", callback_data="cb:back")],
        ]
    )


def top_n_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="5", callback_data="cb:top:5"),
                InlineKeyboardButton(text="10", callback_data="cb:top:10"),
                InlineKeyboardButton(text="20", callback_data="cb:top:20"),
            ],
            [InlineKeyboardButton(text="\u0411\u0435\u0437 \u043e\u0433\u0440\u0430\u043d\u0438\u0447\u0435\u043d\u0438\u044f", callback_data="cb:top:0")],
            [InlineKeyboardButton(text="\u2b05\ufe0f \u041d\u0430\u0437\u0430\u0434", callback_data="cb:back")],
        ]
    )


def bins_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="10", callback_data="cb:bins:10"),
                InlineKeyboardButton(text="20", callback_data="cb:bins:20"),
                InlineKeyboardButton(text="30", callback_data="cb:bins:30"),
            ],
            [InlineKeyboardButton(text="50", callback_data="cb:bins:50")],
            [InlineKeyboardButton(text="\u2b05\ufe0f \u041d\u0430\u0437\u0430\u0434", callback_data="cb:back")],
        ]
    )


def combo_type_keyboard(target: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="bar", callback_data=f"cb:{target}:bar"),
                InlineKeyboardButton(text="line", callback_data=f"cb:{target}:line"),
            ],
            [InlineKeyboardButton(text="\u2b05\ufe0f \u041d\u0430\u0437\u0430\u0434", callback_data="cb:back")],
        ]
    )


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="\u041f\u043e\u0441\u0442\u0440\u043e\u0438\u0442\u044c \u0433\u0440\u0430\u0444\u0438\u043a", callback_data="cb:confirm:build")],
            [InlineKeyboardButton(text="\u041d\u0430\u0447\u0430\u0442\u044c \u0437\u0430\u043d\u043e\u0432\u043e", callback_data="cb:confirm:restart")],
            [InlineKeyboardButton(text="\u2b05\ufe0f \u041d\u0430\u0437\u0430\u0434", callback_data="cb:back")],
        ]
    )


def after_chart_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="\u041f\u043e\u0441\u0442\u0440\u043e\u0438\u0442\u044c \u0435\u0449\u0435 \u043f\u043e \u044d\u0442\u043e\u043c\u0443 \u0444\u0430\u0439\u043b\u0443", callback_data="cb:after:again")],
            [InlineKeyboardButton(text="\u0412\u0435\u0440\u043d\u0443\u0442\u044c\u0441\u044f \u043a \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u044f\u043c \u043f\u043e \u0444\u0430\u0439\u043b\u0443", callback_data="cb:after:file_menu")],
            [InlineKeyboardButton(text="\u0417\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c \u043d\u043e\u0432\u044b\u0439 \u0444\u0430\u0439\u043b", callback_data="cb:after:new_file")],
            [InlineKeyboardButton(text="\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0433\u0440\u0430\u0444\u0438\u043a\u0438 \u0432 PDF", callback_data="cb:after:pdf")],
            [InlineKeyboardButton(text="\u0413\u043b\u0430\u0432\u043d\u043e\u0435 \u043c\u0435\u043d\u044e", callback_data="cb:after:menu")],
        ]
    )

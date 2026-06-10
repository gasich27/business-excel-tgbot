from aiogram.fsm.state import State, StatesGroup


class ChartBuilderStates(StatesGroup):
    waiting_for_file = State()
    choosing_chart_type = State()
    choosing_x_column = State()
    choosing_y_column = State()
    choosing_multiple_y_columns = State()
    choosing_aggregation = State()
    choosing_sorting = State()
    choosing_top_n = State()
    choosing_bins = State()
    choosing_hue = State()
    choosing_size = State()
    choosing_output_format = State()
    confirming_chart = State()
    finished = State()

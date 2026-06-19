# Excel Analyst Bot

Telegram-бот для анализа таблиц Excel и CSV. Бот строит EDA-отчёты,
бизнес-метрики и графики, выполняет кластеризацию и снижение размерности,
а также сохраняет историю результатов в локальных SQLite-базах.

## Возможности

- загрузка файлов `.xlsx`, `.xls` и `.csv`;
- автоматический разведочный анализ данных (EDA);
- анализ продаж, остатков, клиентов и данных маркетплейсов;
- сравнение двух таблиц;
- поиск аномалий и прогнозирование;
- конструктор графиков с экспортом в PNG и PDF;
- PCA, UMAP, t-SNE, KMeans и DBSCAN;
- генерация PDF- и PowerPoint-отчётов;
- история таблиц, отчётов и графиков;
- отдельный Streamlit-dashboard.

## Требования

- Python 3.11 или 3.12;
- токен Telegram-бота от BotFather.

## Быстрый запуск

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

$env:BOT_TOKEN="ваш_токен"
python bot.py
```

После запуска отправьте боту команду `/start`, затем загрузите таблицу
документом. Команда `/history` показывает последние результаты анализа,
а `/charts` открывает конструктор графиков.

## Dashboard

Streamlit-приложение запускается отдельно:

```powershell
.\.venv\Scripts\Activate.ps1
streamlit run dashboard/app.py
```

## Переменные окружения

| Переменная | Обязательна | Значение по умолчанию | Назначение |
| --- | --- | --- | --- |
| `BOT_TOKEN` | да | нет | Токен Telegram-бота |
| `MAX_FILE_SIZE_MB` | нет | `25` | Максимальный размер загружаемого файла |
| `TEMP_DIR` | нет | `temp` | Рабочий каталог временных файлов |
| `IMAGE_DIR` | нет | `images` | Каталог создаваемых изображений |

Каталоги создаются автоматически при запуске бота.

## Docker

```powershell
docker build -t excel-analyst-bot .
docker run --rm -e BOT_TOKEN="ваш_токен" excel-analyst-bot
```

SQLite-базы создаются в рабочем каталоге контейнера. Для сохранения истории
между перезапусками подключите постоянный Docker volume к `/app`.

## Тесты

```powershell
$env:BOT_TOKEN="test-token"
pytest -q
```

Тесты покрывают конструктор графиков, подготовку ML-данных, кластеризацию,
UMAP, сравнение embeddings и генерацию PowerPoint-отчётов.

## Структура проекта

```text
.
|-- analysis/       # EDA, UMAP, embeddings и кластеризация
|-- business/       # бизнес-анализ, прогнозы и аномалии
|-- dashboard/      # Streamlit-интерфейс
|-- database/       # история таблиц, графиков и UMAP
|-- handlers/       # Telegram-обработчики
|-- keyboards/      # клавиатуры Telegram
|-- reports/        # PDF- и PowerPoint-отчёты
|-- states/         # FSM-состояния aiogram
|-- storage/        # история аналитических отчётов
|-- tests/          # автоматические тесты
|-- utils/          # вспомогательные функции и ML-кэш
|-- visualization/  # построение и проверка графиков
|-- bot.py          # точка входа Telegram-бота
|-- config.py       # настройки из переменных окружения
`-- requirements.txt
```

## Локальные данные

Во время работы проект создаёт:

- `temp/`, `images/` и `outputs/` с временными результатами;
- `*.sqlite3` с локальной историей;
- Python- и pytest-кэши.

Эти файлы исключены из Git и могут быть удалены без изменения исходного кода.
Удаление SQLite-баз сбрасывает только сохранённую историю пользователей.

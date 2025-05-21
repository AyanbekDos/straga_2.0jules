# CCE — Content Chunk Enricher

📦 ETL-пайплайн, превращающий список URL-ов в обогащённые чанки текста для RAG.

## Структура проекта

- `data/` — входные и промежуточные файлы
- `etl/` — скрипты для каждого шага (extract, clean, chunk, enrich)
- `db/` — база данных
- `scripts/` — управление пайплайном

## Запуск пайплайна

```bash
python scripts/update_pipeline.py


# Пайплайн извлечения, очистки и разбиения текстов

Репозиторий содержит набор Python-скриптов, организованных в поэтапный конвейер:

1. **Дедупликация ссылок** (`dedupe_links.py`)
2. **Извлечение метаданных и «сырое» HTML** (`extract_meta_with_progress.py`)
3. **Очистка HTML → чистый текст** (`clean_text_extractor_with_progress.py`)
4. **Семантическое разбиение на чанки** (`chunker.py`)
5. **(Дальнейшие этапы — обогащение, векторизация, валидация)**

---

## Структура репозитория

```
├── links.txt                      # Исходный список URL (одна ссылка в строке)
├── clean_links.txt                # После дедупликации
├── metadata.jsonl                 # После extract_meta_with_progress.py (сырой HTML + базовые метаданные)
├── metadata_with_clean.jsonl      # После clean_text_extractor_with_progress.py (добавлено поле clean_text)
├── chunks.jsonl                   # После chunker.py (семантические чанки с метаданными)
├── dedupe_links.py                # Скрипт удаления дубликатов
├── extract_meta_with_progress.py  # Скрипт парсинга метаданных + raw_html с прогрессом
├── clean_text_extractor_with_progress.py  # Скрипт очистки HTML → clean_text с прогрессом
├── chunker.py                     # Скрипт для семантического разбиения на чанки
└── README.md                      # Этот файл
```

---

## 1. Дедупликация ссылок

**Скрипт:** `dedupe_links.py`

- **Что делает:** убирает повторы и пустые строки из `links.txt`.
- **Запуск:**
  ```bash
  pip install argparse
  python dedupe_links.py \
    --input links.txt \
    --output clean_links.txt
  ```
- **Результат:** файл `clean_links.txt` с уникальными URL.

---

## 2. Извлечение метаданных и raw HTML

**Скрипт:** `extract_meta_with_progress.py`

- **Что делает:** по списку `clean_links.txt` скачивает страницы,
  парсит метаданные (url, title, date, author, description, keywords, language)
  и сохраняет сырой HTML.
- **Запуск:**
  ```bash
  pip install aiohttp trafilatura beautifulsoup4 python-dateutil langdetect selenium playwright
  python extract_meta_with_progress.py \
    --input clean_links.txt \
    --output metadata.jsonl
  ```
- **Результат:** файл `metadata.jsonl`, каждая строка — JSON с полями:
  ```json
  {
    "url": "...",
    "title": "...",
    "date": "...",
    "author": "...",
    "description": "...",
    "keywords": "...",
    "language": "...",
    "raw_html": "<html>…</html>"
  }
  ```

---

## 3. Очистка HTML → получение чистого текста

**Скрипт:** `clean_text_extractor_with_progress.py`

- **Что делает:** читает `metadata.jsonl`, извлекает из `raw_html`
  чистый текст (`clean_text`) через Trafilatura, отображает прогресс в % и логирует ошибки.
- **Запуск:**
  ```bash
  pip install trafilatura
  python clean_text_extractor_with_progress.py \
    --input metadata.jsonl \
    --output metadata_with_clean.jsonl
  ```
- **Результат:** файл `metadata_with_clean.jsonl`, каждая строка — JSON:
  ```json
  {
    "url": "...",
    "title": "...",
    "date": "...",
    "author": "...",
    "description": "...",
    "keywords": "...",
    "language": "...",
    "clean_text": "Текст статьи без HTML",
    "raw_html": "<html>…</html>"
  }
  ```

---

## 4. Семантическое разбиение на чанки

**Скрипт:** `chunker.py`

- **Что делает:** читает `metadata_with_clean.jsonl`, семантически делит `clean_text`
  на предложения (NLTK), группирует их в чанки по токенам (tiktoken).
- **Параметры CLI:**
  - `--input` (по умолчанию `metadata_with_clean.jsonl`)
  - `--output` (по умолчанию `chunks.jsonl`)
  - `--chunk_size N` (максимум N токенов на чанк, default=300)
  - `--overlap M` (перекрытие M токенов между соседними чанками, default=0)
  - `--model` (модель для tiktoken, default=`gpt-3.5-turbo`)
  - `--verbose` (подробный лог)
- **Запуск пример:**
  ```bash
  pip install nltk tiktoken tqdm
  python chunker.py \
    --input metadata_with_clean.jsonl \
    --output chunks.jsonl \
    --chunk_size 500 \
    --overlap 30 \
    --verbose
  ```
- **Результат:** файл `chunks.jsonl`, где каждая строка — JSON с полями:
  ```json
  {
    "url": "…",
    "title": "…",
    "date": "…",
    "author": "…",
    "description": "…",
    "keywords": "…",
    "language": "…",
    "chunk_id": 0,
    "chunk_text": "Текст чанка (до 500 токенов, с перекрытием)"
  }
  ```

---

## 5. Дальнейшие шаги

- **Обогащение чанков** через GPT (RAG-метаданные, summary, entities и т.д.)
- **Векторизация** и загрузка в хранилище (Pinecone, Supabase)
- **Валидация** и отчёты об ошибках
- **Интеграция** в n8n, Telegram-бот или веб-интерфейс

---

> **Совет:** храните промежуточные файлы и логи ошибок (`errors.log`), чтобы быстро перезапустить только проблемные этапы, не обрабатывая заново весь пайплайн.

---

**Удачи в работе!**

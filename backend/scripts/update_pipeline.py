"""update_pipeline.py

Инкрементально обновляет базу CCE.

Добавлено:
* Явный список шагов со счётчиком («Step 1/5 …»), чтобы было видно, где скрипт находится.
* Если новых URL нет — выводит INFO‑сообщение и прерывает работу **до** обогащения.

Запуск:
    python update_pipeline.py                 # стандартные файлы
    python update_pipeline.py -n links2.txt   # кастомный файл новых ссылок
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List

# ──────────────────────────── Константы ────────────────────────────────
DEFAULT_NEW_FILE   = "new_links.txt"
DEFAULT_CLEAN_FILE = "clean_links_unique.txt"
DEFAULT_TMP_FILE   = "new_links_unique.txt"

EXTRACT = "extract.py"
CLEAN   = "clean_text_extractor.py"
CHUNK   = "chunker.py"
DEDUPER = "deduper.py"          # optional
ENRICH  = "enricher.py"

CHUNK_SIZE = 500
OVERLAP    = 30
DEDUP_THRESHOLD = 0.9            # None → пропускаем шаг дедупа

# ──────────────────────────── Вспомогательные утилиты ─────────────────

def run(cmd: List[str | Path]) -> None:
    """Запускает внешнюю команду и стримит вывод в лог.
    Принимает список str/Path, конвертирует в str для subprocess.
    """
    cmd_str = [str(c) for c in cmd]
    logging.info("$ %s", " ".join(cmd_str))
    print(f"\n🚀 Запускаем команду: {' '.join(cmd_str)}")

    proc = subprocess.Popen(
        cmd_str,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding='utf-8',
        errors='replace'
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip()
        logging.debug(line)
        print(f"  {line}")
    proc.wait()
    if proc.returncode != 0:
        print(f"❌ Ошибка выполнения команды (код {proc.returncode})")
        raise RuntimeError(f"Command failed: {' '.join(cmd_str)} → {proc.returncode}")
    print("✅ Команда выполнена успешно\n")


def diff_links(new_path: Path, clean_path: Path, tmp_path: Path) -> int:
    """Сохраняет в tmp_path только те URL, которых нет в clean_path.
    Если clean_path отсутствует – считаем, что база пуста.
    """
    if clean_path.exists():
        clean = {u.strip() for u in clean_path.read_text(encoding="utf-8").splitlines() if u.strip()}
    else:
        logging.warning("%s not found; treating as empty master list", clean_path)
        clean = set()
    added = 0
    with new_path.open("r", encoding="utf-8") as src, tmp_path.open("w", encoding="utf-8") as dst:
        for url in src:
            url = url.strip()
            if url and url not in clean:
                dst.write(url + "\n"); added += 1
    return added


def append_file(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    with src.open("rb") as s, dst.open("ab") as d:
        shutil.copyfileobj(s, d)

# ──────────────────────────── Основной скрипт ─────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Incremental update of CCE pipeline")
    parser.add_argument("-n", "--new",   default=DEFAULT_NEW_FILE,   help="file with raw new links")
    parser.add_argument("-c", "--clean", default=DEFAULT_CLEAN_FILE, help="master unique links list")
    parser.add_argument("-q", "--quiet", action="store_true", help="suppress INFO logs, show only WARNING")
    parser.add_argument("--skip-dedupe",  action="store_true", help="skip semantic dedupe step even if available")
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING if args.quiet else logging.INFO,
                        format="%(levelname)s: %(message)s")

    print("\n📋 Начинаем обновление базы CCE")
    print("=" * 50)

    root = Path.cwd()
    new_path, clean_path, tmp_path = root / args.new, root / args.clean, root / DEFAULT_TMP_FILE

    if not new_path.exists():
        print(f"❌ Файл {new_path} не найден")
        logging.critical("File %s not found", new_path); sys.exit(1)

    print(f"\n🔍 Проверяем новые URL из {new_path}")
    added = diff_links(new_path, clean_path, tmp_path)
    print(f"📊 Найдено {added} новых URL")

    # ── Early exit ────────────────────────────────────────────────────
    if added == 0:
        print("\n✨ Нет новых URL - завершаем работу")
        logging.info("No new links → pipeline finished BEFORE enrichment ✋")
        return

    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    meta        = root / f"meta_{ts}.jsonl"
    meta_clean  = root / f"meta_clean_{ts}.jsonl"
    chunks      = root / f"chunks_{ts}.jsonl"
    enriched    = root / f"enriched_{ts}.jsonl"

    step = 1; total = 5 + (0 if args.skip_dedupe else 1)

    # Step 1: extract ---------------------------------------------------
    print(f"\n📝 Шаг {step}/{total}: Извлечение метаданных")
    print("-" * 50)
    run([sys.executable, EXTRACT, "--input", tmp_path, "--output", meta])

    # Step 2: clean -----------------------------------------------------
    print(f"\n🧹 Шаг {step}/{total}: Очистка текста")
    print("-" * 50)
    run([sys.executable, CLEAN, "--input", meta, "--output", meta_clean])

    # Step 3: chunk -----------------------------------------------------
    print(f"\n✂️ Шаг {step}/{total}: Разбиение на чанки")
    print("-" * 50)
    run([sys.executable, CHUNK,
         "--input", meta_clean,
         "--output", chunks,
         "--chunk_size", str(CHUNK_SIZE),
         "--overlap", str(OVERLAP)])

    # Step 4: dedupe (optional) ----------------------------------------
    chunks_to_enrich = chunks
    if not args.skip_dedupe and Path(DEDUPER).exists() and DEDUP_THRESHOLD:
        print(f"\n🔄 Шаг {step}/{total}: Семантическая дедупликация")
        print("-" * 50)
        dedup_chunks = root / f"chunks_dedup_{ts}.jsonl"
        run([sys.executable, DEDUPER,
             "-i", chunks,
             "-o", dedup_chunks,
             "-t", str(DEDUP_THRESHOLD)])
        chunks_to_enrich = dedup_chunks
    else:
        print("\n⏩ Пропускаем шаг дедупликации")

    # Step 5: enrich ----------------------------------------------------
    print(f"\n✨ Шаг {step}/{total}: Обогащение данных")
    print("-" * 50)
    run([sys.executable, ENRICH, "--input", chunks_to_enrich, "--output", enriched])

    # Step 6: append to master -----------------------------------------
    print(f"\n💾 Шаг {step}/{total}: Добавление в основную базу")
    print("-" * 50)
    append_file(tmp_path,          clean_path)
    append_file(chunks_to_enrich,  root / "chunks.jsonl")
    append_file(enriched,          root / "enriched_chunks.jsonl")

    print("\n🎉 Обновление базы завершено успешно!")
    logging.info("Pipeline finished ✅. Master files updated.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.critical("Fatal: %s", e, exc_info=True)
        sys.exit(1)

from __future__ import annotations

import hashlib
import pickle
import time
from pathlib import Path
from typing import Any


CACHE_DIR = Path("outputs/ml_cache")


def get_cache_key(file_path: str, analysis_type: str) -> str:
    path = Path(file_path)
    modified = path.stat().st_mtime if path.exists() else 0
    raw = f"{path.resolve()}::{modified}::{analysis_type}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_cached_result(cache_key: str) -> Any | None:
    path = CACHE_DIR / f"{cache_key}.pkl"
    if not path.exists():
        return None
    with path.open("rb") as file:
        return pickle.load(file)


def save_cached_result(cache_key: str, result) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with (CACHE_DIR / f"{cache_key}.pkl").open("wb") as file:
        pickle.dump(result, file)


def clear_old_cache(days: int = 3) -> None:
    if not CACHE_DIR.exists():
        return
    threshold = time.time() - days * 24 * 60 * 60
    for path in CACHE_DIR.glob("*.pkl"):
        if path.stat().st_mtime < threshold:
            path.unlink(missing_ok=True)

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    bot_token: str
    max_file_size_mb: int
    temp_dir: Path
    image_dir: Path


def _build_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Set BOT_TOKEN environment variable before starting the bot.")

    temp_dir = Path(os.getenv("TEMP_DIR", "temp"))
    image_dir = Path(os.getenv("IMAGE_DIR", "images"))
    temp_dir.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)

    return Settings(
        bot_token=token,
        max_file_size_mb=int(os.getenv("MAX_FILE_SIZE_MB", "25")),
        temp_dir=temp_dir,
        image_dir=image_dir,
    )


settings = _build_settings()

import logging
from pathlib import Path


def set_logger(logger_name: str) -> logging.Logger:

    logger = logging.getLogger(logger_name)
    logger.setLevel(level=logging.INFO)

    log_dir = Path("logs")
    handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / f"{logger_name}.log",
        encoding="utf-8",
        maxBytes=32 * 1024 * 1024,  # 32 MiB
        backupCount=5,  # Rotate through 5 files
    )

    dt_fmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(
        "[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

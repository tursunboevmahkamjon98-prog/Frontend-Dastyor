import logging
import re
import sys
from datetime import datetime
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

class RedactingFormatter(logging.Formatter):
    def __init__(self, *args, original=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.original = original

    def format(self, record):
        rendered = self.original.format(record) if self.original else super().format(record)
        try:
            from app.config import get_settings
            settings = get_settings()
            for name in type(settings).model_fields:
                if any(part in name for part in ("TOKEN", "SECRET", "PASSWORD", "API_KEY")):
                    value = getattr(settings, name, None)
                    if isinstance(value, str) and value:
                        rendered = rendered.replace(value, "[REDACTED]")
        except Exception:
            pass
        rendered = re.sub(r"[0-9]+:[A-Za-z0-9_-]{30,}", "[BOT_TOKEN]", rendered)
        return re.sub(r"(postgres(?:ql)?(?:\+\w+)?://)[^\s/@]+:[^\s/@]+@", r"\1[REDACTED]@", rendered)


formatter = RedactingFormatter(LOG_FORMAT, DATE_FORMAT)


def install_secret_redaction():
    loggers = [logging.getLogger()] + [item for item in logging.root.manager.loggerDict.values()
                                      if isinstance(item, logging.Logger)]
    for logger in loggers:
        for handler in logger.handlers:
            if not isinstance(handler.formatter, RedactingFormatter):
                handler.setFormatter(RedactingFormatter(original=handler.formatter or logging.Formatter()))
    for name in ("httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

file_handler = logging.FileHandler(
    LOG_DIR / f"teachai_{datetime.now().strftime('%Y%m%d')}.log",
    encoding="utf-8"
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

error_handler = logging.FileHandler(
    LOG_DIR / f"errors_{datetime.now().strftime('%Y%m%d')}.log",
    encoding="utf-8"
)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(formatter)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    logger.handlers.clear()

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)

    logger.propagate = False

    return logger


logger = get_logger("teachai")

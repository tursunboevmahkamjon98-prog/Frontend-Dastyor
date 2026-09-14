import logging
import sys
from datetime import datetime
from pathlib import Path

# Make the console able to print the languages this product is FOR.
#
# On Windows a non-redirected console defaults to the system ANSI codepage
# (cp1251 here), which has no Tajik letters — ҳ ҷ ғ қ ӯ ӣ are all absent.
# Anything writing them to stdout therefore raises UnicodeEncodeError.
#
# That was not a cosmetic problem. A teacher generating a lesson on
# "Реша ва вазифаҳои он" got "AI xatolik: generatsiya bajarilmadi" and no
# material at all: routers/materials.py logged the topic with a plain
# print(), the print raised on the ҳ, and the exception took the whole
# request down before a single material was made. Every Tajik topic
# containing one of those six letters failed the same way — on the
# product's primary audience.
#
# Reconfiguring here rather than in main.py because every module that
# prints or logs imports this one, so the fix is in place before the
# first line of output. errors="replace" so a stream that still cannot
# encode something degrades to "?" instead of raising: logging must never
# be the reason a request fails.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        # Not a TextIOWrapper (already wrapped, redirected to a pipe, or
        # replaced by the host) — nothing to do, and nothing worth
        # crashing over at import time.
        pass

# Create logs directory
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Configure logging format
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Create formatters
formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# File handler for all logs
file_handler = logging.FileHandler(
    LOG_DIR / f"teachai_{datetime.now().strftime('%Y%m%d')}.log",
    encoding="utf-8"
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# File handler for errors only
error_handler = logging.FileHandler(
    LOG_DIR / f"errors_{datetime.now().strftime('%Y%m%d')}.log",
    encoding="utf-8"
)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(formatter)


def get_logger(name: str) -> logging.Logger:
    """Get configured logger instance"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


# Create default logger
logger = get_logger("teachai")

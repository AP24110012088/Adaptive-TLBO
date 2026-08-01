import logging
import sys
from config import LOG_DIR

def configure_logging(verbose=False):
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("adaptive_tlbo")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    # Log file
    file_handler = logging.FileHandler(
        LOG_DIR / "experiment.log",
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Terminal output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
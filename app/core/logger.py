import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOG_FILE = BASE_DIR / "logs/app.log"

def setup_logger():
    app_logger = logging.getLogger("ReceiptsHub")
    app_logger.setLevel(logging.INFO)

    # Format: Date - Name - Level - Message
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    app_logger.addHandler(console_handler)

    # Rotating File Handler (Max 5MB, keep 3 backup files)
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    app_logger.addHandler(file_handler)

    return app_logger

logger = setup_logger()
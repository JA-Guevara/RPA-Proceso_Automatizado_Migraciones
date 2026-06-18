import logging
from logging.handlers import RotatingFileHandler
import os

LOG_DIR = os.path.join("storage", "logs")
SERVER_LOG_PATH = os.path.join(LOG_DIR, "server.log")

MAX_LOG_SIZE = 90 * 1024 * 1024
BACKUP_COUNT = 3

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL = logging.INFO

class UTF8RotatingFileHandler(RotatingFileHandler):
    def _open(self):
        return open(self.baseFilename, self.mode, encoding="utf-8")

def setup_logging():
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    logger = logging.getLogger()
    logger.setLevel(LOG_LEVEL)

    if getattr(logger, "_configured", False):
        return

    formatter = logging.Formatter(LOG_FORMAT)

    file_handler = UTF8RotatingFileHandler(
        SERVER_LOG_PATH,
        maxBytes=MAX_LOG_SIZE,
        backupCount=BACKUP_COUNT,
    )
    file_handler.setLevel(LOG_LEVEL)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_LEVEL)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger._configured = True

    logger.info("📝 Logger inicializado correctamente")



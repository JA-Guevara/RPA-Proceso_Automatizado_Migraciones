import logging
from logging.handlers import RotatingFileHandler
import os

LOG_DIR = os.path.join('storage', 'logs')
SERVER_LOG_PATH = os.path.join(LOG_DIR, 'server.log')
MAX_LOG_SIZE = 90 * 1024 * 1024  # 90 MB
BACKUP_COUNT = 3
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = logging.INFO

class UTF8RotatingFileHandler(RotatingFileHandler):
    def _open(self):
        return open(self.baseFilename, self.mode, encoding='utf-8')

def setup_logging():
    # Crear el directorio de logs si no existe
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    # Configuración del logger principal
    logger = logging.getLogger()
    logger.setLevel(LOG_LEVEL)

    # Configuración del handler para el archivo de logs
    handler = UTF8RotatingFileHandler(
        SERVER_LOG_PATH,
        maxBytes=MAX_LOG_SIZE,
        backupCount=BACKUP_COUNT
    )
    handler.setLevel(LOG_LEVEL)
    formatter = logging.Formatter(LOG_FORMAT)
    handler.setFormatter(formatter)

    # Añadir el handler al logger principal
    logger.addHandler(handler)


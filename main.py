from shared.logger.logger_config import setup_logging
from task.manager import TaskManagerMigracion
import logging
import signal
import sys

setup_logging()
logger = logging.getLogger(__name__)

def salir_gracioso(sig, frame):
    print("🛑 Ejecución interrumpida por el usuario (Ctrl+C). Cerrando el proceso...")
    sys.exit(0)

signal.signal(signal.SIGINT, salir_gracioso)

if __name__ == "__main__":
    print("🟢 Iniciando ejecución del Task Manager Desktop...")
    try:
        TaskManagerMigracion().ejecutar()
    except Exception as e:
        print(f"❌ Error inesperado en el ciclo principal: {e}")


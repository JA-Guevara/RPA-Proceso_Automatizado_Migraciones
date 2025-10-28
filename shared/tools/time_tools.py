import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class TimeTools:
    @staticmethod
    def marcar_hora_inicio(contexto: dict, clase: str, logger: logging.Logger):
        """Marca la hora de inicio de un módulo y la guarda en el contexto."""
        clave = f"fecha_hora_inicio_{clase.lower()}"
        contexto[clave] = datetime.now()
        logger.info(f"⏱️ Inicio de {clase} registrado en {clave}")

    @staticmethod
    def marcar_hora_fin(contexto: dict, clase: str, logger: logging.Logger):
        """Marca la hora de fin de un módulo y la guarda en el contexto."""
        clave = f"fecha_hora_fin_{clase.lower()}"
        contexto[clave] = datetime.now()
        logger.info(f"⏱️ Fin de {clase} registrado en {clave}")

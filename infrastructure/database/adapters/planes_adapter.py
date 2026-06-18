import logging

from config.config import EnvConfig
from infrastructure.database.database import SessionLocal
from infrastructure.database.repositories.plan_repository import PlanRepository

logger = logging.getLogger(__name__)


class PlanesSQLAdapter:
    def __init__(self):
        self.tabla = EnvConfig.BOT_TABLA_PLANES
        self.repository = PlanRepository()

    def es_plan_valido(self, id_tipo_lista, nombre_plan: str, tipo: str) -> bool:
        try:
            with SessionLocal() as db:
                return self.repository.es_plan_valido(db, id_tipo_lista, nombre_plan, tipo)
        except Exception as e:
            logger.error(f"❌ Error validando plan '{nombre_plan}' (tipo_lista={id_tipo_lista}, tipo={tipo}): {e}", exc_info=True)
            return False

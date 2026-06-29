import logging

from config.config import EnvConfig
from infrastructure.database.database import SessionLocal
from infrastructure.database.repositories.plan_repository import (
    DiagnosticoPlan,
    PlanRepository,
)

logger = logging.getLogger(__name__)


class PlanesSQLAdapter:

    def __init__(self):
        self.tabla = EnvConfig.BOT_TABLA_PLANES
        self.repository = PlanRepository()

    def es_plan_valido(
        self,
        id_tipo_lista,
        nombre_plan: str,
        tipo: str,
    ) -> bool:
        try:
            with SessionLocal() as db:
                return self.repository.es_plan_valido(
                    db,
                    id_tipo_lista,
                    nombre_plan,
                    tipo,
                )

        except Exception as e:
            logger.error(
                "❌ Error validando plan '%s' "
                "(tipo_lista=%r, tipo=%s): %s",
                nombre_plan,
                id_tipo_lista,
                tipo,
                e,
                exc_info=True,
            )

            return False

    def diagnosticar_plan(
        self,
        id_tipo_lista,
        nombre_plan: str,
    ) -> DiagnosticoPlan:
        try:
            with SessionLocal() as db:
                return self.repository.diagnosticar_plan(
                    db,
                    id_tipo_lista,
                    nombre_plan,
                )

        except Exception as e:
            logger.error(
                "❌ Error diagnosticando plan '%s' "
                "(tipo_lista=%r): %s",
                nombre_plan,
                id_tipo_lista,
                e,
                exc_info=True,
            )

            return DiagnosticoPlan(
                entrada_valida=True,
                error_consulta=True,
                detalle_error=str(e),
            )
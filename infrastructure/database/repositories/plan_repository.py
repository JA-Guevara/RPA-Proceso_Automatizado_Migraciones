import logging

from sqlalchemy import select

from infrastructure.database.models.plan_model import PlanModel

logger = logging.getLogger(__name__)


class PlanRepository:

    def es_plan_valido(self, db, id_tipo_lista, nombre_plan: str, tipo: str) -> bool:
        try:
            id_tipo_lista_int = int(id_tipo_lista)
        except (TypeError, ValueError):
            logger.warning(f"⚠️ id_tipo_lista no convertible a int: {id_tipo_lista!r}")
            return False

        tipo_normalizado = (tipo or "").strip()
        nombres_posibles = self._generar_nombres_posibles(nombre_plan)

        if not tipo_normalizado:
            logger.warning("⚠️ Tipo de plan vacío; no se valida plan.")
            return False

        if not nombres_posibles:
            logger.warning("⚠️ Nombre de plan vacío; no se valida plan.")
            return False

        stmt = (
            select(PlanModel.id_tipo_lista)
            .where(
                PlanModel.id_tipo_lista == id_tipo_lista_int,
                PlanModel.tipo == tipo_normalizado,
                PlanModel.nombre_plan.in_(nombres_posibles),
            )
            .limit(1)
        )

        return db.execute(stmt).first() is not None

    def _generar_nombres_posibles(self, nombre_plan: str) -> list[str]:
        nombre_raw = (nombre_plan or "").strip()

        if not nombre_raw:
            return []

        reemplazo_1 = nombre_raw.replace("  ", " ")
        reemplazo_2 = reemplazo_1.replace("  ", " ")
        normalizado = " ".join(nombre_raw.split())

        nombres = {
            nombre_raw,
            reemplazo_1,
            reemplazo_2,
            normalizado,
        }

        return [nombre for nombre in nombres if nombre]
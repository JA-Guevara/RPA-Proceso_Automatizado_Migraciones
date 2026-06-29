import logging
from dataclasses import dataclass, field

from sqlalchemy import select

from infrastructure.database.models.plan_model import PlanModel

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DiagnosticoPlan:
    entrada_valida: bool = False
    existe: bool = False
    existe_para_lista: bool = False
    listas_habilitadas: tuple[int, ...] = field(default_factory=tuple)
    tipos_para_lista: tuple[str, ...] = field(default_factory=tuple)
    error_consulta: bool = False
    detalle_error: str = ""


class PlanRepository:

    def es_plan_valido(
        self,
        db,
        id_tipo_lista,
        nombre_plan: str,
        tipo: str,
    ) -> bool:
        try:
            id_tipo_lista_int = int(id_tipo_lista)
        except (TypeError, ValueError):
            logger.warning(
                "⚠️ id_tipo_lista no convertible a int: %r",
                id_tipo_lista,
            )
            return False

        tipo_normalizado = (tipo or "").strip()
        nombres_posibles = self._generar_nombres_posibles(
            nombre_plan
        )

        if not tipo_normalizado:
            logger.warning(
                "⚠️ Tipo de plan vacío; no se valida plan."
            )
            return False

        if not nombres_posibles:
            logger.warning(
                "⚠️ Nombre de plan vacío; no se valida plan."
            )
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

    def diagnosticar_plan(
        self,
        db,
        id_tipo_lista,
        nombre_plan: str,
    ) -> DiagnosticoPlan:
        try:
            id_tipo_lista_int = int(id_tipo_lista)
        except (TypeError, ValueError):
            logger.warning(
                "⚠️ No se puede diagnosticar el plan porque "
                "id_tipo_lista no es válido: %r",
                id_tipo_lista,
            )

            return DiagnosticoPlan(
                entrada_valida=False,
            )

        nombres_posibles = self._generar_nombres_posibles(
            nombre_plan
        )

        if not nombres_posibles:
            logger.warning(
                "⚠️ No se puede diagnosticar un plan vacío."
            )

            return DiagnosticoPlan(
                entrada_valida=False,
            )

        stmt = (
            select(
                PlanModel.id_tipo_lista,
                PlanModel.tipo,
            )
            .where(
                PlanModel.nombre_plan.in_(nombres_posibles)
            )
        )

        registros = db.execute(stmt).all()

        if not registros:
            return DiagnosticoPlan(
                entrada_valida=True,
                existe=False,
                existe_para_lista=False,
            )

        listas_habilitadas = tuple(
            sorted({
                int(id_lista)
                for id_lista, _ in registros
                if id_lista is not None
            })
        )

        tipos_para_lista = tuple(
            sorted({
                str(tipo).strip()
                for id_lista, tipo in registros
                if (
                    id_lista is not None
                    and int(id_lista) == id_tipo_lista_int
                    and tipo is not None
                    and str(tipo).strip()
                )
            })
        )

        existe_para_lista = (
            id_tipo_lista_int in listas_habilitadas
        )

        return DiagnosticoPlan(
            entrada_valida=True,
            existe=True,
            existe_para_lista=existe_para_lista,
            listas_habilitadas=listas_habilitadas,
            tipos_para_lista=tipos_para_lista,
        )

    def _generar_nombres_posibles(
        self,
        nombre_plan: str,
    ) -> list[str]:
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

        return [
            nombre
            for nombre in nombres
            if nombre
        ]
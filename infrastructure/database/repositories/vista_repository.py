import logging
from typing import Any

from sqlalchemy import case, select
from sqlalchemy.orm import Session

from infrastructure.database.models.vista_migracion_model import VistaMigracionModel

logger = logging.getLogger(__name__)


class VistaRepository:

    def _to_dict(self, fila: VistaMigracionModel) -> dict[str, Any]:
        return {
            "id_migracion": fila.id_migracion,
            "id_sharepoint": fila.id_sharepoint,
            "id_tipo_lista": fila.id_tipo_lista,
            "nombre_lista": fila.nombre_lista,
            "id_tipo_baja": fila.id_tipo_baja,
            "nombre_tipo_baja": fila.nombre_tipo_baja,
            "id_estado": fila.id_estado,
            "nombre_estado": fila.nombre_estado,
            "nro_linea": fila.nro_linea,
            "monto_valor_residual": fila.monto_valor_residual,
            "lote": fila.lote,
        }

    def hay_pendientes_para_bot(
        self,
        db: Session,
        bot_name: str,
    ) -> bool:
        stmt = (
            select(VistaMigracionModel.id_migracion)
            .where(VistaMigracionModel.lote == bot_name)
            .limit(1)
        )

        return db.execute(stmt).first() is not None

    def obtener_siguiente_migracion(
        self,
        db: Session,
        bot_name: str,
        prioridades: list[str],
    ) -> dict | None:
        stmt = (
            select(VistaMigracionModel)
            .where(VistaMigracionModel.lote == bot_name)
        )

        prioridades_limpias = [
            p.strip()
            for p in prioridades
            if p and p.strip()
        ]

        if prioridades_limpias:
            orden_prioridad = case(
                {
                    nombre_lista: orden
                    for orden, nombre_lista in enumerate(prioridades_limpias)
                },
                value=VistaMigracionModel.nombre_lista,
                else_=999,
            )

            stmt = stmt.order_by(
                orden_prioridad.asc(),
                VistaMigracionModel.id_migracion.asc(),
            )
        else:
            stmt = stmt.order_by(
                VistaMigracionModel.id_migracion.asc()
            )

        fila = db.execute(stmt.limit(1)).scalars().first()

        if not fila:
            return None

        return self._to_dict(fila)
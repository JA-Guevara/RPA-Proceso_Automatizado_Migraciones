import logging

from sqlalchemy import text

logger = logging.getLogger(__name__)


class VistaRepository:
    def hay_pendientes_para_bot(self, db, vista: str, bot_name: str) -> bool:
        # Lectura de vista legacy SQL Server; se mantiene NOLOCK por compatibilidad con comportamiento actual.
        sql = text(f"SELECT TOP 1 1 FROM {vista} WITH (NOLOCK) WHERE lote = :bot")
        return db.execute(sql, {"bot": bot_name}).scalar() is not None

    def obtener_siguiente_migracion(self, db, vista: str, bot_name: str, prioridades: list[str]) -> dict | None:
        for prioridad in prioridades:
            filtro_columna = (
                "nombre_lista" if prioridad.upper().startswith("LISTA") else "nombre_tipo_baja"
            )
            condicion_prioridad = (
                f"AND UPPER({filtro_columna}) = UPPER(:prioridad)" if prioridad else ""
            )

            # Lectura de vista legacy SQL Server; se mantiene NOLOCK/TOP por compatibilidad con comportamiento actual.
            sql = text(
                f"SELECT TOP 1 * FROM {vista} WITH (NOLOCK) "
                f"WHERE lote = :bot {condicion_prioridad} ORDER BY id_migracion ASC"
            )

            params = {"bot": bot_name}
            if prioridad:
                params["prioridad"] = prioridad

            row = db.execute(sql, params).mappings().first()
            if row:
                data = dict(row)
                logger.info(f"✅ Registro encontrado para prioridad '{prioridad}' → {data.get('nro_linea')}")
                return data

        logger.warning("⚠️ No se encontraron registros disponibles para el bot.")
        return None

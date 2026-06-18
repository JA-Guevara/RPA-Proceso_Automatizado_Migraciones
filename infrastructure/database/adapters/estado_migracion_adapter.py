import logging

from config.config import EnvConfig
from infrastructure.database.database import SessionLocal
from infrastructure.database.repositories.estado_repository import EstadoRepository
from infrastructure.database.repositories.migracion_repository import MigracionRepository

logger = logging.getLogger(__name__)


class EstadoSQLAdapter:
    def __init__(self):
        self.tabla = EnvConfig.BOT_TABLA_ESTADOS
        self.estado_repository = EstadoRepository()
        self.migracion_repository = MigracionRepository()

    def obtener_id_por_nombre(self, nombre_estado: str) -> int | None:
        try:
            with SessionLocal() as db:
                return self.estado_repository.obtener_id_por_nombre(db, nombre_estado)
        except Exception as e:
            logger.error(f"❌ Error buscando estado '{nombre_estado}' en {self.tabla}: {e}", exc_info=True)
            return None

    def obtener_nombre_por_id(self, id_estado: int) -> str | None:
        # Legacy: sin uso actual en el flujo; se conserva por compatibilidad.
        try:
            with SessionLocal() as db:
                return self.estado_repository.obtener_nombre_por_id(db, id_estado)
        except Exception as e:
            logger.error(f"❌ Error buscando nombre de estado con ID {id_estado}: {e}", exc_info=True)
            return None

    def actualizar_estado_migracion(self, contexto: dict) -> bool:
        baja_realizada = contexto.get("baja_realizada")
        id_migracion = contexto.get("id_migracion")

        if not baja_realizada:
            logger.error("❌ Falta 'baja_realizada' en el contexto; no se actualiza estado.")
            return False
        if not id_migracion:
            logger.error("❌ Falta 'id_migracion' en el contexto; no se actualiza estado.")
            return False

        try:
            with SessionLocal() as db:
                estado_id = self.estado_repository.obtener_id_por_nombre(db, baja_realizada)
                if not estado_id:
                    logger.error(f"❌ Estado '{baja_realizada}' no encontrado en {self.tabla}")
                    return False

                actualizado = self.migracion_repository.actualizar_estado(db, id_migracion, estado_id)
                if not actualizado:
                    db.rollback()
                    logger.error(f"❌ Migración id={id_migracion} no encontrada; no se actualizó estado.")
                    return False

                db.commit()
                logger.info(f"✅ Estado actualizado a '{baja_realizada}' (id_estado={estado_id}) para migración {id_migracion}")
                return True
        except Exception as e:
            logger.error(f"❌ Error actualizando estado desde contexto: {e}", exc_info=True)
            return False

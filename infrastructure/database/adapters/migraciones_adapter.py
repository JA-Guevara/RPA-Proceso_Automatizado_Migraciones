import logging

from infrastructure.database.database import SessionLocal
from infrastructure.database.repositories.migracion_detalle_repository import MigracionDetalleRepository

logger = logging.getLogger(__name__)


class MigracionesSQLAdapter:
    def __init__(self):
        self.repository = MigracionDetalleRepository()

    def registrar_detalle(self, contexto: dict):
        try:
            with SessionLocal() as db:
                self.repository.registrar_o_actualizar(db, contexto)
                db.commit()

                logger.info(
                    f"✅ Detalle registrado correctamente "
                    f"id_migracion={contexto.get('id_migracion')}"
                )

        except Exception as e:
            logger.error(
                f"❌ Error al registrar detalle en migracion_detalle: {e}",
                exc_info=True,
            )
            raise
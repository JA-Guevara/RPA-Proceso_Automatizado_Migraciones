import logging

from config.config import EnvConfig
from infrastructure.database.database import SessionLocal
from infrastructure.database.repositories.vista_repository import VistaRepository

logger = logging.getLogger(__name__)


class VistaSQLAdapter:
    def __init__(self):
        self.vista = EnvConfig.BOT_VISTA
        self.bot_name = EnvConfig.BOT_NAME

        prioridades_env = EnvConfig.PRIORIDAD_BAJAS
        self.prioridades = [
            p.strip()
            for p in prioridades_env.split(",")
            if p.strip()
        ]

        self.repository = VistaRepository()

        logger.info(
            f"⚙️ VistaSQLAdapter inicializado → "
            f"Vista: {self.vista}, "
            f"Bot: {self.bot_name}, "
            f"Prioridades: {self.prioridades}"
        )

    def obtener_siguiente_migracion(self) -> dict | None:
        try:
            with SessionLocal() as db:
                return self.repository.obtener_siguiente_migracion(
                    db=db,
                    bot_name=self.bot_name,
                    prioridades=self.prioridades,
                )

        except Exception as e:
            logger.error(
                f"❌ Error consultando la vista {self.vista}: {e}",
                exc_info=True,
            )
            return None

    def hay_pendientes_para_bot(self) -> bool:
        try:
            with SessionLocal() as db:
                return self.repository.hay_pendientes_para_bot(
                    db=db,
                    bot_name=self.bot_name,
                )

        except Exception as e:
            logger.error(
                f"❌ Error validando pendientes para {self.bot_name}: {e}",
                exc_info=True,
            )
            return False
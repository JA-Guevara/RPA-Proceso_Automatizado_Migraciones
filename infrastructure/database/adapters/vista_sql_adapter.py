import logging
from sqlalchemy import text
from infrastructure.database.database import SessionLocal
from config.config import EnvConfig

logger = logging.getLogger(__name__)

class VistaSQLAdapter:
    def __init__(self):
        self.vista = EnvConfig.BOT_VISTA
        self.bot_name = EnvConfig.BOT_NAME
        prioridades_env = EnvConfig.PRIORIDAD_BAJAS
        self.prioridades = [p.strip() for p in prioridades_env.split(",") if p.strip()]
        logger.info(f"⚙️ VistaSQLAdapter inicializado → Vista: {self.vista}, Bot: {self.bot_name}, Prioridades: {self.prioridades}")

    def obtener_siguiente_migracion(self) -> dict | None:
        """Obtiene la siguiente migración que el bot debe procesar, según sus prioridades."""
        try:
            with SessionLocal() as db:
                for prioridad in self.prioridades:
                    # Determinar si la prioridad aplica sobre la lista o el tipo de baja
                    filtro_columna = (
                        "nombre_lista" if prioridad.upper().startswith("LISTA") else "nombre_tipo_baja"
                    )
                    condicion_prioridad = (
                        f"AND UPPER({filtro_columna}) = UPPER(:prioridad)" if prioridad else ""
                    )

                    # ✅ Sin filtro de id_estado, solo por lote y prioridad
                    sql = text(f"""
                        SELECT TOP 1 *
                        FROM {self.vista} WITH (NOLOCK)
                        WHERE lote = :bot
                        {condicion_prioridad}
                        ORDER BY id_migracion ASC
                    """)

                    params = {"bot": self.bot_name}
                    if prioridad:
                        params["prioridad"] = prioridad

                    result = db.execute(sql, params)
                    row = result.mappings().first()

                    if row:
                        data = dict(row)
                        logger.info(f"✅ Registro encontrado para prioridad '{prioridad}' → {data.get('nro_linea')}")
                        return data

                logger.warning("⚠️ No se encontraron registros disponibles para el bot.")
                return None

        except Exception as e:
            logger.error(f"❌ Error consultando la vista {self.vista}: {e}", exc_info=True)
            return None

    def hay_pendientes_para_bot(self) -> bool:
        """Verifica si la vista tiene al menos un registro disponible para este bot."""
        try:
            with SessionLocal() as db:
                # ✅ Sin filtro de id_estado — la vista ya controla qué mostrar
                sql = text(f"""
                    SELECT TOP 1 1
                    FROM {self.vista} WITH (NOLOCK)
                    WHERE lote = :bot
                """)
                result = db.execute(sql, {"bot": self.bot_name})
                hay = result.scalar() is not None

                logger.info(f"🔍 Pendientes para {self.bot_name}: {'Sí' if hay else 'No'}.")
                return hay

        except Exception as e:
            logger.error(f"❌ Error validando pendientes para {self.bot_name}: {e}", exc_info=True)
            return False

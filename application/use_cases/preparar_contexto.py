from datetime import datetime
import logging

from config.config import EnvConfig

logger = logging.getLogger(__name__)

class PreparadorDeContextos:
    def __init__(self):
        pass

    def preparar(self, tarea) -> dict:
        if not isinstance(tarea, dict):
            logger.error(f"❌ Se esperaba dict en preparar(), pero se recibió {type(tarea)} → {tarea}")
            return {}

        plan_consumo_fijo = getattr(EnvConfig, "PLAN_CONSUMO_POST_A_PRE", "1841")
        contexto = {
            "id_migracion": tarea.get("id_migracion"),
            "id_sharepoint": tarea.get("id_sharepoint"),
            "nro_linea": str(tarea.get("nro_linea", "")).strip(),
            "id_tipo_baja": tarea.get("id_tipo_baja"),
            "tipo_baja": str(tarea.get("nombre_tipo_baja", "")).strip(),
            "id_tipo_lista": str(tarea.get("id_tipo_lista", "")).strip(),
            "lote": tarea.get("lote", ""),
            "monto_valor_residual": tarea.get("monto_valor_residual"),
            "valor_residual": tarea.get("monto_valor_residual", 0),
            "codigo_plan_consumo_asignados_rpa": plan_consumo_fijo,
            "codigo_plan_comercial_prepago_r": EnvConfig.PLAN_COMERCIAL_PREPAGO_R,
            "codigo_plan_consumo_prepago_r": EnvConfig.PLAN_CONSUMO_PREPAGO_R,
        }

        return contexto



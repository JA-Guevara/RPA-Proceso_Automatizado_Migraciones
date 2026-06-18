from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class PreparadorDeContextos:
    def __init__(self):
        pass

    def preparar(self, tarea) -> dict:
        if not isinstance(tarea, dict):
            logger.error(f"❌ Se esperaba dict en preparar(), pero se recibió {type(tarea)} → {tarea}")
            return {}

        contexto = {
            "id_migracion": tarea.get("id_migracion"),
            "id_sharepoint": tarea.get("id_sharepoint"),
            "nro_linea": str(tarea.get("nro_linea", "")).strip(),
            "id_tipo_baja": tarea.get("id_tipo_baja"),
            "tipo_baja": str(tarea.get("nombre_tipo_baja", "")).strip(),
            "id_tipo_lista": str(tarea.get("id_tipo_lista", "")).strip(),
            "lote": tarea.get("lote", ""),

        }


        return contexto



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

        # campos_iniciales = {
        #     "fecha_hora_inicio": "",
        #     "fecha_hora_fin": "",
        #     "estado_cuenta_anterior_rpa": "",
        #     "estado_cuenta_posterior_rpa": "",
        #     "forma_pago_anterior_rpa": "",
        #     "forma_pago_posterior_rpa": "",
        #     "situacion_cuenta_anterior_rpa": "",
        #     "situacion_cuenta_posterior_rpa": "",
        #     "cnsCancelado": "",
        #     "servicios_asignados_rpa": "",
        #     "servicios_eliminados_rpa": "",
        #     "facturas_pendientes_rpa": "",
        #     "deuda_pendiente": "",
        #     "billetera_prepago_rpa": "",
        #     "antiguedad_meses_rpa": "",
        #     "plan_consumo_anterior_rpa": "",
        #     "plan_consumo_asignado_rpa": "",
        #     "codigo_plan_consumo_asignados_rpa": "",
        #     "notificacion_baja": "",
        #     "existe_cambio_pendiente_rpa": "",
        #     "existe_LDI_900": "",
        #     "existe_sub_LDI_900": "",
        #     "existe_alcanse_llamadas": "",
        #     "existe_factura_fija": "",
        #     "plan_valido": "",
        #     "baja_habilitada": "",
        #     "plan_actual_rpa": "",
        #     "plan_asignado_rpa": "",
        #     "estado_extraido_rpa": "",
        #     "fecha_hora_observacion_rpa": "",
        #     "mensaje_observacion_rpa": "",
        #     "mensaje_memo": "",
        #     "baja_realizada": "",
        # }

        # contexto.update(campos_iniciales)
        return contexto

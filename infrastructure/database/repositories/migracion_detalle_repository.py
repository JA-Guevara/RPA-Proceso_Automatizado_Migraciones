import logging

from infrastructure.database.models.migracion_detalle_model import MigracionDetalleModel

logger = logging.getLogger(__name__)


class MigracionDetalleRepository:
    MAPEO = {
        "id_migracion": "id_migracion",
        "fecha_hora_inicio_migracionactions": "fecha_hora_inicio",
        "fecha_hora_fin_migracionactions": "fecha_hora_fin",
        "plan_actual_rpa": "plan_consumo_anterior_rpa",
        "plan_asignado_rpa": "plan_consumo_asignado_rpa",
        "codigo_plan_consumo_asignados_rpa": "codigo_plan_consumo_asignados_rpa",
        "estado_cuenta_anterior_rpa": "estado_cuenta_anterior_rpa",
        "estado_cuenta_posterior_rpa": "estado_cuenta_posterior_rpa",
        "forma_pago_anterior_rpa": "forma_pago_anterior_rpa",
        "forma_pago_posterior_rpa": "forma_pago_posterior_rpa",
        "situacion_cuenta_anterior_rpa": "situacion_cuenta_anterior_rpa",
        "situacion_cuenta_posterior_rpa": "situacion_cuenta_posterior_rpa",
        "servicios_asignados_rpa": "servicios_asignados_rpa",
        "servicios_eliminados_rpa": "servicios_eliminados_rpa",
        "facturas_pendientes_rpa": "facturas_pendientes_rpa",
        "deuda_pendiente": "deuda_pendiente",
        "billetera_prepago_rpa": "billetera_prepago_rpa",
        "antiguedad_meses_rpa": "antiguedad_meses_rpa",
        "notificacion_baja_rpa": "notificacion_baja",
        "fecha_hora_fin_derivacionsmsaction": "fecha_hora_notificacion_baja_rpa",
        "fecha_hora_observacion_rpa": "fecha_hora_observacion_rpa",
        "mensaje_observacion_rpa": "mensaje_observacion_rpa",
    }

    def obtener_por_id_migracion(self, db, id_migracion):
        return (
            db.query(MigracionDetalleModel)
            .filter(MigracionDetalleModel.id_migracion == id_migracion)
            .first()
        )

    def registrar_o_actualizar(self, db, contexto: dict):
        id_migracion = contexto.get("id_migracion")

        if not id_migracion:
            logger.warning("⚠️ No se encontró 'id_migracion' en el contexto. No se registra detalle.")
            return None

        params = {}

        for ctx_key, col in self.MAPEO.items():
            valor = contexto.get(ctx_key, None)

            if isinstance(valor, str):
                valor = valor.strip()
                if valor == "" or valor.upper().startswith("ERROR_"):
                    valor = None

            params[col] = valor

        params["id_migracion"] = id_migracion

        detalle = self.obtener_por_id_migracion(db, id_migracion)

        if detalle is not None:
            actualizados = 0

            for col, valor in params.items():
                if col == "id_migracion":
                    continue

                if valor is not None:
                    setattr(detalle, col, valor)
                    actualizados += 1

            if actualizados:
                logger.info(f"🌀 Detalle actualizado id_migracion={id_migracion} ({actualizados} campos)")
            else:
                logger.info(f"ℹ️ Nada para actualizar en detalle id_migracion={id_migracion}")

            return detalle

        detalle = MigracionDetalleModel(**params)
        db.add(detalle)

        logger.info(f"✅ Detalle insertado id_migracion={id_migracion}")

        return detalle
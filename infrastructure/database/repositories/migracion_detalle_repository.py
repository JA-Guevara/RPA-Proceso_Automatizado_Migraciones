import logging

from sqlalchemy import String

from config.config import EnvConfig
from infrastructure.database.models.migracion_detalle_model import MigracionDetalleModel

logger = logging.getLogger(__name__)


def _limites_columnas() -> dict:
    """
    Largo maximo por columna, leido del propio modelo ORM.

    Existe para que un texto largo NUNCA rompa el INSERT. SQL Server rechaza
    la fila entera con "String or binary data would be truncated", asi que un
    solo campo desbordado hacia perder TODO el detalle del registro.

    Casos reales de desborde:
      - mensaje_observacion_rpa: MigracionActions._anexar_observacion concatena
        con ' | ', y los mensajes incluyen textos de excepcion que pueden ser
        de cientos de caracteres.
      - plan_consumo_*_rpa: una captura de OCR degradada devuelve texto largo.
      - servicios_asignados_rpa / servicios_eliminados_rpa: String(50) y se
        van concatenando por cada servicio tocado.
    """
    limites = {}

    for col in MigracionDetalleModel.__table__.columns:
        tipo = getattr(col, "type", None)
        largo = getattr(tipo, "length", None)
        if isinstance(tipo, String) and largo:
            limites[col.name] = int(largo)

    # El modelo declara mensaje_observacion_rpa como String(1000), pero la
    # columna real acepta menos. BOT_MAX_OBSERVACION manda cuando es mas chico.
    tope = int(getattr(EnvConfig, "BOT_MAX_OBSERVACION", 0) or 0)
    if tope > 0:
        actual = limites.get("mensaje_observacion_rpa", tope)
        limites["mensaje_observacion_rpa"] = min(actual, tope)

    return limites


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

    LIMITES = _limites_columnas()

    def _recortar(self, columna: str, valor):
        """Recorta al largo de la columna. Deja rastro en el log del original."""
        if not isinstance(valor, str):
            return valor

        limite = self.LIMITES.get(columna)
        if not limite or len(valor) <= limite:
            return valor

        if limite > 3:
            recortado = valor[: limite - 3].rstrip() + "..."
        else:
            recortado = valor[:limite]

        logger.warning(
            "✂️ '%s' excedia el limite de la columna (%s > %s). Se recorta. "
            "Original: %r",
            columna, len(valor), limite, valor[:300],
        )
        return recortado[:limite]

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

            params[col] = self._recortar(col, valor)

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
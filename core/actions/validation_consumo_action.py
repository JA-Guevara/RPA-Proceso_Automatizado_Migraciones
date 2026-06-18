import pyperclip
from core.action_base.action_base import ActionBase


class ValidationConsumoAction(ActionBase):

    def __init__(self, variables_base: dict, contexto: dict):
        super().__init__(
            variables_base,
            contexto,
            flow_name="validation_consumo"
        )
        self.executor._action_extraer_validar_consumo = self.extraer_validar_consumo

    def ejecutar(self) -> bool:
        self.logger.info("🚀 Iniciando validation_consumo action...")
        self.hora_inicio()

        try:
            self.executor.ejecutar_bloque("validation")
            cantidad = int(self.contexto.get("facturas_pendientes_rpa", 0))
            id_sharepoint = self.contexto.get("id_sharepoint")

            if cantidad > 0:
                observacion = f"Línea presenta {cantidad} factura(s) pendientes de pago"
                deuda = "Con Deuda"
                memo = f"Baja observada - ID solicitud: {id_sharepoint}"
                baja = "Baja Observada"
            else:
                observacion = ""
                deuda = "Sin Deuda"
                memo = ""
                baja = ""
            self.contexto.update({
                "facturas_pendientes_rpa": cantidad,
                "mensaje_observacion_rpa": observacion,
                "deuda_pendiente": deuda,
                "mensaje_memo": memo,
                "baja_realizada": baja,
            })
            self.logger.info(
                f"🧾 Facturas: {cantidad} | 💬 Obs: '{observacion}' | 🏷️ Deuda: {deuda} | 📝 Memo: '{memo}'"
            )

            if cantidad > 0:
                self.logger.warning("⚠️ Deuda detectada → se devolverá False para cierre con reclamo.")
                return False

            return True

        except Exception as e:
            self.manejar_excepcion(e)
            try:
                self.executor.ejecutar_bloque("reboot_validation")
            except Exception:
                self.logger.warning("⚠️ Falló también reboot_validation", exc_info=True)
            raise
        finally:
            self.hora_fin()

    def extraer_validar_consumo(self, paso):
        self.logger.info("🔍 Ejecutando acción personalizada: extraer_validar_consumo")

        try:
            ruta, nombre = self.executor._resolver_imagen(paso.get("target"))

            self.clicker.hacer_clic(
                target=ruta,
                offset_x=paso.get("offset_x", 0),
                offset_y=paso.get("offset_y", 0),
                clicks=paso.get("clicks", 2),
                nombre_logico=nombre,
                usar_imagen=paso.get("usar_imagen", True),
                raise_error=paso.get("raise_error", True),
                transitorio=paso.get("transitorio", False),
            )

            self.app_tools.esperar(0.2)
            self.app_tools.presionar_tecla_real("up")

            texto = self.basic_tools.copiar_texto_actual(
                seleccionar_todo=False,
                limpiar=True,
                mayusculas=False,
                usar_real=True,
                timeout=12.0,
            )

            if not texto:
                self.logger.warning("⚠️ No se pudo capturar texto para validar consumo.")
                self.contexto["facturas_pendientes_rpa"] = 0
                return

            lineas = texto.splitlines()
            pendientes = [l for l in lineas if "pendiente" in l.lower()]
            cantidad = len(pendientes)

            self.contexto["facturas_pendientes_rpa"] = cantidad
            self.logger.info(f"📋 Facturas pendientes detectadas: {cantidad}")

        except Exception as e:
            self.logger.error(f"❌ Error al extraer facturas: {e}", exc_info=True)
            raise
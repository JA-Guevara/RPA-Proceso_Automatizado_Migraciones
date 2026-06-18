import pyperclip
from core.action_base.action_base import ActionBase


class ValidationEstadoCuentaAction(ActionBase):
    def __init__(self, variables_base, contexto):
        super().__init__(variables_base, contexto,
                         flow_name="validation_estado_cuenta")
        self.executor._action_extraer_validar_estado = self.extraer_validar_estado

    def ejecutar(self):
        self.logger.info("🚀 Iniciando validation_estado_cuenta action...")
        self.hora_inicio()

        try:
            self.executor.ejecutar_bloque("validation")

            estado = self.contexto.get("estado_extraido_rpa", "").strip().upper()
            id_sharepoint = self.contexto.get("id_sharepoint")

            if self.contexto.get("error_de_estado"):
                self.logger.warning("🚫 Error al detectar el estado → devolverá False.")
                self.contexto.update({
                    "baja_realizada": "Baja Observada",
                    "mensaje_memo": f"Baja observada - ID solicitud: {id_sharepoint}"
                })
                self.registrar_observacion("Error al detectar el estado de cuenta válido.")
                return False

            if estado == "PO":
                self.logger.info("📌 Línea con Port Out: registrar desestimación y cerrar con reclamo.")
                self.contexto.update({
                        "estado_cuenta_anterior_rpa": estado,
                    })
                self.contexto.update({
                    "baja_realizada": "Baja Desestimada",
                    "mensaje_memo": f"Baja observada - ID solicitud: {id_sharepoint}"
                })
                self.registrar_observacion("Línea realizó Port Out")
                return False

            elif estado == "PP":
                self.logger.info("🚫 Línea en PP: cerrar con reclamo.")
                self.contexto.update({
                        "estado_cuenta_anterior_rpa": estado,
                    })
                self.contexto.update({
                    "baja_realizada": "Baja Desestimada",
                    "mensaje_memo": f"Baja observada - ID solicitud: {id_sharepoint}"
                })
                self.registrar_observacion("Línea se encuentra en proceso de portación")
                return False

            elif estado == "PK":
                self.logger.info("🔁 Línea en PK: ejecutando pre-eliminación")
                self.executor.ejecutar_bloque("flow_pre-eliminacion")
                self.contexto.update({
                    "estado_cuenta_anterior_rpa": "PK",
                    "estado_cuenta_posterior_rpa": "AC"
                })
                self.registrar_observacion("Pre-eliminación ejecutada.")
                return True

            elif estado != "AC":
                self.logger.info("🔁 Estado distinto de AC: ejecutando validación de cambio de estado (validation2)")
                self.executor.ejecutar_bloque("validation2")

                if not self.contexto.get("imagen_encontrada", False):
                    self.logger.warning("🚫 Imagen de cambio de estado no encontrada → cerrar con reclamo.")
                    self.contexto.update({
                        "baja_realizada": "Baja Observada",
                        "mensaje_memo": f"Baja observada - ID solicitud: {id_sharepoint}",
                        "error_de_estado": True
                    })
                    self.registrar_observacion("No se encontró imagen de cambio de estado")
                    return False
                else:
                    self.logger.info("✅ Imagen detectada correctamente, ejecutando flow_distinto_AC.")
                    self.executor.ejecutar_bloque("flow_distinto_AC")
                    self.contexto.update({
                        "estado_cuenta_anterior_rpa": estado,
                        "estado_cuenta_posterior_rpa": "AC"
                    })
                    self.registrar_observacion("")
                    return True

            else:
                self.logger.info("✅ Estado AC: continúa validación siguiente.")
                self.contexto.update({
                    "estado_cuenta_anterior_rpa": "AC",
                    "estado_cuenta_posterior_rpa": "AC",
                })
                self.registrar_observacion("")
                return True

        except Exception as e:
            self.manejar_excepcion(e)
            try:
                self.logger.warning("🔁 Ejecutando reboot_validation como fallback...")
                self.executor.ejecutar_bloque("reboot_validation")
            except Exception:
                self.logger.warning("⚠️ Falló también reboot_validation", exc_info=True)
            raise
        finally:
            self.hora_fin()

    def extraer_validar_estado(self, paso):
        self.logger.info("🔍 Ejecutando acción personalizada: extraer_estado_cuenta")
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
                transitorio=paso.get("transitorio", False)
            )

            self.app_tools.esperar(1)
            self.app_tools.presionar_combinacion_real("ctrl", "c")
            self.app_tools.esperar(0.2)

            texto = pyperclip.paste().strip().upper()
            estado_detectado = texto.split()[0] if texto else ""

            ESTADOS_VALIDOS = ["AC", "PP", "PO", "PK"]
            if estado_detectado not in ESTADOS_VALIDOS:
                self.logger.warning(f"⚠️ Estado inválido detectado: '{estado_detectado}'")
                self.contexto.update({
                    "estado_extraido_rpa": None,
                    "error_de_estado": True
                })
                return

            self.logger.info(f"📋 Estado de cuenta detectado: '{estado_detectado}'")
            self.contexto.update({
                "estado_extraido_rpa": estado_detectado,
                "error_de_estado": False
            })

        except Exception as e:
            self.logger.error(f"❌ Error al extraer estado de cuenta: {e}", exc_info=True)
            self.contexto["error_de_estado"] = True
            raise



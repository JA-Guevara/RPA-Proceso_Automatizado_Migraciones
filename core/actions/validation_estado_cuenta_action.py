import pyperclip

from core.action_base.action_base import ActionBase


class ValidationEstadoCuentaAction(ActionBase):
    ESTADOS_VALIDOS = {"AC", "PP", "PO", "PK", "EL"}

    def __init__(self, variables_base, contexto):
        super().__init__(
            variables_base,
            contexto,
            flow_name="validation_estado_cuenta",
        )
        self.executor._action_extraer_validar_estado = self.extraer_validar_estado

    def ejecutar(self):
        self.logger.info("🚀 Iniciando validation_estado_cuenta action...")
        self.hora_inicio()

        try:
            self.executor.ejecutar_bloque("validation")

            estado = str(self.contexto.get("estado_extraido_rpa") or "").strip().upper()
            id_sharepoint = self.contexto.get("id_sharepoint")

            if self.contexto.get("error_de_estado"):
                self.logger.warning("🚫 Error al detectar el estado → devolverá False.")
                self.contexto.update({
                    "baja_realizada": "Baja Observada",
                    "mensaje_memo": f"Baja observada - ID solicitud: {id_sharepoint}",
                    "estado_cuenta_anterior_rpa": estado or "",
                })
                self.registrar_observacion("Error al detectar el estado de cuenta válido.")
                return False
            
            if estado == "EL":
                self.logger.info("🚫 Línea en estado EL: cuenta eliminada, cerrar con reclamo.")
                self.contexto.update({
                    "estado_cuenta_anterior_rpa": "EL",
                    "estado_cuenta_posterior_rpa": "EL",
                    "baja_realizada": "Baja Desestimada",
                    "mensaje_memo": f"Baja observada - ID solicitud: {id_sharepoint}",
                })
                self.registrar_observacion("Línea se encuentra en estado eliminado.")
                return False

            if estado == "PO":
                self.logger.info("📌 Línea con Port Out: registrar desestimación y cerrar con reclamo.")
                self.contexto.update({
                    "estado_cuenta_anterior_rpa": "PO",
                    "estado_cuenta_posterior_rpa": "PO",
                    "baja_realizada": "Baja Desestimada",
                    "mensaje_memo": f"Baja observada - ID solicitud: {id_sharepoint}",
                })
                self.registrar_observacion("Línea realizó Port Out")
                return False

            if estado == "PP":
                self.logger.info("🚫 Línea en PP: cerrar con reclamo.")
                self.contexto.update({
                    "estado_cuenta_anterior_rpa": "PP",
                    "estado_cuenta_posterior_rpa": "PP",
                    "baja_realizada": "Baja Desestimada",
                    "mensaje_memo": f"Baja observada - ID solicitud: {id_sharepoint}",
                })
                self.registrar_observacion("Línea se encuentra en proceso de portación")
                return False

            if estado == "PK":
                self.logger.info("🔁 Línea en PK: ejecutando pre-eliminación")
                self.executor.ejecutar_bloque("flow_pre-eliminacion")
                self.contexto.update({
                    "estado_cuenta_anterior_rpa": "PK",
                    "estado_cuenta_posterior_rpa": "AC",
                })
                self.registrar_observacion("Pre-eliminación ejecutada.")
                return True

            if estado != "AC":
                self.logger.info("🔁 Estado distinto de AC: ejecutando validación de cambio de estado (validation2)")
                self.executor.ejecutar_bloque("validation2")

                if not self.contexto.get("imagen_encontrada", False):
                    self.logger.warning("🚫 Imagen de cambio de estado no encontrada → cerrar con reclamo.")
                    self.contexto.update({
                        "estado_cuenta_anterior_rpa": estado,
                        "estado_cuenta_posterior_rpa": estado,
                        "baja_realizada": "Baja Observada",
                        "mensaje_memo": f"Baja observada - ID solicitud: {id_sharepoint}",
                        "error_de_estado": True,
                    })
                    self.registrar_observacion("No se encontró imagen de cambio de estado")
                    return False

                self.logger.info("✅ Imagen detectada correctamente, ejecutando flow_distinto_AC.")
                self.executor.ejecutar_bloque("flow_distinto_AC")
                self.contexto.update({
                    "estado_cuenta_anterior_rpa": estado,
                    "estado_cuenta_posterior_rpa": "AC",
                })
                self.registrar_observacion("")
                return True

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
                transitorio=paso.get("transitorio", False),
            )

            self.app_tools.esperar(1)
            self.app_tools.presionar_combinacion_real("ctrl", "c")
            self.app_tools.esperar(0.2)

            texto = str(pyperclip.paste() or "").strip().upper()
            estado_detectado = texto.split()[0] if texto else ""

            self.contexto["estado_cuenta_texto_crudo_rpa"] = texto

            if estado_detectado not in self.ESTADOS_VALIDOS:
                self.logger.warning("⚠️ Estado inválido detectado: '%s' | texto_crudo=%r", estado_detectado, texto)
                self.contexto.update({
                    "estado_extraido_rpa": "",
                    "error_de_estado": True,
                })
                return

            self.logger.info("📋 Estado de cuenta detectado: '%s'", estado_detectado)
            self.contexto.update({
                "estado_extraido_rpa": estado_detectado,
                "error_de_estado": False,
            })

        except Exception as e:
            self.logger.error("❌ Error al extraer estado de cuenta: %s", e, exc_info=True)
            self.contexto.update({
                "estado_extraido_rpa": "",
                "error_de_estado": True,
            })
            raise
from core.action_base.action_base import ActionBase

class CrearServicioFflteAction(ActionBase):
    def __init__(self, variables_base, contexto):
        super().__init__(variables_base, contexto,
                         flow_name="crear_servicio_fflte")

    def ejecutar(self):
        self.logger.info("🚀 Iniciando crear_servicio_fflte action...")
        self.hora_inicio()

        try:
            self.executor.ejecutar_bloque("validation_FFLTE")

            if self.contexto.get("existe_FFLTE", False):
                self.executor.ejecutar_bloque("validation_FFLTE_error")
                mensaje_error = self.contexto.get("mensaje_error", "").upper()

                if "CUENTA ESTA BLOQUEADA" in mensaje_error:
                    self.logger.info("🔐 Cuenta bloqueada detectada. Ejecutando flujo de desbloqueo...")
                    self.executor.ejecutar_bloque("flow_desbloqueo")
                    self.logger.info("🔄 Reintentando validación y flujo FFLTE...")
                    self.executor.ejecutar_bloque("validation_FFLTE")

                    if self.contexto.get("existe_FFLTE", False):
                        self.executor.ejecutar_bloque("flow_FFLTE")
                        self.contexto["servicios_asignados_rpa"] = (
                            self.contexto.get("servicios_asignados_rpa", "") + "Factura Fija LTE, "
                        )

                elif mensaje_error:
                    self.logger.warning(f"⚠️ Error detectado en FFLTE: {mensaje_error}")
                    self.contexto["existe_error"] = True
                    self.executor.ejecutar_bloque("reboot_validation_FFLTE_error")

                else:
                    self.logger.info("▶ Ejecutando flow_FFLTE...")
                    self.executor.ejecutar_bloque("flow_FFLTE")
                    self.contexto["servicios_asignados_rpa"] = (
                        self.contexto.get("servicios_asignados_rpa", "") + "Factura Fija LTE, "
                    )

            else:
                self.logger.warning("⚠️ No se encontró FFLTE. Ejecutando reboot_validation_FFLTE...")
                self.executor.ejecutar_bloque("reboot_validation_FFLTE")

            return True

        except Exception as e:
            self.manejar_excepcion(e)
            try:
                self.executor.ejecutar_bloque("reboot_validation_FFLTE")
            except Exception as inner_e:
                self.logger.warning(f"⚠️ Falló también reboot_validation_FFLTE: {inner_e}", exc_info=True)

            raise  

        finally:
            self.hora_fin()



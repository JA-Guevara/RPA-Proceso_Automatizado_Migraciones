from core.action_base.action_base import ActionBase

class CapturaDatosAction(ActionBase):
    def __init__(self, variables_base, contexto):
        super().__init__(variables_base, contexto, flow_name="captura_datos", executor_type="desktop")

    def ejecutar(self):
        self.logger.info("🚀 Iniciando captura_datos action...")
        self.hora_inicio()

        try:
            self.executor.ejecutar_bloque("flow")
            if self.executor.contexto.get("existe_error_captura", False):
                self.logger.info("⚠️ Error en captura de fecha, reintentando...")
                self.executor.contexto["existe_error_captura"] = False  # limpiar ANTES
                self.executor.ejecutar_bloque("flow")
            return True

        except Exception as e:
            self.manejar_excepcion(e)
            try:
                self.executor.ejecutar_bloque("reboot_validation")
            except Exception as fallback_error:
                self.logger.warning("⚠️ Falló también reboot_validation", exc_info=True)

            raise  

        finally:
            self.hora_fin()

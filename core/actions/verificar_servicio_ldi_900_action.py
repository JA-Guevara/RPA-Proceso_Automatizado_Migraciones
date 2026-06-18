from core.action_base.action_base import ActionBase

class VerificarServicioLdi_900Action(ActionBase):
    def __init__(self, variables_base, contexto):
        super().__init__(variables_base, contexto,
                         flow_name="verificar_servicio_ldi_900")

    def ejecutar(self):
        self.logger.info("🚀 Iniciando verificar_servicios_ldi900 action...")
        self.hora_inicio()

        try:
            self.executor.ejecutar_bloque("validation")

            if self.contexto.get("existe_LDI_900", False):
                self.logger.info("▶ Ejecutando flow_LDI_LDN_900...")
                self.executor.ejecutar_bloque("flow")

                servicios_previos = self.contexto.get("servicios_eliminados_rpa", "")
                self.contexto["servicios_eliminados_rpa"] = servicios_previos + "LDI_LDN_900, "
            else:
                self.logger.warning("⚠️ No se encontró LDI_900. No se requiere acción adicional.")
                self.executor.ejecutar_bloque("reboot_validation")

            return True

        except Exception as e:
            self.manejar_excepcion(e)
            raise  

        finally:
            self.hora_fin()



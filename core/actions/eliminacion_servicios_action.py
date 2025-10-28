from core.action_base.action_base import ActionBase

class EliminacionServiciosAction(ActionBase):
    def __init__(self, variables_base, contexto):
        super().__init__(variables_base, contexto, flow_name="eliminacion_servicios", executor_type="desktop")

    def ejecutar(self):
        self.logger.info("🚀 Iniciando eliminacion_servicios action...")
        self.hora_inicio()
        try:
            self.executor.ejecutar_bloque("validation")

            if self.executor.contexto.get("existeRestringirNav", False):
                self.logger.info("✅ Restricción detectada → ejecutando flow_eliminacion")
                self.executor.ejecutar_bloque("flow_eliminacion")
                self.contexto["servicios_eliminados_rpa"] = self.contexto.get("servicios_eliminados_rpa", "") + "Restringir Navegación sin Nominación"
                return False
            else:
                self.logger.info("📌 Sin restricciones presentes → ejecutando reboot_validation")
                self.executor.ejecutar_bloque("reboot_validation")
                self.contexto["servicios_eliminados_rpa"] = self.contexto.get("servicios_eliminados_rpa", "") 
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

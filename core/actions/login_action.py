from core.action_base.action_base import ActionBase

class LoginAction(ActionBase):
    def __init__(self, variables_base, contexto):
        super().__init__(variables_base, contexto, flow_name="login", executor_type="desktop")

    def ejecutar(self):
        self.logger.info("🚀 Iniciando login action...")
        self.hora_inicio()
        try:
            self.executor.ejecutar_bloque("flow")
            return True
        except Exception as e:
            self.manejar_excepcion(e)
            try:
                self.executor.ejecutar_bloque("reboot_logout")
            except Exception as e2:
                self.logger.warning("⚠️ Falló también reboot_logout", exc_info=True)
            raise  

        finally:
            self.hora_fin()

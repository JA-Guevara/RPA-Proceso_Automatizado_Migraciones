from core.action_base.action_base import ActionBase
from infrastructure.remote_desktop.conexion_escritorio import ConexionEscritorio

class LogoutAction(ActionBase):
    def __init__(self, variables_base, contexto):
        super().__init__(variables_base, contexto, flow_name="logout")

    def ejecutar(self):
        self.logger.info("🚀 Iniciando logout action...")
        self.hora_inicio()
        try:
            self.executor.ejecutar_bloque("flow")
            ConexionEscritorio.instancia().desconectar()
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



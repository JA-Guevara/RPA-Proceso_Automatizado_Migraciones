from core.action_base.action_base import ActionBase
from core.actions.login_escritorio_web_action import LoginEscritorioWebAction
from infrastructure.remote_desktop.conexion_escritorio import ConexionEscritorio, MODO_WEB


class LoginAction(ActionBase):

    def __init__(self, variables_base: dict, contexto: dict | None = None):
        super().__init__(variables_base=variables_base, contexto=contexto, flow_name="login")

    def ejecutar(self) -> bool:
        self.hora_inicio()
        self.logger.info("🚀 Iniciando LoginAction")

        try:
            conexion = ConexionEscritorio.instancia()
            wait_time = self._resolver_wait_time()

            conexion.conectar(
                variables_base=self.variables_base,
                wait_time=wait_time,
            )

            self.contexto["conexion_escritorio_activa"] = True
            self.contexto["conexion_escritorio_modo"] = conexion.modo

            if conexion.modo == MODO_WEB:
                LoginEscritorioWebAction(self.variables_base, self.contexto).ejecutar()
                self.contexto["login_escritorio_web_activo"] = True

            conexion.esperar_ancla(wait_time=wait_time)
            self.contexto["conexion_escritorio_ready"] = True

            self.executor.ejecutar_bloque("flow")

            self.logger.info("✅ Login completado")
            return True

        except Exception as e:
            self.manejar_excepcion(e)

            try:
                self.executor.ejecutar_bloque("reboot_login")
            except Exception:
                self.logger.warning("⚠️ Falló reboot_login", exc_info=True)

            raise

        finally:
            self.hora_fin()

    def _resolver_wait_time(self) -> float:
        valor = (
            self.variables_base.get("wait_time")
            or self.contexto.get("wait_time")
            or self.variables_base.get("desktop_wait_time")
            or self.contexto.get("desktop_wait_time")
            or 10
        )

        try:
            return float(valor)
        except (TypeError, ValueError):
            self.logger.warning("⚠️ wait_time inválido, usando 10 segundos")
            return 10
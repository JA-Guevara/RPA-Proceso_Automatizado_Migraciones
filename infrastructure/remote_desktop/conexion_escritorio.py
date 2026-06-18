import logging
import os
import subprocess
import time

from config.config import EnvConfig, IMAGES_DIR
from shared.tools.app_tools import AppTools
from shared.tools.exceptions import RPAExceptions
from infrastructure.browser.browser_profiles import BROWSER_ESCRITORIO_WEB, BROWSER_ESCRITORIO_WEB_FULLSCREEN

logger = logging.getLogger(__name__)

MODO_RDP = "rdp"
MODO_WEB = "web"
ESCRITORIO_STORAGE = "storage/cookies/escritorio_state.json"


class ConexionEscritorio:
    _instancia = None

    @classmethod
    def instancia(cls):
        if cls._instancia is None:
            cls._instancia = cls()
        return cls._instancia

    def __init__(self):
        self.modo = EnvConfig.CONEXION_ESCRITORIO or MODO_RDP
        self.app_tools = AppTools()
        self._session = None
        self._locator = None

        logger.info(f"🖥️ ConexionEscritorio inicializada (modo={self.modo})")

    def conectar(self, variables_base: dict | None = None, host: str | None = None, wait_time=None) -> bool:
        variables_base = variables_base or {}

        if self.modo == MODO_WEB:
            return self._conectar_web()

        return self._conectar_rdp(variables_base, host, wait_time)

    def desconectar(self, wait_time=None) -> bool:
        if self.modo == MODO_WEB:
            if self._session:
                self._session.cerrar()
                self._session = None
                logger.info("🧹 Escritorio web cerrado (navegador)")
                return True

            logger.info("⏭️ Teardown web omitido: no hay sesión activa")
            return False

        proceso = EnvConfig.DESKTOP_PROCCESS

        if not proceso:
            logger.info("⏭️ Teardown RDP omitido: DESKTOP_PROCCESS no configurado")
            return False

        segundos = wait_time if wait_time is not None else 3
        cerrado = self.app_tools.cerrar_proceso_remoto(proceso, wait_time=segundos)
        logger.info("🖥️ Teardown RDP: proceso '%s' cerrado=%s", proceso, cerrado)
        return cerrado

    def esta_activa(self):
        if self.modo == MODO_WEB:
            return self._session is not None and self._session.esta_activa()

        return True

    @property
    def page(self):
        if not self._session:
            return None

        return self._session.page

    @property
    def session(self):
        return self._session

    def run(self, coro):
        if not self._session:
            raise RuntimeError("No existe una sesión web activa.")

        return self._session.run(coro)

    def _conectar_rdp(self, variables_base: dict, host: str | None = None, wait_time=None) -> bool:
        host = (
            host
            or variables_base.get("host_rdp")
            or variables_base.get("terminal_ruta")
            or EnvConfig.TERMINAL_RUTA
        )

        user = variables_base.get("usuario_rdp")
        password = variables_base.get("clave_rdp")

        if not host:
            raise ValueError("Host RDP no configurado.")

        conectado = self.app_tools.conectar_rdp(
            host=host,
            user=user,
            password=password,
            wait_time=wait_time,
        )

        if not conectado:
            raise RPAExceptions.ConexionFallidaException("No se pudo iniciar conexión RDP.")

        logger.info("🖥️ Conexión RDP iniciada")
        return True

    def _conectar_web(self) -> bool:
        if self.esta_activa():
            logger.info("🌐 Reutilizando sesión web")
            return True

        from infrastructure.browser.browser_session import BrowserSession

        self._session = BrowserSession(
            vida="sesion",
            storage_file=ESCRITORIO_STORAGE,
            remember_session=False,
            **BROWSER_ESCRITORIO_WEB_FULLSCREEN,
        )

        self._session.abrir()
        logger.info("🌐 Browser escritorio iniciado")
        return True

    def esperar_ancla(self, wait_time=None):
        ancla = self._resolver_ancla()

        if not ancla:
            segundos = wait_time if wait_time is not None else 10
            time.sleep(segundos)
            return

        if self._locator is None:
            from shared.tools.image_locator import ImageLocator
            self._locator = ImageLocator()

        timeout = max(float(wait_time or 0), EnvConfig.LOCATOR_TIMEOUT)
        box = self._locator.localizar(ancla, nombre_logico="ancla_escritorio", timeout=timeout)

        if box is None:
            raise RPAExceptions.ConexionFallidaException("No se encontró ancla de escritorio.")

    @staticmethod
    def _resolver_ancla():
        val = EnvConfig.DESKTOP_ANCHOR_IMAGE

        if not val:
            return None

        if os.path.isabs(val):
            return val if os.path.exists(val) else None

        candidato = os.path.join(IMAGES_DIR, val)

        if os.path.exists(candidato):
            return candidato

        return val if os.path.exists(val) else None
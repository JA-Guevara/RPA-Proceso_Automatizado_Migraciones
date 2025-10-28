import logging
from datetime import datetime
from shared.tools.flow_loader import FlowLoader
from config.images import ImagePaths
from core.action_executor.desktop_executor import DesktopExecutor
from core.action_executor.web_executor import WebExecutor
from config.selectors import WebSelectors
from infrastructure.browser.browser_manager import BrowserManager
from shared.tools.exceptions import RPAExceptions


class ActionBase:

    def __init__(self, variables_base: dict, contexto: dict, flow_name: str, executor_type: str = "desktop"):
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")

        self.variables_base = variables_base or {}
        self.contexto = contexto or {}
        self.executor_type = executor_type.lower()
        self.flow_data = FlowLoader.load(flow_name)

        if self.executor_type == "desktop":
            image_map = ImagePaths.get_all()
            self.executor = DesktopExecutor(
                flow=self.flow_data,
                image_map=image_map,
                variables_base=self.variables_base,
                contexto=self.contexto
            )
            self.clicker = self.executor.clicker
            self.app_tools = self.executor.app_tools
            self.extractor = self.executor.extractor

        elif self.executor_type == "web":
            self.browser_manager = BrowserManager(headless=False)
            self.executor = WebExecutor(
                flow=self.flow_data,
                selectors=WebSelectors.get_all(),
                variables_base=self.variables_base,
                contexto=self.contexto,
                browser_manager=self.browser_manager
            )
            self.page = getattr(self.executor, "page", None)

        else:
            raise ValueError(f"❌ Executor_type desconocido: {self.executor_type}")


    def hora_inicio(self):
        """Marca la hora de inicio del módulo actual."""
        clave = f"fecha_hora_inicio_{self.__class__.__name__.lower()}"
        self.contexto[clave] = datetime.now()
        self.logger.info(f"⏱️ Inicio de {self.__class__.__name__} registrado en {clave}")

    def hora_fin(self):
        """Marca la hora de fin del módulo actual."""
        clave = f"fecha_hora_fin_{self.__class__.__name__.lower()}"
        self.contexto[clave] = datetime.now()
        self.logger.info(f"⏱️ Fin de {self.__class__.__name__} registrado en {clave}")

    def registrar_observacion(self, mensaje: str, tipo: str = "info"):
        """Guarda una observación contextual (info, warning o error)."""
        nombre_accion = self.__class__.__name__
        mensaje_completo = f"[{nombre_accion}] {mensaje}"

        self.contexto["mensaje_observacion_rpa"] = mensaje_completo
        self.contexto["fecha_hora_observacion_rpa"] = datetime.now()

        if tipo == "error":
            self.logger.error(f"🛑 Observación registrada (error): {mensaje_completo}")
        elif tipo == "warning":
            self.logger.warning(f"⚠️ Observación registrada (warning): {mensaje_completo}")
        else:
            self.logger.info(f"📝 Observación registrada: {mensaje_completo}")



    def manejar_excepcion(self, excepcion: Exception):
        try:
            if isinstance(excepcion, RPAExceptions.ErrorBaseException):
                self.contexto["estado_final"] = excepcion.tipo
                self.contexto["observaciones_exception"] = str(excepcion)
                self.contexto["requiere_notificacion_exception"] = True

                self.logger.critical(
                    f"🟥 Excepción RPA [{excepcion.tipo}] en {self.__class__.__name__}: {excepcion}"
                )
                raise excepcion
            else:
                self.contexto["estado_final"] = "ERROR_GENERAL"
                self.contexto["observaciones_exception"] = str(excepcion)
                self.contexto["requiere_notificacion_exception"] = True
                self.logger.error(
                    f"💣 Error no controlado en {self.__class__.__name__}: {excepcion}",
                    exc_info=True
                )
                raise RPAExceptions.FlujoException(str(excepcion), contexto=self.contexto)

        except Exception as e:
            # --- Log final por seguridad: evita que se pierda el error
            self.logger.exception(f"💥 Error al manejar excepción en {self.__class__.__name__}: {e}")
            raise

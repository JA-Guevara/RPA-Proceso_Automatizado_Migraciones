import logging
from datetime import datetime

from shared.tools.exceptions import RPAExceptions


class BaseAction:

    def __init__(
        self,
        variables_base: dict,
        contexto: dict | None = None,
    ):
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )

        self.variables_base = variables_base or {}
        self.contexto = contexto or {}

    def var(self, clave: str, default=None):
        return self.contexto.get(
            clave,
            self.variables_base.get(clave, default)
        )

    def hora_inicio(self):
        clave = f"fecha_hora_inicio_{self.__class__.__name__.lower()}"
        self.contexto[clave] = datetime.now()

        self.logger.info(
            f"⏱️ Inicio de {self.__class__.__name__} registrado en {clave}"
        )

    def hora_fin(self):
        clave = f"fecha_hora_fin_{self.__class__.__name__.lower()}"
        self.contexto[clave] = datetime.now()

        self.logger.info(
            f"⏱️ Fin de {self.__class__.__name__} registrado en {clave}"
        )

    def registrar_observacion(
        self,
        mensaje: str,
        tipo: str = "info",
    ):
        nombre_accion = self.__class__.__name__

        mensaje_completo = (
            f"[{nombre_accion}] {mensaje}"
        )

        self.contexto[
            "mensaje_observacion_rpa"
        ] = mensaje_completo

        self.contexto[
            "fecha_hora_observacion_rpa"
        ] = datetime.now()

        if tipo == "error":
            self.logger.error(mensaje_completo)

        elif tipo == "warning":
            self.logger.warning(mensaje_completo)

        else:
            self.logger.info(mensaje_completo)

    def manejar_excepcion(
        self,
        excepcion: Exception,
    ):
        try:

            if isinstance(
                excepcion,
                RPAExceptions.ErrorBaseException,
            ):

                self.contexto["estado_final"] = excepcion.tipo
                self.contexto["observaciones_exception"] = str(excepcion)
                self.contexto["requiere_notificacion_exception"] = True

                raise excepcion

            self.contexto["estado_final"] = "ERROR_GENERAL"
            self.contexto["observaciones_exception"] = str(excepcion)
            self.contexto["requiere_notificacion_exception"] = True

            raise RPAExceptions.FlujoException(
                f"{excepcion.__class__.__name__}: {excepcion}",
                contexto=self.contexto,
            )

        except Exception:
            self.logger.exception(
                f"💥 Error en {self.__class__.__name__}"
            )
            raise
import logging
from datetime import datetime
from typing import Optional, Tuple

import pyautogui
from pywinauto.keyboard import send_keys

from shared.tools.app_tools import AppTools
from shared.tools.clipboard import clipboard_service


logger = logging.getLogger(__name__)


class BasicTools:
    def __init__(self, timeout: int = 10, confidence: float = 0.9):
        self.timeout = timeout
        self.confidence = confidence
        self.app_tools = AppTools()

    def copiar_texto_actual(
        self,
        seleccionar_todo: bool = True,
        limpiar: bool = True,
        mayusculas: bool = False,
        usar_real: bool = True,
        timeout: float | None = None,
        spec: dict | None = None,
    ) -> str:
        """
        Copia el texto de la aplicacion remota.

        El backend lo elige clipboard_service segun CONEXION_ESCRITORIO: en web
        intercepta onclipboard del cliente Guacamole; en rdp conserva el
        centinela + estabilizacion sobre pyperclip.

        `spec` es opcional: si viene, un valor que no cumple la forma esperada
        se descarta y se sigue esperando en vez de aceptarlo.

        Ya NO devuelve "" ante un fallo de lectura: con CLIPBOARD_FAIL_CLOSED
        propaga excepcion tecnica para que TaskManagerMigracion recupere la
        sesion en lugar de seguir con informacion vieja o vacia.
        """
        texto = clipboard_service.leer(
            spec=spec,
            timeout=timeout,
            seleccionar_todo=seleccionar_todo,
        )

        if limpiar:
            texto = texto.strip()
        if mayusculas:
            texto = texto.upper()

        logger.info(f"📋 Texto copiado: '{texto[:60]}...'")
        return texto

    def pegar_texto_actual(self, delay: float = 0.1) -> bool:
        try:
            if not self.app_tools.presionar_combinacion("ctrl", "v"):
                return False

            self.app_tools.esperar(delay)
            logger.info("📋 Texto pegado correctamente.")
            return True

        except Exception as e:
            logger.error(f"❌ Error al pegar texto: {e}", exc_info=True)
            return False

    def seleccionar_todo(self, usar_real: bool = True) -> bool:
        try:
            if usar_real:
                ok = self.app_tools.presionar_combinacion_real("ctrl", "a")
            else:
                ok = self.app_tools.presionar_combinacion("ctrl", "a")

            if not ok:
                return False

            self.app_tools.esperar(0.15)
            logger.info("✅ Todo el texto fue seleccionado.")
            return True

        except Exception as e:
            logger.error(f"❌ Error al seleccionar todo el texto: {e}", exc_info=True)
            return False

    def escribir_texto_clipboard(self, texto: str, delay: float = 0.001) -> bool:
        """
        Escribe en el campo enfocado del remoto.

        En web ya no hay `esperar(0.1)` a ciegas: el backend confirma o espera
        el settle antes del Ctrl+V, y el router puede decidir tipear en vez de
        pegar si el valor es corto y ASCII.

        Se quito el gc.collect() por escritura: era una pausa global del
        interprete en cada campo, sin beneficio.
        """
        texto = self._normalizar_texto(texto)
        ok = clipboard_service.escribir_valor(texto, seleccionar_todo=True)
        if ok and delay:
            self.app_tools.esperar(delay)
        return ok

    def escribir_texto_simulado(self, texto: str, delay: float = 0.0) -> bool:
        try:
            texto = self._normalizar_texto(texto)
            pyautogui.write(texto, interval=delay)
            logger.info(f"⌨️ Texto simulado escrito: '{texto[:60]}...'")
            return True

        except Exception as e:
            logger.error(f"❌ Error al escribir texto simulado: {e}", exc_info=True)
            return False

    def escribir_texto_real(self, texto: str, delay: float = 0.001) -> bool:
        try:
            texto = self._normalizar_texto(texto)
            send_keys(texto, with_spaces=True, pause=delay)
            logger.info(f"⌨️ Texto real escrito con send_keys: '{texto[:60]}...'")
            return True

        except Exception as e:
            logger.error(f"❌ Error al escribir texto real: {e}", exc_info=True)
            return False

    def presionar_f2_y_pegar(self, delay: float = 0.1) -> bool:
        try:
            if not self.app_tools.presionar_tecla_real("f2"):
                return False

            self.app_tools.esperar(0.1)
            return self.pegar_texto_actual(delay)

        except Exception as e:
            logger.error(f"❌ Error al presionar F2 y pegar: {e}", exc_info=True)
            return False

    def calcular_antiguedad(self, fecha_str: str) -> Optional[Tuple[int, int, int]]:
        try:
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
            hoy = datetime.now()

            if fecha > hoy:
                logger.warning(f"⚠️ La fecha '{fecha_str}' es futura. Se devuelve 0.")
                return 0, 0, 0

            delta = hoy - fecha
            total_dias = delta.days

            anios = total_dias // 365
            meses = total_dias // 30
            dias = total_dias

            return anios, meses, dias

        except Exception as e:
            logger.error(f"❌ Error al calcular antigüedad: {e}", exc_info=True)
            return None

    def _normalizar_texto(self, texto) -> str:
        if isinstance(texto, datetime):
            return texto.strftime("%d/%m/%Y")

        if texto is None:
            return ""

        return str(texto)
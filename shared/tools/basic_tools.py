import gc
import logging
from datetime import datetime
from typing import Optional, Tuple

import pyautogui
import pyperclip
from pywinauto.keyboard import send_keys

from shared.tools.app_tools import AppTools
from shared.tools.guacamole_clipboard_sync import intentar_copiar_guacamole_sync,copiar_desde_app_activa_sync


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
    ) -> str:
        try:
            if seleccionar_todo:
                if not self.seleccionar_todo(usar_real=usar_real):
                    return ""

            texto = copiar_desde_app_activa_sync(
                usar_real=usar_real,
                timeout=timeout,
                limpiar=limpiar,
                mayusculas=mayusculas,
            )

            logger.info(f"📋 Texto copiado: '{texto[:60]}...'")
            return texto

        except Exception as e:
            logger.error(f"❌ Error al copiar texto actual: {e}", exc_info=True)
            return ""

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
        try:
            logger.warning(
                "🧪 BASIC_TOOLS_ACTIVO archivo=%s metodo=escribir_texto_clipboard_v2",
                __file__,
            )

            texto = self._normalizar_texto(texto)

            # 1. Copia normal al portapapeles local
            pyperclip.copy(texto)
            logger.info(f"📋 Texto copiado al portapapeles local: '{texto[:60]}...'")
            logger.info(f"📋 Validación local pyperclip: '{pyperclip.paste()[:60]}...'")

            # 2. Refuerzo silencioso para Guacamole
            ok_guacamole = intentar_copiar_guacamole_sync(texto)
            logger.info("📋 Refuerzo clipboard Guacamole aplicado=%s", ok_guacamole)

            # Reafirmar clipboard local después del bridge.
            # Esto evita que el intento con navegador/Guacamole deje un valor viejo o extraño.
            pyperclip.copy(texto)
            logger.info(f"📋 Clipboard local reafirmado antes de Ctrl+V: '{pyperclip.paste()[:60]}...'")

            self.app_tools.esperar(0.1)

            if not self.app_tools.presionar_combinacion_real("ctrl", "a"):
                logger.error("❌ No se pudo seleccionar el texto actual con ctrl+a")
                gc.collect()
                return False

            if not self.app_tools.presionar_combinacion_real("ctrl", "v"):
                logger.error("❌ No se pudo pegar texto con ctrl+v")
                gc.collect()
                return False

            self.app_tools.esperar(delay)
            logger.info(f"📋 Texto pegado con clipboard: '{texto[:40]}...'")

            gc.collect()
            return True

        except Exception as e:
            logger.error(f"❌ Error al pegar con clipboard: {e}", exc_info=True)
            gc.collect()
            return False

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
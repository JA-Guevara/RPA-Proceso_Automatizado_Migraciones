import gc
import logging
import pyautogui
import pyperclip
from datetime import datetime,timedelta
from typing import Optional, Tuple
from pywinauto.keyboard import send_keys
from shared.tools.region_locator import RegionLocator
from shared.tools.app_tools import AppTools
from shared.tools.exceptions import RPAExceptions

logger = logging.getLogger(__name__)

class BasicTools:
    def __init__(self, timeout: int = 10, confidence: float = 0.9):
        self.timeout = timeout
        self.confidence = confidence
        self.region_locator = RegionLocator()
        self.app_tools = AppTools()

    def copiar_texto_actual(self) -> str:
        try:
            self.seleccionar_todo()
            self.app_tools.presionar_combinacion("ctrl", "c")
            self.app_tools.esperar(0.1)
            texto = pyperclip.paste().strip()
            logger.info(f"📋 Texto copiado: '{texto[:60]}...'")
            return texto
        except Exception as e:
            logger.error(f"❌ Error al copiar texto actual: {e}", exc_info=True)
            return ""


    def pegar_texto_actual(self, delay: float = 0.1):
        try:
            self.app_tools.presionar_combinacion("ctrl", "v")
            self.app_tools.esperar(delay)
            logger.info("📋 Texto pegado correctamente.")
            return True
        except Exception as e:
            logger.error(f"❌ Error al pegar texto: {e}", exc_info=True)
            return False

    def seleccionar_todo(self):
        try:
            self.app_tools.presionar_combinacion("ctrl", "a")
            self.app_tools.esperar(0.1)
            logger.info("✅ Todo el texto fue seleccionado.")
        except Exception as e:
            logger.error(f"❌ Error al seleccionar todo el texto: {e}", exc_info=True)

    def escribir_directo_clipboard(self, texto: str, delay: float = 0.1):
        try:
            pyperclip.copy(texto)
            logger.info(f"📋 Texto copiado al portapapeles: '{texto[:60]}...'")
            return self.pegar_texto_actual(delay)
        except Exception as e:
            logger.error(f"❌ Error al escribir desde clipboard: {e}", exc_info=True)
            return False

    def escribir_texto_simulado(self, texto: str, delay: float = 0.0):
        try:
            if isinstance(texto, datetime):
                texto = texto.strftime("%d/%m/%Y")
            pyautogui.write(str(texto), interval=delay)
            logger.info(f"⌨️ Texto simulado escrito: '{texto[:60]}...'")
            return True
        except Exception as e:
            logger.error(f"❌ Error al escribir texto simulado: {e}", exc_info=True)
            return False

    def escribir_texto_real(self, texto: str, delay: float = 0.001):
        try:
            if isinstance(texto, datetime):
                texto = texto.strftime("%d/%m/%Y")
            send_keys(texto, with_spaces=True, pause=delay)
            logger.info(f"⌨️ Texto real escrito con send_keys: '{texto[:60]}...'")
            return True
        except Exception as e:
            logger.error(f"❌ Error al escribir texto real: {e}", exc_info=True)
            return False

    def presionar_f2_y_pegar(self, delay: float = 0.1):
        try:
            self.app_tools.presionar_tecla_real("f2")
            self.app_tools.esperar(0.1)
            return self.pegar_texto_actual(delay)
        except Exception as e:
            logger.error(f"❌ Error al presionar F2 y pegar: {e}", exc_info=True)
            return False
        
    def escribir_texto_clipboard(self, texto: str, delay: float = 0.001) -> bool:
        try:
            pyperclip.copy(texto)
            self.app_tools.presionar_combinacion_real("ctrl", "a")
            self.app_tools.esperar(0.1)
            self.app_tools.presionar_combinacion_real("ctrl", "v")
            self.app_tools.esperar(delay)
            logger.info(f"📋 Texto pegado con clipboard: '{texto[:40]}...'")
            gc.collect()
            return True
        except Exception as e:
            logger.error(f"❌ Error al pegar con clipboard: {e}", exc_info=True)
            gc.collect()
            return False

    def calcular_antiguedad(self, fecha_str: str, formato: str = "%m/%d/%Y") -> Optional[Tuple[int, int, int]]:
        try:
            fecha = datetime.strptime(fecha_str.strip().replace("...", ""), formato)
            hoy = datetime.now()

            if fecha > hoy:
                logger.warning(f"⚠️ La fecha '{fecha_str}' es futura. Se devuelve 0.")
                return 0, 0, 0

            # Diferencia total en días
            total_dias = (hoy - fecha).days

            # Cálculos coherentes
            # 1 año = 365.25 días promedio (cuenta años bisiestos)
            anios = int(total_dias // 365.25)
            meses = int(total_dias // 30.44)  # promedio mensual realista
            dias = total_dias

            return anios, meses, dias

        except Exception as e:
            logger.error(f"❌ Error al calcular antigüedad de '{fecha_str}' con formato '{formato}': {e}", exc_info=True)
            return None
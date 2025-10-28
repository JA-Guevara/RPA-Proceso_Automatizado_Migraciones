import pyautogui
import time
import gc
import logging
from typing import Optional, Tuple
from typing import Union
from shared.tools.region_locator import RegionLocator
from shared.tools.app_tools import AppTools
from shared.tools.exceptions import RPAExceptions

from shared.tools.basic_tools import BasicTools

logger = logging.getLogger(__name__)

class ClickTools:
    def __init__(self, timeout: int = 10, confidence: float = 0.9):
        self.timeout = timeout
        self.confidence = confidence
        self.region_locator = RegionLocator()
        self.app_tools = AppTools()
        self.basic_tools = BasicTools()

    def _localizar_para_click(self, image_path: str, nombre_logico: str, t_region: float = 3.0):
        try:
            region = self.region_locator.obtener_region(nombre_logico)
            if region:
                region_box = (region['x'], region['y'], region['width'], region['height'])
                inicio = time.time()
                while time.time() - inicio < t_region:
                    try:
                        pos = pyautogui.locateOnScreen(image_path, confidence=self.confidence, region=region_box)
                        if pos:
                            return (pos.left, pos.top, pos.width, pos.height)
                    except Exception:
                        pass

            inicio_total = time.time()
            while time.time() - inicio_total < self.timeout:
                try:
                    pos = pyautogui.locateOnScreen(image_path, confidence=self.confidence)
                    if pos:
                        nueva_region = (pos.left, pos.top, pos.width, pos.height)
                        self.region_locator.guardar_region(nombre_logico, nueva_region)
                        logger.info(f"🔁 Región actualizada para '{nombre_logico}': {nueva_region}")
                        return nueva_region
                except Exception:
                    pass
            return None

        except Exception as e:
            logger.error(f"❌ Error en _localizar_para_click: {e}", exc_info=True)
            return None

    def hacer_clic(
    self,
    target: Union[str, tuple],
    clicks: int = 1,
    offset_x: int = 0,
    offset_y: int = 0,
    usar_inicio: bool = False,
    usar_imagen: bool = True,
    raise_error: bool = True,
    nombre_logico: str = None,
    t_region: float = 3.0,
    transitorio: bool = False,
    wait_after_click: float = 0.5,       
    wait_timeout: float = 30.0            
) -> bool:
        try:
            x = y = None

            if usar_imagen and isinstance(target, str):
                nombre_logico = nombre_logico or target

                if transitorio:
                    logger.info(f"🔍 Buscando imagen (modo transitorio) '{nombre_logico}'...")
                    caja = pyautogui.locateOnScreen(target, confidence=self.confidence)
                    if not caja:
                        logger.warning(f"❌ No se encontró imagen transitoria: {target}")
                        return False
                else:
                    caja = self.region_locator.buscar_o_actualizar_region(
                        image_path=target,
                        nombre_logico=nombre_logico,
                        confidence=self.confidence,
                        t_region=t_region,
                        t_total=self.timeout
                    )
                    if not caja:
                        logger.warning(f"❌ No se encontró imagen: {target} [{nombre_logico}]")
                        return False

                left, top, width, height = caja
                x = left if usar_inicio else left + width // 2
                y = top if usar_inicio else top + height // 2

            elif isinstance(target, tuple) and len(target) == 2:
                x, y = target
                if not nombre_logico:
                    nombre_logico = "coordenadas"
            else:
                logger.error("⚠️ Target inválido: debe ser ruta de imagen o tupla (x, y).")
                return False

            x += offset_x
            y += offset_y

            logger.info(f"🗉 Haciendo clic en '{nombre_logico}' ({x},{y}) clicks={clicks}")
            pyautogui.click(x, y, clicks=clicks)

            start = time.time()
            while time.time() - start < wait_timeout:
                break

            gc.collect()
            return True

        except RPAExceptions.ErrorBaseException:
            raise
        except Exception as e:
            msg = f"💥 Error inesperado en hacer_clic(): {e}"
            logger.error(msg, exc_info=True)
            raise RPAExceptions.InterfazException(msg)

    def clic_y_escribir(self, target: Union[str, tuple], texto: str, delay: float = 0,
                        offset_x: int = 0, offset_y: int = 0, clicks: int = 1,
                        nombre_logico: str = None, transitorio: bool = False) -> bool:
        try:
            clic_realizado = self.hacer_clic(
                target,
                offset_x=offset_x,
                offset_y=offset_y,
                clicks=clicks,
                usar_imagen=isinstance(target, str),
                raise_error=True,
                nombre_logico=nombre_logico,
                transitorio=transitorio
            )
            if not clic_realizado:
                return False

            return self.basic_tools.escribir_texto_clipboard(
                texto,
                delay=delay,
            )

        except Exception as e:
            logger.error(f"❌ Error en clic_y_escribir: {e}", exc_info=True)
            return False

    def clic_y_escribir_tradicional(self, target: Union[str, tuple], texto: str, delay: float = 0,
                                     offset_x: int = 0, offset_y: int = 0, clicks: int = 1, nombre_logico: str = None, transitorio: bool = False) -> bool:
        try:
            clic_realizado = self.hacer_clic(
                target, offset_x=offset_x, offset_y=offset_y, clicks=clicks,
                usar_imagen=isinstance(target, str), raise_error=True, nombre_logico=nombre_logico, transitorio=transitorio)
            if not clic_realizado:
                return False
            self.basic_tools.escribir_texto_simulado(texto, delay=delay)
            return True
        except Exception as e:
            logger.error(f"Error en clic_y_escribir_tradicional: {e}", exc_info=True)
            return False


    def buscar_imagen(self, target: str, nombre_logico: Optional[str] = None,
                  usar_inicio: bool = False, raise_error: bool = True,
                  timeout: float = None, retry_delay: float = 0.2, transitorio: bool = False
                 ) -> Optional[Tuple[int, int, int, int]]:
        try:
            nombre_logico = nombre_logico or target
            imagen_path = target
            timeout = timeout if timeout is not None else self.timeout
            start_time = time.time()

            while time.time() - start_time < timeout:
                try:
                    region = self.region_locator.obtener_region(nombre_logico) if not transitorio else None

                    if region:
                        region_box = (region['x'], region['y'], region['width'], region['height'])
                        posicion = pyautogui.locateOnScreen(imagen_path, confidence=self.confidence, region=region_box)
                    else:
                        posicion = pyautogui.locateOnScreen(imagen_path, confidence=self.confidence)

                    if posicion:
                        if not transitorio:
                            nueva_region = (posicion.left, posicion.top, posicion.width, posicion.height)
                            self.region_locator.guardar_region(nombre_logico, nueva_region)
                            logger.info(f"📌 Región guardada para '{nombre_logico}': {nueva_region}")
                        return (posicion.left, posicion.top, posicion.width, posicion.height)

                except Exception as e:
                    logger.debug(f"⚠️ Error parcial al buscar imagen: {e}")

                self.app_tools.esperar(retry_delay)

            # --- Si termina sin encontrar ---
            msg = f"❌ Imagen no encontrada al buscar: {nombre_logico}"
            logger.warning(msg)
            if raise_error:
                raise RPAExceptions.ImagenNoEncontradaException(msg)
            return None

        except RPAExceptions.ErrorBaseException:
            raise
        except Exception as e:
            msg = f"💥 Error inesperado en buscar_imagen(): {e}"
            logger.error(msg, exc_info=True)
            raise RPAExceptions.InterfazException(msg)

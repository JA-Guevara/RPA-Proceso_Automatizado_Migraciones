
import logging
import time
from typing import Optional, Tuple, Union

import pyautogui

from shared.tools.app_tools import AppTools
from shared.tools.basic_tools import BasicTools
from shared.tools.exceptions import RPAExceptions
from shared.tools.image_locator import ImageLocator, default_locator

logger = logging.getLogger(__name__)


class ClickTools:
    def __init__(self, timeout: int = 10, confidence: float = 0.9, locator: ImageLocator = None):
        self.timeout = timeout
        self.confidence = confidence
        self.locator = locator or default_locator
        self.app_tools = AppTools()
        self.basic_tools = BasicTools()

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
        t_region: float = None,
        transitorio: bool = False,
        wait_after_click: float = 0.5,
        wait_timeout: float = None,
        timeout: float = None,
    ) -> bool:
        try:
            x = y = None

            if usar_imagen and isinstance(target, str):
                nombre_logico = nombre_logico or target
                timeout_efectivo = timeout if timeout is not None else (
                    self.locator.timeout_transitorio if transitorio else self.timeout
                )

                caja = self.locator.localizar(
                    target,
                    nombre_logico=nombre_logico,
                    timeout=timeout_efectivo,
                    confidence=self.confidence,
                    log_miss_como_warning=not transitorio,
                )

                if not caja:
                    if transitorio or not raise_error:
                        logger.info(f"⏭️ Paso opcional sin imagen: '{nombre_logico}' → se omite.")
                        return False

                    raise RPAExceptions.ImagenNoEncontradaException(
                        f"Elemento requerido no encontrado: '{nombre_logico}' ({target})"
                    )

                left, top, width, height = caja

                if usar_inicio:
                    x = left
                    y = top
                else:
                    x = left + width // 2
                    y = top + height // 2

                x += offset_x
                y += offset_y

            elif isinstance(target, tuple) and len(target) == 2:
                x = target[0] + offset_x
                y = target[1] + offset_y
                nombre_logico = nombre_logico or "coordenadas"

            else:
                msg = f"Target inválido en hacer_clic: {target!r} (imagen o tupla (x, y))."
                if raise_error and not transitorio:
                    raise RPAExceptions.InterfazException(msg)

                logger.error(f"⚠️ {msg}")
                return False

            logger.info(f"🖱️ Clic en '{nombre_logico}' ({x},{y}) clicks={clicks}")
            self._click_estable(x, y, clicks=clicks)

            if wait_after_click and wait_after_click > 0:
                time.sleep(wait_after_click)

            return True

        except RPAExceptions.ErrorBaseException:
            raise

        except Exception as e:
            msg = f"Error inesperado en hacer_clic('{nombre_logico or target}'): {e}"
            logger.error(f"💥 {msg}", exc_info=True)
            raise RPAExceptions.InterfazException(msg)

    def clic_y_escribir(
        self,
        target: Union[str, tuple],
        texto: str,
        delay: float = 0,
        offset_x: int = 0,
        offset_y: int = 0,
        clicks: int = 1,
        nombre_logico: str = None,
        transitorio: bool = False,
        raise_error: bool = True,
        timeout: float = None,
    ) -> bool:
        clic_realizado = self.hacer_clic(
            target,
            offset_x=offset_x,
            offset_y=offset_y,
            clicks=clicks,
            usar_imagen=isinstance(target, str),
            raise_error=raise_error,
            nombre_logico=nombre_logico,
            transitorio=transitorio,
            timeout=timeout,
        )

        if not clic_realizado:
            return False

        return self.basic_tools.escribir_texto_clipboard(texto, delay=delay)

    def clic_y_escribir_tradicional(
        self,
        target: Union[str, tuple],
        texto: str,
        delay: float = 0,
        offset_x: int = 0,
        offset_y: int = 0,
        clicks: int = 1,
        nombre_logico: str = None,
        transitorio: bool = False,
        raise_error: bool = True,
        timeout: float = None,
    ) -> bool:
        clic_realizado = self.hacer_clic(
            target,
            offset_x=offset_x,
            offset_y=offset_y,
            clicks=clicks,
            usar_imagen=isinstance(target, str),
            raise_error=raise_error,
            nombre_logico=nombre_logico,
            transitorio=transitorio,
            timeout=timeout,
        )

        if not clic_realizado:
            return False

        return self.basic_tools.escribir_texto_simulado(texto, delay=delay)

    def buscar_imagen(
        self,
        target: str,
        nombre_logico: Optional[str] = None,
        usar_inicio: bool = False,
        raise_error: bool = True,
        timeout: float = None,
        retry_delay: float = 0.2,
        transitorio: bool = False,
        confidence: Optional[float] = None,
    ) -> Optional[Tuple[int, int, int, int]]:
        nombre_logico = nombre_logico or target
        timeout_efectivo = timeout if timeout is not None else (
            self.locator.timeout_transitorio if transitorio else self.timeout
        )

        caja = self.locator.localizar(
            target,
            nombre_logico=nombre_logico,
            timeout=timeout_efectivo,
            confidence=confidence if confidence is not None else self.confidence,
            poll_interval=retry_delay,
            log_miss_como_warning=not transitorio,
        )

        if caja:
            return caja

        if raise_error and not transitorio:
            raise RPAExceptions.ImagenNoEncontradaException(
                f"Imagen no encontrada al buscar: {nombre_logico}"
            )

        return None

    def _click_estable(self, x: int, y: int, clicks: int = 1) -> None:
        pyautogui.moveTo(x, y, duration=0.05)

        for _ in range(max(int(clicks), 1)):
            pyautogui.mouseDown()
            time.sleep(0.08)
            pyautogui.mouseUp()

            if clicks > 1:
                time.sleep(0.15)

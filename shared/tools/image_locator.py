import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import pyautogui

from config.config import BASE_DIR, EnvConfig
from shared.tools.exceptions import RPAExceptions

logger = logging.getLogger(__name__)

Box = Tuple[int, int, int, int]
EVIDENCIA_DIR = Path(BASE_DIR) / "storage" / "debug_failures"
_NOT_FOUND = getattr(pyautogui, "ImageNotFoundException", None) or tuple()

class ImageLocator:
    _variantes_cache: dict = {}

    def __init__(
        self,
        timeout: float = None,
        timeout_transitorio: float = None,
        poll_interval: float = None,
        confidence: float = None,
        grayscale: bool = None,
        confidence_fallback: Optional[float] = None,
    ):
        self.timeout = timeout if timeout is not None else EnvConfig.LOCATOR_TIMEOUT
        self.timeout_transitorio = (
            timeout_transitorio if timeout_transitorio is not None
            else EnvConfig.LOCATOR_TIMEOUT_TRANSITORIO
        )
        self.poll_interval = (
            poll_interval if poll_interval is not None
            else EnvConfig.LOCATOR_POLL_INTERVAL
        )
        self.confidence = confidence if confidence is not None else EnvConfig.LOCATOR_CONFIDENCE
        self.grayscale = grayscale if grayscale is not None else EnvConfig.LOCATOR_GRAYSCALE
        self.confidence_fallback = (
            confidence_fallback if confidence_fallback is not None
            else EnvConfig.LOCATOR_CONFIDENCE_FALLBACK
        )

        self._stats = {"hits": 0, "misses": 0, "fallback_hits": 0, "ms_total": 0.0}

    # ------------------------------------------------------------------ API

    def localizar(
        self,
        imagen: str,
        nombre_logico: Optional[str] = None,
        timeout: Optional[float] = None,
        confidence: Optional[float] = None,
        poll_interval: Optional[float] = None,
        log_miss_como_warning: bool = True,
    ) -> Optional[Box]:

        nombre = nombre_logico or imagen
        timeout = timeout if timeout is not None else self.timeout
        confidence = confidence if confidence is not None else self.confidence
        poll = poll_interval if poll_interval is not None else self.poll_interval

        self._validar_plantilla(imagen, nombre)
        variantes = self._variantes(imagen)

        inicio = time.perf_counter()
        intentos = 0

        while True:
            intentos += 1
            box, variante = self._intento(variantes, confidence)
            elapsed = time.perf_counter() - inicio

            if box:
                ms = elapsed * 1000
                self._stats["hits"] += 1
                self._stats["ms_total"] += ms
                extra = f", variante={Path(variante).name}" if variante != imagen else ""
                logger.info(
                    f"🎯 '{nombre}' localizada en {ms:.0f}ms "
                    f"(intentos={intentos}, conf={confidence}{extra})"
                )
                return box

            if elapsed >= timeout:
                break

            time.sleep(poll)

        # --- Intento final con confianza reducida (si está configurado) ---
        if self.confidence_fallback and self.confidence_fallback < confidence:
            box, variante = self._intento(variantes, self.confidence_fallback)
            if box:
                self._stats["fallback_hits"] += 1
                logger.warning(
                    f"🟠 '{nombre}' SOLO se encontró con confianza reducida "
                    f"({self.confidence_fallback} < {confidence}). "
                    f"La plantilla está degradada → renovar captura: {variante}"
                )
                return box

        self._stats["misses"] += 1
        msg = f"Imagen no encontrada tras {timeout:.1f}s ({intentos} intentos): '{nombre}'"
        if log_miss_como_warning:
            evidencia = self._guardar_evidencia(nombre)
            if evidencia:
                msg += f" | 📸 evidencia: {evidencia}"
            logger.warning(f"❌ {msg}")
        else:
            logger.info(f"👀 {msg}")
        return None

    def esta_presente(
        self,
        imagen: str,
        nombre_logico: Optional[str] = None,
        timeout: float = 2,
        confidence: Optional[float] = None,
    ) -> bool:
        """Chequeo de presencia (para elementos opcionales/diálogos de error)."""
        return self.localizar(
            imagen,
            nombre_logico=nombre_logico,
            timeout=timeout,
            confidence=confidence,
            log_miss_como_warning=False,
        ) is not None

    @staticmethod
    def centro(box: Box, offset_x: int = 0, offset_y: int = 0) -> Tuple[int, int]:
        """Centro de la caja con offsets aplicados."""
        left, top, width, height = box
        return left + width // 2 + offset_x, top + height // 2 + offset_y

    def resumen(self) -> dict:
        """Métricas acumuladas de la sesión (hit-rate, tiempo medio)."""
        total = self._stats["hits"] + self._stats["misses"]
        return {
            **self._stats,
            "total": total,
            "hit_rate": round(self._stats["hits"] / total, 3) if total else None,
            "ms_promedio_hit": (
                round(self._stats["ms_total"] / self._stats["hits"], 1)
                if self._stats["hits"] else None
            ),
        }

    def log_resumen(self):
        logger.info(f"📊 ImageLocator resumen sesión: {self.resumen()}")

    # ------------------------------------------------------------ internos

    @staticmethod
    def _validar_plantilla(imagen: str, nombre: str):
        if not isinstance(imagen, str) or not imagen:
            raise RPAExceptions.InterfazException(
                f"Plantilla inválida para '{nombre}': se recibió {imagen!r}"
            )
        if not Path(imagen).is_file():
            raise RPAExceptions.InterfazException(
                f"La plantilla de '{nombre}' no existe en disco: {imagen}. "
                "Revisar config/images.py o el flow JSON."
            )

    def _variantes(self, imagen: str) -> List[str]:
        cache = ImageLocator._variantes_cache.get(imagen)
        if cache is not None:
            return cache

        base = Path(imagen)
        variantes = [imagen]
        try:
            variantes += sorted(
                str(v)
                for v in base.parent.glob(f"{base.stem}@*{base.suffix}")
                if v.is_file()
            )
        except Exception:
            pass

        if len(variantes) > 1:
            logger.info(f"🧩 {base.name}: {len(variantes) - 1} variante(s) detectadas")

        ImageLocator._variantes_cache[imagen] = variantes
        return variantes

    def _intento(self, variantes: List[str], confidence: float) -> Tuple[Optional[Box], Optional[str]]:
        """Una pasada de matching: prueba cada variante contra la pantalla."""
        for variante in variantes:
            try:
                box = pyautogui.locateOnScreen(
                    variante, confidence=confidence, grayscale=self.grayscale
                )
                if box:
                    return (box.left, box.top, box.width, box.height), variante
            except _NOT_FOUND:
                continue
            except Exception as e:
                # Captura de pantalla fallida (sesión bloqueada, etc.): se trata
                # como "no encontrado" pero queda rastro del motivo real.
                logger.debug(f"⚠️ locateOnScreen falló ({variante}): {e}")
        return None, None

    def _guardar_evidencia(self, nombre: str) -> Optional[str]:
        if not EnvConfig.LOCATOR_EVIDENCIA:
            return None
        try:
            EVIDENCIA_DIR.mkdir(parents=True, exist_ok=True)
            seguro = re.sub(r"[^A-Za-z0-9._-]+", "_", nombre)[:60]
            ruta = EVIDENCIA_DIR / f"miss_{datetime.now():%Y%m%d_%H%M%S%f}_{seguro}.png"
            pyautogui.screenshot().save(str(ruta))
            self._podar_evidencias()
            return str(ruta)
        except Exception as e:
            logger.debug(f"No se pudo guardar evidencia de fallo: {e}")
            return None

    @staticmethod
    def _podar_evidencias():
        try:
            archivos = sorted(
                EVIDENCIA_DIR.glob("miss_*.png"),
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )
            for viejo in archivos[EnvConfig.LOCATOR_EVIDENCIA_MAX:]:
                viejo.unlink()
        except Exception:
            pass


default_locator = ImageLocator()
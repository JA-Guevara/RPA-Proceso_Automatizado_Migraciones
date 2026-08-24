"""
Backend de portapapeles para modo RDP (mstsc).

Conserva EXACTAMENTE la mecánica que ya funcionaba: centinela local + espera de
estabilización sobre el portapapeles del host. En RDP el portapapeles es un
canal redirigido del propio SO, así que `pyperclip` y el portapapeles remoto son
prácticamente el mismo objeto y esta estrategia es correcta.

Los únicos agregados son aditivos y no cambian el resultado en el camino feliz:
  - `spec` opcional: si viene, un valor intermedio se descarta y se sigue
    esperando en vez de aceptarlo. Con spec=None el comportamiento es idéntico
    al original.
  - telemetría.
"""

from __future__ import annotations

import hashlib
import logging
import time
import uuid

import pyperclip

from shared.tools.exceptions import RPAExceptions
from shared.tools.clipboard import specs as S
from shared.tools.clipboard import telemetria as T

logger = logging.getLogger(__name__)


class PyperclipBackend:
    """Backend RDP. No conoce Guacamole ni Playwright."""

    nombre = "pyperclip"

    def __init__(self, cfg):
        self.cfg = cfg

    # ------------------------------------------------------------------ infra

    def instalar(self) -> dict:
        return {"ok": True, "backend": self.nombre, "yaEstaba": True}

    def salud(self) -> dict:
        return {"ok": True, "backend": self.nombre, "conectado": True, "sano": True}

    def exigir_tunel_sano(self) -> dict:
        return self.salud()

    def conexion_viva(self) -> bool:
        # En rdp no hay navegador que se pueda cerrar por debajo.
        return True

    def desconexiones(self) -> int:
        return 0

    def liberar_modificadores(self) -> None:
        return None

    # ---------------------------------------------------------------- lectura

    def leer(self, spec: dict | None = None, timeout: float | None = None,
             seleccionar_todo: bool = False) -> str:
        from shared.tools.app_tools import AppTools

        app = AppTools()
        timeout = float(timeout if timeout is not None else self.cfg.timeout_rdp)
        reintentos = max(1, int(self.cfg.reintentos))
        t_inicio = time.perf_counter()

        for intento in range(1, reintentos + 1):
            if intento > 1:
                T.registrar_reintento()

            if seleccionar_todo:
                if not app.presionar_combinacion_real("ctrl", "a"):
                    continue
                time.sleep(0.15)

            marca = f"__RPA_CLIPBOARD_SENTINEL_{uuid.uuid4()}__"
            pyperclip.copy(marca)
            time.sleep(0.15)

            if not app.presionar_combinacion_real("ctrl", "c"):
                logger.warning("⚠️ Ctrl+C falló intento=%s/%s", intento, reintentos)
                continue

            texto = self._esperar_estable(marca, timeout, spec)

            if texto:
                ms = (time.perf_counter() - t_inicio) * 1000
                T.registrar_lectura(ok=True, ms=ms)
                logger.info("📋 Texto copiado (rdp) len=%s", len(texto))
                return texto

            logger.warning(
                "⚠️ Portapapeles vacío/no sincronizado intento=%s/%s", intento, reintentos
            )

        T.registrar_lectura(ok=False, motivo="timeout")

        if self.cfg.fail_closed:
            raise RPAExceptions.TiempoEsperaExcedidoException(
                "No se pudo copiar texto desde la aplicación remota (rdp)."
            )

        logger.error("❌ No se pudo copiar texto desde app activa (rdp) → vacío")
        return ""

    def _esperar_estable(self, marca: str, timeout: float, spec: dict | None,
                         intervalo: float = 0.25, muestras_estables: int = 2) -> str:
        inicio = time.time()
        ultimo_hash = None
        ultimo_len = -1
        estables = 0
        mejor = ""

        while time.time() - inicio < timeout:
            time.sleep(intervalo)

            texto = pyperclip.paste() or ""

            if texto == marca or texto == "":
                continue

            # Aditivo: un valor que no cumple la forma esperada no se acepta;
            # se sigue esperando dentro del timeout.
            if spec is not None and not S.cumple(texto, spec):
                continue

            largo = len(texto)
            firma = hashlib.sha256(texto.encode("utf-8", errors="ignore")).hexdigest()

            if firma == ultimo_hash and largo == ultimo_len:
                estables += 1
            else:
                estables = 0
                ultimo_hash = firma
                ultimo_len = largo
                mejor = texto

            if estables >= muestras_estables:
                return mejor

        return mejor

    # -------------------------------------------------------------- escritura

    def escribir(self, texto: str, seleccionar_todo: bool = True,
                 pegar: bool = True) -> bool:
        from shared.tools.app_tools import AppTools

        app = AppTools()
        t0 = time.perf_counter()

        pyperclip.copy(str(texto))
        time.sleep(0.1)

        if pegar:
            if seleccionar_todo and not app.presionar_combinacion_real("ctrl", "a"):
                T.registrar_escritura(ok=False)
                raise RPAExceptions.EntradaTextoException(
                    "No se pudo seleccionar el texto actual con ctrl+a"
                )
            if not app.presionar_combinacion_real("ctrl", "v"):
                T.registrar_escritura(ok=False)
                raise RPAExceptions.EntradaTextoException(
                    "No se pudo pegar texto con ctrl+v"
                )

        T.registrar_escritura(ok=True, ms=(time.perf_counter() - t0) * 1000)
        return True

    def tipear(self, texto: str, seleccionar_todo: bool = True) -> bool:
        from shared.tools.app_tools import AppTools
        from pywinauto.keyboard import send_keys

        app = AppTools()

        if seleccionar_todo:
            app.presionar_combinacion_real("ctrl", "a")
            time.sleep(0.06)

        send_keys(str(texto), with_spaces=True, pause=0.001)
        T.registrar_tipeo()
        return True

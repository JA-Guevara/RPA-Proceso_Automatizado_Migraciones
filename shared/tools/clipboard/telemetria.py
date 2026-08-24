"""
Telemetría del portapapeles. Mismo espíritu que ImageLocator._stats: contadores
en memoria y un resumen que se loguea por lote.

Es lo que convierte "el bot falla raro" en un número: latencia p50/p95, cuántas
lecturas se reintentaron, cuántas veces el Ctrl+C no copió nada, cuántas veces
el túnel avisó inestabilidad, y si el eco de escritura existe en este servidor.
"""

from __future__ import annotations

import logging
import threading
from collections import deque

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_MAX_MUESTRAS = 300


class _Metricas:
    def __init__(self):
        self.lecturas_ok = 0
        self.lecturas_reintento = 0
        self.lecturas_timeout = 0
        self.lecturas_copia_vacia = 0
        self.lecturas_spec_descartada = 0
        self.lecturas_tap_reinstalado = 0
        self.lecturas_tunel_caido = 0

        self.escrituras_ok = 0
        self.escrituras_fallidas = 0
        self.escrituras_con_eco = 0
        self.escrituras_sin_eco = 0
        self.verificaciones_ok = 0
        self.verificaciones_mismatch = 0

        self.tipeos = 0
        self.inestable_visto = 0

        self.latencias_lectura: deque[float] = deque(maxlen=_MAX_MUESTRAS)
        self.latencias_escritura: deque[float] = deque(maxlen=_MAX_MUESTRAS)


_M = _Metricas()


def registrar_lectura(ok: bool, ms: float | None = None, motivo: str | None = None,
                      descartados: int = 0, inestable: bool = False):
    with _LOCK:
        if ok:
            _M.lecturas_ok += 1
            if ms is not None:
                _M.latencias_lectura.append(float(ms))
        else:
            if motivo == "copia_vacia":
                _M.lecturas_copia_vacia += 1
            elif motivo == "tunel_no_conectado":
                _M.lecturas_tunel_caido += 1
            else:
                _M.lecturas_timeout += 1
        if descartados:
            _M.lecturas_spec_descartada += descartados
        if inestable:
            _M.inestable_visto += 1


def registrar_reintento():
    with _LOCK:
        _M.lecturas_reintento += 1


def registrar_reinstalacion():
    with _LOCK:
        _M.lecturas_tap_reinstalado += 1


def registrar_escritura(ok: bool, ms: float | None = None, eco: bool | None = None):
    with _LOCK:
        if ok:
            _M.escrituras_ok += 1
            if ms is not None:
                _M.latencias_escritura.append(float(ms))
        else:
            _M.escrituras_fallidas += 1
        if eco is True:
            _M.escrituras_con_eco += 1
        elif eco is False:
            _M.escrituras_sin_eco += 1


def registrar_verificacion(coincide: bool):
    with _LOCK:
        if coincide:
            _M.verificaciones_ok += 1
        else:
            _M.verificaciones_mismatch += 1


def registrar_tipeo():
    with _LOCK:
        _M.tipeos += 1


def _percentil(muestras, p: float):
    if not muestras:
        return None
    datos = sorted(muestras)
    idx = min(len(datos) - 1, max(0, int(round((len(datos) - 1) * p))))
    return round(datos[idx], 1)


def resumen() -> dict:
    with _LOCK:
        total_lecturas = (
            _M.lecturas_ok + _M.lecturas_timeout
            + _M.lecturas_copia_vacia + _M.lecturas_tunel_caido
        )
        return {
            "lecturas": total_lecturas,
            "lecturas_ok": _M.lecturas_ok,
            "timeout": _M.lecturas_timeout,
            "copia_vacia": _M.lecturas_copia_vacia,
            "tunel_caido": _M.lecturas_tunel_caido,
            "reintentos": _M.lecturas_reintento,
            "reinstalaciones_tap": _M.lecturas_tap_reinstalado,
            "eventos_descartados_por_spec": _M.lecturas_spec_descartada,
            "lectura_p50_ms": _percentil(_M.latencias_lectura, 0.50),
            "lectura_p95_ms": _percentil(_M.latencias_lectura, 0.95),
            "escrituras_ok": _M.escrituras_ok,
            "escrituras_fallidas": _M.escrituras_fallidas,
            "escritura_p50_ms": _percentil(_M.latencias_escritura, 0.50),
            "escritura_p95_ms": _percentil(_M.latencias_escritura, 0.95),
            "eco_si": _M.escrituras_con_eco,
            "eco_no": _M.escrituras_sin_eco,
            "verificacion_ok": _M.verificaciones_ok,
            "verificacion_mismatch": _M.verificaciones_mismatch,
            "tipeos": _M.tipeos,
            "tunel_inestable_visto": _M.inestable_visto,
            "tasa_exito": (
                round(_M.lecturas_ok / total_lecturas, 3) if total_lecturas else None
            ),
        }


def log_resumen(prefijo: str = "📊 Portapapeles"):
    logger.info(f"{prefijo}: {resumen()}")

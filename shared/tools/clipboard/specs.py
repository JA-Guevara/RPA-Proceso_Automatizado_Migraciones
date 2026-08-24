"""
Especificaciones declarativas de validación de contenido.

Un spec es un dict serializable. Se evalúa en DOS lugares con la misma
semántica:

  1. En el navegador, DURANTE la espera del evento de portapapeles: si el
     texto que llegó no cumple, se descarta y se sigue esperando en vez de
     aceptarlo. Esto es lo que impide tomar un fragmento parcial del túnel
     como valor final.
  2. En Python, al recibirlo, como defensa en profundidad.

Al ser datos y no código, se testean sin navegador y no hay `eval`.

IMPORTANTE: cualquier tipo nuevo debe agregarse también a `cumpleSpec()` en
tap_js.py. Un spec desconocido NO bloquea (devuelve True) para que una
diferencia de versión nunca frene la producción.
"""

from __future__ import annotations

import re
from typing import Any


def cumple(texto: Any, spec: dict | None) -> bool:
    """Evalúa un spec contra un texto. Espejo exacto de cumpleSpec() en JS."""
    if not spec:
        return True

    t = "" if texto is None else str(texto)
    tipo = spec.get("tipo")

    if tipo == "no_vacio":
        return len(t.strip()) > 0

    if tipo == "igual":
        return t == spec.get("txt", "")

    if tipo == "min_len":
        return len(t) >= int(spec.get("n", 0))

    if tipo == "max_len":
        return len(t) <= int(spec.get("n", 0))

    if tipo == "contiene":
        objetivo = str(spec.get("txt", ""))
        if spec.get("ci"):
            return objetivo.upper() in t.upper()
        return objetivo in t

    if tipo == "en":
        return t.strip() in [str(v) for v in spec.get("valores", [])]

    if tipo == "primer_token_en":
        partes = t.strip().split()
        token = partes[0].upper() if partes else ""
        return token in [str(v).upper() for v in spec.get("valores", [])]

    if tipo == "min_lineas":
        lineas = [l for l in t.splitlines() if l.strip()]
        return len(lineas) >= int(spec.get("n", 1))

    if tipo == "min_columnas":
        sep = spec.get("sep", "\t")
        n = int(spec.get("n", 2))
        lineas = [l for l in t.splitlines() if l.strip()]
        if not lineas:
            return False
        return any(len(l.split(sep)) >= n for l in lineas)

    if tipo == "regex":
        banderas = 0
        if "i" in str(spec.get("flags", "")):
            banderas |= re.IGNORECASE
        return re.search(str(spec.get("re", "")), t, banderas) is not None

    if tipo == "y":
        return all(cumple(t, s) for s in spec.get("de", []))

    if tipo == "o":
        return any(cumple(t, s) for s in spec.get("de", []))

    # Spec desconocido: no bloquea.
    return True


# ---------------------------------------------------------------------------
# Catálogo de specs por lectura.
#
# Solo cubren lecturas que HOY ya usan portapapeles. Las tres lecturas por
# OCR de región (forma_pago_rpa, situacion, idctl_actual_rpa) NO entran acá:
# conservan su mecanismo intacto según la decisión D14 de TRAZABILIDAD.md.
# ---------------------------------------------------------------------------

# ValidationEstadoCuentaAction.extraer_validar_estado
ESTADO_CUENTA = {
    "tipo": "primer_token_en",
    "valores": ["AC", "PP", "PO", "PK", "EL"],
}

# ValidationConsumoAction.extraer_validar_consumo — la grilla de facturas
CONSUMO = {"tipo": "min_lineas", "n": 1}

# ValidationEstadoControladoAction.extraer_situacion_ventas — grilla CNS
CNS = {"tipo": "min_columnas", "sep": " ", "n": 4}

# SaldoCoreBalanceAction.extraer_y_validar_billetera
BILLETERA = {"tipo": "no_vacio"}

# ExtractionTools.extraer_y_validar_plan — replica las reglas actuales
# (líneas 454-459 de extraction_tools.py: len <= 100 y contiene "plan")
PLAN = {
    "tipo": "y",
    "de": [
        {"tipo": "contiene", "txt": "plan", "ci": True},
        {"tipo": "max_len", "n": 100},
    ],
}

# ExtractionTools.extraer_validar_error — mensaje de error de BCCS
ERROR_BCCS = {"tipo": "no_vacio"}

# ValidationIdctlActualAction.extraer_validar_plan_programado — grilla de planes
PLAN_PROGRAMADO = {"tipo": "min_lineas", "n": 1}

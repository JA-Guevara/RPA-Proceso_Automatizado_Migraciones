"""
Servicio de portapapeles con backends por modo de conexión.

Uso normal (el consumidor no sabe si es web o rdp):

    from shared.tools.clipboard import clipboard_service, specs

    texto = clipboard_service.leer(spec=specs.ESTADO_CUENTA)
    clipboard_service.escribir_valor("59171234567")

Módulos:
    service.py            ClipboardService + configuración + lock + router
    guacamole_backend.py  modo web: intercepta onclipboard del cliente Guacamole
    pyperclip_backend.py  modo rdp: centinela + estabilización (comportamiento original)
    tap_js.py             payload JavaScript del interceptor
    specs.py              validadores declarativos (espejo Python/JS)
    keysyms.py            keysyms X11 para sendKeyEvent
    telemetria.py         contadores y resumen por lote
"""

from shared.tools.clipboard.service import ClipboardService, clipboard_service
from shared.tools.clipboard import specs
from shared.tools.clipboard import telemetria

__all__ = [
    "ClipboardService",
    "clipboard_service",
    "specs",
    "telemetria",
]

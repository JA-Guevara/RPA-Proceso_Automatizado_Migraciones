"""
ClipboardService — punto único de acceso al portapapeles.

Los consumidores no saben si están sobre Guacamole o sobre RDP:

    texto = clipboard_service.leer(spec=specs.ESTADO_CUENTA)
    clipboard_service.escribir_valor("59171234567")

El despacho por modo es dinámico y perezoso: se resuelve en la primera
operación leyendo CONEXION_ESCRITORIO, y el backend RDP nunca importa
Playwright ni Guacamole (ni al revés).

El lock es real y abarca la operación completa. Hay un solo portapapeles y un
solo túnel: dos lecturas concurrentes esperarían el mismo evento.
"""

from __future__ import annotations

import logging
import re
import threading

from shared.tools.exceptions import RPAExceptions
from shared.tools.clipboard import telemetria as T

logger = logging.getLogger(__name__)

_ESPACIOS = re.compile(r"\s+")


# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

class ClipboardConfig:
    """Snapshot de configuración. Se lee de EnvConfig una sola vez."""

    def __init__(self):
        from config.config import EnvConfig as E

        def flag(nombre, default):
            valor = getattr(E, nombre, None)
            if valor is None:
                return default
            if isinstance(valor, bool):
                return valor
            return str(valor).strip().lower() in ("1", "true", "si", "sí", "yes")

        def num(nombre, default):
            try:
                valor = getattr(E, nombre, None)
                return type(default)(valor) if valor not in (None, "") else default
            except (TypeError, ValueError):
                return default

        def txt(nombre, default):
            valor = getattr(E, nombre, None)
            return str(valor).strip().lower() if valor else default

        self.backend = txt("CLIPBOARD_BACKEND", "auto")
        self.input_mode = txt("GUACAMOLE_INPUT_MODE", "os")

        self.timeout = num("CLIPBOARD_TIMEOUT", 8.0)
        self.timeout_rdp = num("CLIPBOARD_TIMEOUT_RDP", 5.0)
        self.reintentos = num("CLIPBOARD_REINTENTOS", 2)

        self.fail_closed = flag("CLIPBOARD_FAIL_CLOSED", True)

        # OFF por defecto: el veneno solo se puede DETECTAR si el servidor RDP
        # devuelve el portapapeles por onclipboard. Medido en produccion:
        # este servidor no lo hace (eco=False), asi que el veneno nunca podria
        # dispararse y solo agrega latencia por lectura.
        self.poison = flag("CLIPBOARD_POISON", False)
        self.veneno_settle_ms = num("CLIPBOARD_VENENO_SETTLE_MS", 120)

        # OFF por defecto por lo mismo: ya sabemos que no hay eco.
        self.medir_eco = flag("CLIPBOARD_MEDIR_ECO", False)
        self.eco_timeout_ms = num("CLIPBOARD_ECO_TIMEOUT_MS", 400)
        self.settle_escritura_ms = num("CLIPBOARD_SETTLE_ESCRITURA_MS", 400)

        self.espera_inestable = num("CLIPBOARD_ESPERA_INESTABLE", 1.5)
        self.verificar_escritura = flag("CLIPBOARD_VERIFICAR_ESCRITURA", False)

        # Guard de clics: APAGADO por defecto. Ver exigir_viva().
        self.guard_clics = flag("CLIPBOARD_GUARD_CLICS", False)

        # Gracia tras el PRIMER evento recibido. Si ya llegó algo del remoto,
        # no tiene sentido quemar el timeout completo esperando algo mejor.
        self.gracia_ms = num("CLIPBOARD_GRACIA_MS", 800)

        self.router_tipeo = flag("INPUT_ROUTER_TIPEO", False)
        self.tipeo_max_len = num("INPUT_TIPEO_MAX_LEN", 30)

    def __repr__(self):
        return (
            f"ClipboardConfig(backend={self.backend}, input_mode={self.input_mode}, "
            f"timeout={self.timeout}, reintentos={self.reintentos}, "
            f"fail_closed={self.fail_closed}, poison={self.poison}, "
            f"router_tipeo={self.router_tipeo}, verificar={self.verificar_escritura})"
        )


# ---------------------------------------------------------------------------
# Servicio
# ---------------------------------------------------------------------------

class ClipboardService:

    def __init__(self):
        self.cfg = ClipboardConfig()
        self._lock = threading.RLock()
        self._backend = None
        self._modo = None

    # ------------------------------------------------------------- despacho

    def _modo_actual(self) -> str:
        if self.cfg.backend in ("guacamole", "pyperclip"):
            return "web" if self.cfg.backend == "guacamole" else "rdp"
        try:
            from config.config import EnvConfig
            return (EnvConfig.CONEXION_ESCRITORIO or "rdp").strip().lower()
        except Exception:
            return "rdp"

    def backend(self):
        modo = self._modo_actual()

        if self._backend is not None and self._modo == modo:
            return self._backend

        if modo == "web":
            from shared.tools.clipboard.guacamole_backend import GuacamoleBackend
            self._backend = GuacamoleBackend(self.cfg)
        else:
            from shared.tools.clipboard.pyperclip_backend import PyperclipBackend
            self._backend = PyperclipBackend(self.cfg)

        self._modo = modo
        logger.info(
            "📋 ClipboardService → backend=%s (modo=%s) | %s",
            self._backend.nombre, modo, self.cfg,
        )
        return self._backend

    @property
    def es_web(self) -> bool:
        return self._modo_actual() == "web"

    # ---------------------------------------------------------------- ciclo

    def instalar(self) -> dict:
        """Idempotente. En rdp es un no-op."""
        with self._lock:
            return self.backend().instalar()

    def salud(self) -> dict:
        with self._lock:
            return self.backend().salud()

    def exigir_conexion(self) -> dict:
        """
        Llamar antes de operaciones críticas. En web lanza excepción técnica si
        el túnel no está conectado, para que TaskManagerMigracion recupere la
        sesión en lugar de seguir operando sobre un canvas congelado.
        """
        with self._lock:
            return self.backend().exigir_tunel_sano()

    def desconexiones(self) -> int:
        return self.backend().desconexiones()

    def conexion_viva(self) -> bool:
        """Chequeo local y barato. Apto para llamar antes de cada clic."""
        try:
            return bool(self.backend().conexion_viva())
        except Exception:
            # Falla ABIERTA: ante cualquier duda no bloqueamos.
            return True

    def exigir_viva(self):
        """
        Aborta si la página del escritorio está POSITIVAMENTE cerrada.

        APAGADO por defecto (`CLIPBOARD_GUARD_CLICS=false`). Motivo: la primera
        versión de este guard bloqueó el logout de recuperación con el
        escritorio vivo y detuvo el bot. Antes de encenderlo hay que confirmar
        en producción que `conexion_viva()` no da falsos negativos.

        Cuando esté encendido, el objetivo sigue siendo válido: si el navegador
        se cerró, PyAutoGUI seguiría disparando clics sobre lo que haya quedado
        en pantalla (el escritorio del usuario, otra ventana).
        """
        if not self.cfg.guard_clics:
            return

        if not self.conexion_viva():
            raise RPAExceptions.ConexionFallidaException(
                "La página del escritorio remoto está cerrada. Se aborta antes "
                "de seguir operando a ciegas."
            )

    def log_resumen(self, prefijo: str = "📊 Portapapeles"):
        T.log_resumen(prefijo)

    # -------------------------------------------------------------- lectura

    def leer(self, spec: dict | None = None, timeout: float | None = None,
             seleccionar_todo: bool = False) -> str:
        with self._lock:
            return self.backend().leer(
                spec=spec, timeout=timeout, seleccionar_todo=seleccionar_todo
            )

    # ------------------------------------------------------------ escritura

    def escribir(self, texto: str, seleccionar_todo: bool = True,
                 pegar: bool = True, verificar: bool | None = None) -> bool:
        """Escritura por portapapeles, con verificación en destino opcional."""
        verificar = self.cfg.verificar_escritura if verificar is None else verificar

        with self._lock:
            backend = self.backend()
            backend.escribir(texto, seleccionar_todo=seleccionar_todo, pegar=pegar)

            if not (verificar and pegar):
                return True

            if self._verificar_destino(backend, texto):
                return True

            # Reintento por portapapeles.
            logger.warning("🔁 Verificación falló → reescribiendo por portapapeles")
            backend.escribir(texto, seleccionar_todo=True, pegar=True)
            if self._verificar_destino(backend, texto):
                return True

            # Último recurso: tipear (determinista, sin portapapeles).
            logger.warning("⌨️ Verificación falló dos veces → cayendo a tipeo")
            backend.tipear(texto, seleccionar_todo=True)
            if self._verificar_destino(backend, texto):
                return True

            raise RPAExceptions.EntradaTextoException(
                f"El campo no quedó con el valor esperado tras 3 intentos "
                f"(esperado={self._normalizar(texto)!r})"
            )

    def tipear(self, texto: str, seleccionar_todo: bool = True) -> bool:
        with self._lock:
            return self.backend().tipear(texto, seleccionar_todo=seleccionar_todo)

    def escribir_valor(self, texto: str, seleccionar_todo: bool = True,
                       forzar_portapapeles: bool = False) -> bool:
        """
        Router. Valores cortos y ASCII se tipean (deterministas, sin viaje de
        vuelta); el resto va por portapapeles.

        Es el arreglo más barato para la clase de error más peligrosa: que
        `nro_linea` o el código de plan de consumo se peguen con el valor del
        registro anterior.
        """
        valor = "" if texto is None else str(texto)

        if (
            not forzar_portapapeles
            and self.cfg.router_tipeo
            and self._tipeable(valor)
        ):
            logger.info("⌨️ Router: '%s' se tipea (len=%s)", valor[:20], len(valor))
            return self.tipear(valor, seleccionar_todo=seleccionar_todo)

        return self.escribir(valor, seleccionar_todo=seleccionar_todo, pegar=True)

    def _tipeable(self, valor: str) -> bool:
        if not valor:
            return False
        if len(valor) > self.cfg.tipeo_max_len:
            return False
        return all(0x20 <= ord(c) <= 0x7E for c in valor)

    def _verificar_destino(self, backend, esperado: str) -> bool:
        """Lee el campo de vuelta y compara. Es la única prueba real."""
        try:
            leido = backend.leer(spec=None, timeout=self.cfg.timeout,
                                 seleccionar_todo=True)
        except Exception as e:
            logger.warning("⚠️ No se pudo verificar el destino: %s", e)
            T.registrar_verificacion(False)
            return False

        coincide = self._normalizar(leido) == self._normalizar(esperado)
        T.registrar_verificacion(coincide)

        if not coincide:
            logger.warning(
                "⚠️ Verificación en destino NO coincide | esperado=%r | leído=%r",
                self._normalizar(esperado)[:60], self._normalizar(leido)[:60],
            )
        return coincide

    @staticmethod
    def _normalizar(valor) -> str:
        return _ESPACIOS.sub(" ", str(valor or "").strip()).upper()


# Instancia compartida del proceso.
clipboard_service = ClipboardService()

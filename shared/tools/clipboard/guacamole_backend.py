"""
Backend de portapapeles para modo WEB (Guacamole).

Lee el portapapeles remoto interceptando el evento `onclipboard` del cliente
Guacamole, es decir TRES saltos antes de donde lo leía el código anterior:

    antes:  remoto -> guacd -> túnel -> onclipboard -> navigator.clipboard
            -> portapapeles del HOST -> pyperclip.paste()   (polling a ciegas)

    ahora:  remoto -> guacd -> túnel -> onclipboard -> Python
                                        (evento, con número de secuencia)

Con eso desaparecen la dependencia del permiso/foco de la Clipboard API del
navegador y la imposibilidad de saber si lo leído era nuevo, viejo o parcial.

REGLA DURA: en modo web NO hay fallback a pyperclip. Una vez que el tap
consume el stream, `navigator.clipboard` deja de actualizarse, así que
pyperclip devolvería el valor del registro ANTERIOR — exactamente el bug que
se está corrigiendo. Si el camino del tap falla, es falla técnica y se
propaga para que TaskManagerMigracion recupere la sesión.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from shared.tools.exceptions import RPAExceptions
from shared.tools.clipboard import keysyms as K
from shared.tools.clipboard import specs as S
from shared.tools.clipboard import telemetria as T
from shared.tools.clipboard import tap_js as JS

logger = logging.getLogger(__name__)


async def _con_limite(coro, segundos: float):
    return await asyncio.wait_for(coro, timeout=segundos)


class GuacamoleBackend:
    """Backend web. Nunca se instancia en modo rdp."""

    nombre = "guacamole"

    def __init__(self, cfg):
        self.cfg = cfg
        self._ultima_salud: dict = {}

    # ------------------------------------------------------------------ infra

    def _conexion(self):
        try:
            from infrastructure.remote_desktop.conexion_escritorio import ConexionEscritorio
        except Exception as e:
            # Import perezoso: en modo rdp este backend no se instancia nunca,
            # así que un fallo acá es de entorno y debe salir tipado para que
            # TaskManagerMigracion lo trate como falla técnica.
            raise RPAExceptions.ConexionFallidaException(
                f"No se pudo cargar la conexión de escritorio: {e}"
            )
        return ConexionEscritorio.instancia()

    def _page(self):
        conexion = self._conexion()
        page = conexion.page
        if page is None:
            raise RPAExceptions.ConexionFallidaException(
                "No hay sesión web activa para el portapapeles."
            )
        return conexion, page

    def _ejecutar(self, js: str, arg=None, limite: float = 20.0):
        """
        Un viaje al navegador, con techo de tiempo propio.

        El techo es imprescindible: si el WebSocket muere en medio de un
        evaluate, Playwright puede quedar esperando hasta detectar la caída, y
        sin este límite el bot se cuelga en vez de fallar.
        """
        conexion, page = self._page()
        try:
            if arg is None:
                return conexion.run(_con_limite(page.evaluate(js), limite))
            return conexion.run(_con_limite(page.evaluate(js, arg), limite))
        except asyncio.TimeoutError:
            raise RPAExceptions.TiempoEsperaExcedidoException(
                f"El navegador no respondió en {limite:.1f}s (portapapeles)."
            )
        except Exception as e:
            texto = str(e)
            # Contexto destruido = la página navegó o recargó: hay que reinstalar.
            if "Execution context was destroyed" in texto or "context was destroyed" in texto:
                raise RPAExceptions.ConexionFallidaException(
                    "El contexto de la página se destruyó (navegación/recarga)."
                )
            raise RPAExceptions.ComunicacionException(
                f"Fallo evaluando en el navegador: {texto}"
            )

    # ----------------------------------------------------------------- ciclo

    def instalar(self) -> dict:
        salud = self._ejecutar(JS.TAP_INSTALAR, limite=15.0) or {}
        self._ultima_salud = salud

        if not salud.get("ok"):
            raise RPAExceptions.ConexionFallidaException(
                f"No se pudo instalar el interceptor de portapapeles: "
                f"{salud.get('motivo', 'desconocido')}"
            )

        if salud.get("yaEstaba"):
            logger.info("📋 Tap de portapapeles ya instalado y sano (seq=%s)", salud.get("seq"))
        else:
            logger.info(
                "📋 Tap de portapapeles instalado | cliente=%s | túnel_enganchado=%s | estado=%s",
                salud.get("clientPath"), salud.get("tunnelHook"), salud.get("estadoCliente"),
            )
        return salud

    def salud(self) -> dict:
        salud = self._ejecutar(JS.OP_SALUD, limite=10.0) or {}
        self._ultima_salud = salud
        return salud

    def _asegurar_tap(self) -> dict:
        salud = self.salud()
        if salud.get("ok") and salud.get("sano"):
            return salud
        logger.warning(
            "♻️ Tap inválido (%s) → reinstalando", salud.get("motivo") or "no sano"
        )
        T.registrar_reinstalacion()
        return self.instalar()

    def exigir_tunel_sano(self) -> dict:
        """
        Cortafuegos contra el peor modo de falla: el túnel caído con el canvas
        congelado. Sin esto el bot sigue clickeando sobre una foto y "valida"
        pantallas que ya no existen.
        """
        salud = self._asegurar_tap()
        if not salud.get("conectado"):
            raise RPAExceptions.ConexionFallidaException(
                f"Túnel Guacamole no conectado (estado={salud.get('estadoCliente')})."
            )
        return salud

    def desconexiones(self) -> int:
        return int((self._ultima_salud or {}).get("desconexiones") or 0)

    # ---------------------------------------------------------------- lectura

    def _veneno(self) -> str | None:
        if not self.cfg.poison:
            return None
        return f"__RPA_VOID_{uuid.uuid4().hex[:8]}__"

    def leer(self, spec: dict | None = None, timeout: float | None = None,
             seleccionar_todo: bool = False) -> str:
        timeout = float(timeout or self.cfg.timeout)
        intentos = max(1, int(self.cfg.reintentos))
        ultimo: dict = {}

        for intento in range(1, intentos + 1):
            if intento > 1:
                T.registrar_reintento()
                logger.warning(
                    "🔁 Reintento de lectura %s/%s (motivo previo=%s)",
                    intento, intentos, ultimo.get("motivo"),
                )

            salud = self.exigir_tunel_sano()

            # Si el túnel ya avisó que está inestable, damos aire antes de
            # gastar el intento. La señal la calcula el propio túnel.
            if salud.get("inestable"):
                logger.warning("🌐 Túnel marcado inestable → esperando antes de leer")
                self._dormir(self.cfg.espera_inestable)

            r = self._leer_una_vez(spec, timeout, seleccionar_todo) or {}
            ultimo = r

            T.registrar_lectura(
                ok=bool(r.get("ok")),
                ms=r.get("ms"),
                motivo=r.get("motivo"),
                descartados=int(r.get("descartados") or 0),
                inestable=bool(r.get("inestable")),
            )

            # Caso bueno: llegó un evento y cumple la forma esperada.
            if r.get("ok") and r.get("cumplioSpec"):
                texto = r.get("texto") or ""
                if spec and not S.cumple(texto, spec):
                    logger.warning(
                        "⚠️ Texto pasó el spec en el navegador pero no en Python: %r",
                        texto[:80],
                    )
                    continue

                logger.info(
                    "📋 Lectura remota ok | %sms | seq=%s | descartados=%s | len=%s",
                    round(r.get("ms") or 0), r.get("seq"),
                    r.get("descartados"), len(texto),
                )
                return texto

            # Llegó un evento pero sin la forma esperada. NO es falla de
            # transporte: el Ctrl+C funcionó y el remoto mandó algo. Puede ser
            # una grilla vacía ('\r\n'), que es un resultado de negocio válido.
            # Se reintenta por si fue una lectura parcial, y si en el último
            # intento sigue igual, se devuelve tal cual para que la acción
            # decida qué significa.
            if r.get("ok"):
                texto = r.get("texto") or ""
                if intento < intentos:
                    logger.warning(
                        "⚠️ Llegó un evento que no cumple el spec (len=%s, %r) → "
                        "reintento %s/%s",
                        len(texto), texto[:40], intento + 1, intentos,
                    )
                    continue

                logger.warning(
                    "📋 Lectura remota SIN forma esperada tras %s intentos | "
                    "%sms | seq=%s | len=%s | %r → se devuelve para que la "
                    "acción decida (puede ser vacío legítimo)",
                    intentos, round(r.get("ms") or 0), r.get("seq"),
                    len(texto), texto[:60],
                )
                return texto

            # ok == False: no llegó NADA. Esto sí es falla de transporte.
            if r.get("motivo") == "tap_invalido":
                self.instalar()

            logger.warning(
                "❌ Lectura remota falló | motivo=%s | %sms | eventos=%s | "
                "veneno_visto=%s | vistos=%s",
                r.get("motivo"), round(r.get("ms") or 0),
                r.get("eventosVistos"), r.get("venenoVisto"), r.get("vistos"),
            )

        return self._fallar_lectura(ultimo)

    def _leer_una_vez(self, spec, timeout, seleccionar_todo) -> dict:
        veneno = self._veneno()
        limite_navegador = timeout + 8.0

        if self.cfg.input_mode == "tunnel":
            # UN solo viaje: envenenar + disparar + esperar + validar, adentro.
            return self._ejecutar(
                JS.OP_LEER,
                {
                    "timeoutMs": int(timeout * 1000),
                    "graciaMs": int(self.cfg.gracia_ms),
                    "spec": spec,
                    "veneno": veneno,
                    "venenoSettleMs": int(self.cfg.veneno_settle_ms),
                    "seleccionarTodo": bool(seleccionar_todo),
                    "keysCopiar": K.COPIAR,
                    "keysSeleccionar": K.SELECCIONAR_TODO,
                },
                limite=limite_navegador,
            )

        # Modo compatible: las teclas salen del SO (pywinauto), como hoy.
        armado = self._ejecutar(JS.OP_ARMAR, {"veneno": veneno}, limite=10.0) or {}
        if not armado.get("ok"):
            return armado

        if armado.get("venenoPuesto"):
            self._dormir(self.cfg.veneno_settle_ms / 1000.0)

        from shared.tools.app_tools import AppTools
        app = AppTools()
        if seleccionar_todo:
            app.presionar_combinacion_real("ctrl", "a")
            self._dormir(0.06)
        app.presionar_combinacion_real("ctrl", "c")

        return self._ejecutar(
            JS.OP_ESPERAR,
            {
                "seq0": armado.get("seq0", 0),
                "timeoutMs": int(timeout * 1000),
                "graciaMs": int(self.cfg.gracia_ms),
                "spec": spec,
                "veneno": veneno,
                "venenoPuesto": bool(armado.get("venenoPuesto")),
            },
            limite=limite_navegador,
        )

    def _fallar_lectura(self, ultimo: dict):
        motivo = (ultimo or {}).get("motivo") or "desconocido"

        if not self.cfg.fail_closed:
            logger.error(
                "🚨 Lectura de portapapeles agotada (%s) y FAIL_CLOSED=false → "
                "se devuelve vacío. Configuración NO recomendada.", motivo,
            )
            return ""

        if motivo == "copia_vacia":
            raise RPAExceptions.DatosException(
                "El Ctrl+C no copió nada: volvió el token de control. "
                "Probablemente el campo no estaba enfocado."
            )
        if motivo == "tunel_no_conectado":
            raise RPAExceptions.ConexionFallidaException(
                "Túnel Guacamole caído durante la lectura del portapapeles."
            )
        raise RPAExceptions.TiempoEsperaExcedidoException(
            "No llegó NINGÚN evento de portapapeles desde el remoto "
            f"(motivo={motivo}). El Ctrl+C no produjo ninguna actualización: "
            "revisar foco de la ventana del navegador o estado del túnel."
        )

    # ------------------------------------------------------------- liveness

    def conexion_viva(self) -> bool:
        """
        ¿Sigue viva la página del escritorio remoto?

        FALLA ABIERTA A PROPÓSITO: solo devuelve False cuando puede determinar
        POSITIVAMENTE que la página está cerrada. Si el chequeo es inconcluyente,
        devuelve True y deja pasar.

        Historia: la primera versión usaba `ConexionEscritorio.esta_activa()`,
        cuya semántica real no estaba verificada. Devolvió False con el
        escritorio vivo y bloqueó el logout de recuperación, convirtiendo un
        miss de imagen recuperable en una parada total del bot. Un guard de
        seguridad que falla cerrado en el camino de recuperación es peor que no
        tener guard.

        `Page.is_closed()` sí es un booleano sincrónico y confiable.
        """
        try:
            conexion = self._conexion()
        except Exception:
            return True

        try:
            page = getattr(conexion, "page", None)
            if page is None:
                return False

            is_closed = getattr(page, "is_closed", None)
            if callable(is_closed):
                return not bool(is_closed())

            # No se pudo determinar: NO bloqueamos.
            return True
        except Exception:
            return True

    # -------------------------------------------------------------- escritura

    def escribir(self, texto: str, seleccionar_todo: bool = True,
                 pegar: bool = True) -> bool:
        self.exigir_tunel_sano()

        r = self._ejecutar(
            JS.OP_ESCRIBIR,
            {
                "texto": str(texto),
                "esperarEco": bool(self.cfg.medir_eco),
                "ecoTimeoutMs": int(self.cfg.eco_timeout_ms),
                "settleMs": int(self.cfg.settle_escritura_ms),
                "pegar": bool(pegar),
                "seleccionarTodo": bool(seleccionar_todo),
                "keysPegar": K.PEGAR,
                "keysSeleccionar": K.SELECCIONAR_TODO,
            },
            limite=20.0,
        ) or {}

        T.registrar_escritura(
            ok=bool(r.get("ok")), ms=r.get("ms"),
            eco=r.get("eco") if self.cfg.medir_eco else None,
        )

        if not r.get("ok"):
            raise RPAExceptions.EntradaTextoException(
                f"No se pudo escribir por portapapeles: {r.get('motivo')}"
            )

        logger.info(
            "📋 Escritura remota ok | %sms | eco=%s", round(r.get("ms") or 0), r.get("eco")
        )
        return True

    def tipear(self, texto: str, seleccionar_todo: bool = True) -> bool:
        """Tipeo por el túnel. No usa portapapeles: no hay viaje de vuelta."""
        self.exigir_tunel_sano()

        r = self._ejecutar(
            JS.OP_TIPEAR,
            {
                "keysyms": K.keysyms_de_texto(texto),
                "seleccionarTodo": bool(seleccionar_todo),
                "keysSeleccionar": K.SELECCIONAR_TODO,
            },
            limite=20.0,
        ) or {}

        if not r.get("ok"):
            raise RPAExceptions.EntradaTextoException(
                f"No se pudo tipear por el túnel: {r.get('motivo')}"
            )

        T.registrar_tipeo()
        return True

    def liberar_modificadores(self) -> None:
        try:
            self._ejecutar(JS.OP_LIBERAR_MODS, limite=8.0)
        except Exception:
            logger.debug("No se pudo liberar modificadores", exc_info=True)

    # --------------------------------------------------------------- utilidad

    @staticmethod
    def _dormir(segundos: float):
        import time
        if segundos and segundos > 0:
            time.sleep(segundos)

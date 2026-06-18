import hashlib
import logging
import time
import uuid

import pyperclip

logger = logging.getLogger(__name__)


def obtener_modo_conexion() -> str:

    try:
        from infrastructure.remote_desktop.conexion_escritorio import ConexionEscritorio

        conexion = ConexionEscritorio.instancia()
        modo = getattr(conexion, "modo", None)

        if modo:
            return str(modo).lower()

    except Exception:
        pass

    return "local"


def intentar_copiar_guacamole_sync(texto: str) -> bool:

    try:
        from infrastructure.remote_desktop.conexion_escritorio import ConexionEscritorio
        from shared.tools.guacamole_clipboard_bridge import copiar_en_guacamole_por_debajo

        conexion = ConexionEscritorio.instancia()

        modo = getattr(conexion, "modo", None)
        page = getattr(conexion, "page", None)

        logger.info(
            "🧪 Guacamole sync bridge | modo=%s | page_existe=%s | texto='%s...'",
            modo,
            page is not None,
            texto[:30],
        )

        if modo != "web":
            logger.info("⏭️ Guacamole sync bridge omitido: modo no es web")
            return False

        if page is None:
            logger.info("⏭️ Guacamole sync bridge omitido: no hay page activa")
            return False

        ok = conexion.run(
            copiar_en_guacamole_por_debajo(
                page=page,
                texto=texto,
                logger=logger,
            )
        )

        logger.info("🧪 Guacamole sync bridge resultado=%s", ok)
        return bool(ok)

    except Exception as e:
        logger.warning("⚠️ Guacamole sync bridge omitido/falló: %s", e)
        return False


def copiar_desde_app_activa_sync(
    usar_real: bool = True,
    modo: str | None = None,
    timeout: float | None = None,
    intervalo: float = 0.25,
    reintentos: int | None = None,
    limpiar: bool = False,
    mayusculas: bool = False,
) -> str:

    try:
        from shared.tools.app_tools import AppTools

        app_tools = AppTools()

        modo_detectado = (modo or obtener_modo_conexion()).lower()

        if timeout is None:
            timeout = 12.0 if modo_detectado == "web" else 5.0

        if reintentos is None:
            reintentos = 3 if modo_detectado == "web" else 2

        logger.info(
            "📋 Copiar desde app activa | modo=%s | timeout=%s | reintentos=%s | usar_real=%s",
            modo_detectado,
            timeout,
            reintentos,
            usar_real,
        )

        for intento in range(1, reintentos + 1):
            marca = f"__RPA_CLIPBOARD_SENTINEL_{uuid.uuid4()}__"

            pyperclip.copy(marca)
            time.sleep(0.15)

            if usar_real:
                ok = app_tools.presionar_combinacion_real("ctrl", "c")
            else:
                ok = app_tools.presionar_combinacion("ctrl", "c")

            if not ok:
                logger.warning("⚠️ Ctrl+C falló intento=%s/%s", intento, reintentos)
                continue

            texto = _esperar_clipboard_cambie_y_estabilice(
                marca=marca,
                timeout=timeout,
                intervalo=intervalo,
            )

            if not texto:
                logger.warning(
                    "⚠️ Clipboard vacío/no sincronizado intento=%s/%s modo=%s",
                    intento,
                    reintentos,
                    modo_detectado,
                )
                continue

            if limpiar:
                texto = texto.strip()

            if mayusculas:
                texto = texto.upper()

            logger.info(
                "📋 Texto copiado estable | modo=%s | intento=%s | len=%s | preview=%r",
                modo_detectado,
                intento,
                len(texto),
                texto[:80],
            )

            return texto

        logger.error(
            "❌ No se pudo copiar texto desde app activa | modo=%s",
            modo_detectado,
        )
        return ""

    except Exception as e:
        logger.error("❌ Error copiando desde app activa: %s", e, exc_info=True)
        return ""


def _esperar_clipboard_cambie_y_estabilice(
    marca: str,
    timeout: float = 10.0,
    intervalo: float = 0.25,
    muestras_estables: int = 2,
) -> str:
    inicio = time.time()

    ultimo_hash = None
    ultimo_len = -1
    estable_count = 0
    mejor_texto = ""

    while time.time() - inicio < timeout:
        time.sleep(intervalo)

        texto = pyperclip.paste() or ""

        if texto == marca:
            continue

        if texto == "":
            continue

        texto_len = len(texto)
        texto_hash = hashlib.sha256(
            texto.encode("utf-8", errors="ignore")
        ).hexdigest()

        if texto_hash == ultimo_hash and texto_len == ultimo_len:
            estable_count += 1
        else:
            estable_count = 0
            ultimo_hash = texto_hash
            ultimo_len = texto_len
            mejor_texto = texto

        if estable_count >= muestras_estables:
            return mejor_texto

    return mejor_texto
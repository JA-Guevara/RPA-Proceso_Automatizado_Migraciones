import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
IMAGES_DIR = os.path.join(BASE_DIR, "assets", "images")


class EnvConfig:
    BOT_NAME = os.getenv("BOT_NAME")
    BOT_VISTA = os.getenv("BOT_VISTA")
    BOT_TABLA_MIGRACION = os.getenv("BOT_TABLA_MIGRACION")
    BOT_TABLA_MIGRACION_DETALLE = os.getenv("BOT_TABLA_MIGRACION_DETALLE")
    BOT_TABLA_PLANES = os.getenv("BOT_TABLA_PLANES")
    PRIORIDAD_BAJAS = os.getenv("PRIORIDAD_BAJAS")
    BOT_TABLA_ESTADOS = os.getenv("BOT_TABLA_ESTADOS")

    DATABASE_URL = os.getenv("DATABASE_URL")

    TERMINAL_RUTA = os.getenv("TERMINAL_RUTA")
    TERMINAL_USER = os.getenv("TERMINAL_USER")
    TERMINAL_PASSWORD = os.getenv("TERMINAL_PASSWORD")
    TERMINAL_LOG = os.getenv("TERMINAL_LOG")

    BCCS_USER = os.getenv("BCCS_USER")
    BCCS_PASSWORD = os.getenv("BCCS_PASSWORD")

    SMS_USER = os.getenv("SMS_USER")
    SMS_PASSWORD = os.getenv("SMS_PASSWORD")
    SMS_URL = os.getenv("SMS_URL")

    TESSERACT_PATH = os.getenv("TESSERACT_PATH")
    DESKTOP_URL = os.getenv("DESKTOP_URL")
    DESKTOP_PROCCESS = os.getenv("DESKTOP_PROCCESS")

    CONEXION_ESCRITORIO = (os.getenv("CONEXION_ESCRITORIO", "rdp") or "rdp").strip().lower()

    GUACAMOLE_URL = os.getenv("GUACAMOLE_URL")
    GUACAMOLE_USER = os.getenv("GUACAMOLE_USER")
    GUACAMOLE_PASSWORD = os.getenv("GUACAMOLE_PASSWORD")

    DESKTOP_ANCHOR_IMAGE = os.getenv("DESKTOP_ANCHOR_IMAGE")

    LOCATOR_TIMEOUT = float(os.getenv("LOCATOR_TIMEOUT", "10"))
    LOCATOR_TIMEOUT_TRANSITORIO = float(os.getenv("LOCATOR_TIMEOUT_TRANSITORIO", "4"))
    LOCATOR_POLL_INTERVAL = float(os.getenv("LOCATOR_POLL_INTERVAL", "0.25"))
    LOCATOR_CONFIDENCE = float(os.getenv("LOCATOR_CONFIDENCE", "0.9"))
    LOCATOR_GRAYSCALE = os.getenv("LOCATOR_GRAYSCALE", "false").lower() in ("1", "true", "si", "sí")
    _fallback = os.getenv("LOCATOR_CONFIDENCE_FALLBACK", "").strip()
    LOCATOR_CONFIDENCE_FALLBACK = float(_fallback) if _fallback else None
    LOCATOR_EVIDENCIA = os.getenv("LOCATOR_EVIDENCIA", "true").lower() in ("1", "true", "si", "sí")
    LOCATOR_EVIDENCIA_MAX = int(os.getenv("LOCATOR_EVIDENCIA_MAX", "40"))

    MAIL_HOST = os.getenv("MAIL_HOST")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USER = os.getenv("MAIL_USER")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")

    MAIL_COMPARACION = os.getenv("MAIL_COMPARACION")
    MAIL_VALIDACION = os.getenv("MAIL_VALIDACION")
    MAIL_LOGISTICA = os.getenv("MAIL_LOGISTICA")
    MAIL_DEFAULT = os.getenv("MAIL_DEFAULT")
    MAIL_LOGIN = os.getenv("MAIL_LOGIN")
    MAIL_SOPORTE = os.getenv("MAIL_SOPORTE")

    # ---------------- Portapapeles ----------------
    # auto (segun CONEXION_ESCRITORIO) | guacamole | pyperclip
    CLIPBOARD_BACKEND = os.getenv("CLIPBOARD_BACKEND", "auto")

    # os     = las teclas salen del SO con pywinauto (comportamiento actual)
    # tunnel = las teclas salen por el tunel con sendKeyEvent (no depende del foco)
    GUACAMOLE_INPUT_MODE = os.getenv("GUACAMOLE_INPUT_MODE", "os")

    CLIPBOARD_TIMEOUT = float(os.getenv("CLIPBOARD_TIMEOUT", "8"))
    CLIPBOARD_TIMEOUT_RDP = float(os.getenv("CLIPBOARD_TIMEOUT_RDP", "5"))
    CLIPBOARD_REINTENTOS = int(os.getenv("CLIPBOARD_REINTENTOS", "2"))

    CLIPBOARD_FAIL_CLOSED = os.getenv("CLIPBOARD_FAIL_CLOSED", "true")
    CLIPBOARD_POISON = os.getenv("CLIPBOARD_POISON", "true")
    CLIPBOARD_VENENO_SETTLE_MS = int(os.getenv("CLIPBOARD_VENENO_SETTLE_MS", "120"))

    CLIPBOARD_MEDIR_ECO = os.getenv("CLIPBOARD_MEDIR_ECO", "true")
    CLIPBOARD_ECO_TIMEOUT_MS = int(os.getenv("CLIPBOARD_ECO_TIMEOUT_MS", "400"))
    CLIPBOARD_SETTLE_ESCRITURA_MS = int(os.getenv("CLIPBOARD_SETTLE_ESCRITURA_MS", "400"))

    CLIPBOARD_ESPERA_INESTABLE = float(os.getenv("CLIPBOARD_ESPERA_INESTABLE", "1.5"))
    CLIPBOARD_VERIFICAR_ESCRITURA = os.getenv("CLIPBOARD_VERIFICAR_ESCRITURA", "false")

    # Router: valores cortos y ASCII se tipean en vez de pegarse
    INPUT_ROUTER_TIPEO = os.getenv("INPUT_ROUTER_TIPEO", "false")
    INPUT_TIPEO_MAX_LEN = int(os.getenv("INPUT_TIPEO_MAX_LEN", "30"))

    # ---------------- OCR de region ----------------
    OCR_TRI_ESTADO = os.getenv("OCR_TRI_ESTADO", "true")

    # Umbral de similitud para el snap de OCR contra palabras_validas.
    # Bajado de 0.8 a 0.70 con evidencia de produccion: el OCR leyo 'CONTROLS'
    # (la region recorta el final de 'CONTROLADO') y la similitud fue 0.778,
    # asi que con 0.8 quedaba marcado como ilegible.
    # Margen medido: 'CONTROLS' vs 'PROPIO' da 0.286, y 'PROPIO' exacto da
    # 1.000 vs 0.375 contra 'CONTROLADO'. Con 0.70 las dos palabras validas
    # siguen separadas con holgura.
    # Un paso del flow puede sobreescribirlo con "umbral_similitud".
    OCR_UMBRAL_SIMILITUD = float(os.getenv("OCR_UMBRAL_SIMILITUD", "0.70"))

    # ---------------- Limites de almacenamiento ----------------
    # El modelo declara mensaje_observacion_rpa como String(1000) pero la
    # columna real de la BD acepta menos. Este tope se aplica al guardar y
    # evita el "String or binary data would be truncated" de SQL Server.
    # Poner 0 para usar el largo declarado en el modelo.
    BOT_MAX_OBSERVACION = int(os.getenv("BOT_MAX_OBSERVACION", "200"))

    # Tope del nombre de plan cuando se incrusta en un mensaje de observacion.
    BOT_MAX_PLAN_EN_MENSAJE = int(os.getenv("BOT_MAX_PLAN_EN_MENSAJE", "80"))
    OCR_UMBRAL_TINTA = float(os.getenv("OCR_UMBRAL_TINTA", "0.005"))
    OCR_EVIDENCIA = os.getenv("OCR_EVIDENCIA", "false")
    OCR_EVIDENCIA_MAX = int(os.getenv("OCR_EVIDENCIA_MAX", "60"))


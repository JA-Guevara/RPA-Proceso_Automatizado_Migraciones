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


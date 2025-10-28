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

    DB_SERVER = os.getenv("DB_SERVER")
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")

    TERMINAL_RUTA = os.getenv("TERMINAL_RUTA")
    TERMINAL_USER = os.getenv("TERMINAL_USER")
    TERMINAL_PASSWORD = os.getenv("TERMINAL_PASSWORD")
    TERMINAL_LOG = os.getenv("TERMINAL_LOG")

    BCCS_USER = os.getenv("BCCS_USER")
    BCCS_PASSWORD = os.getenv("BCCS_PASSWORD")

    SMS_USER = os.getenv("SMS_USER")
    SMS_PASSWORD = os.getenv("SMS_PASSWORD")
    SMS_URL = os.getenv("SMS_URL")

    DESKTOP_URL = os.getenv("DESKTOP_URL")
    DESKTOP_PROCCESS = os.getenv("DESKTOP_PROCCESS")
    
    MAIL_HOST = os.getenv("MAIL_HOST")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USER = os.getenv("MAIL_USER")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")

    MAIL_COMPARACION = os.getenv("MAIL_COMPARACION")
    MAIL_VALIDACION = os.getenv("MAIL_VALIDACION")
    MAIL_LOGISTICA = os.getenv("MAIL_LOGISTICA")
    MAIL_VALIDACION = os.getenv("MAIL_VALIDACION")
    MAIL_DEFAULT = os.getenv("MAIL_DEFAULT")
    MAIL_LOGIN = os.getenv("MAIL_LOGIN")
    MAIL_SOPORTE = os.getenv("MAIL_SOPORTE")
    

    
    
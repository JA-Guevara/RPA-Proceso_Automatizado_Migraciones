import smtplib
from email.message import EmailMessage
import logging
from typing import List, Union
import re
from config.config import EnvConfig

logger = logging.getLogger(__name__)

class MailService:
    """📧 Servicio simplificado y robusto de envío de correos para el RPA."""

    def __init__(self, variables_base: dict = None):
        self.host = EnvConfig.MAIL_HOST
        self.port = int(EnvConfig.MAIL_PORT)
        self.user = EnvConfig.MAIL_USER
        self.password = EnvConfig.MAIL_PASSWORD
        self.sender = self.user
        self.use_tls = True
        self.variables_base = variables_base or {}

        # 🔹 Estructura preparada por si en el futuro se requiere enviar por tipo
        self.mail_map = {
            "ERROR_LOGIN": EnvConfig.MAIL_DEFAULT,
            "ERROR_GENERAL": EnvConfig.MAIL_DEFAULT,
            "ERROR_SOPORTE": EnvConfig.MAIL_DEFAULT,
            "ERROR_VALIDACION": EnvConfig.MAIL_DEFAULT,
            "ERROR_INTERFAZ": EnvConfig.MAIL_DEFAULT,
        }
        default_to = EnvConfig.MAIL_DEFAULT
        self.default_to = self._parse_recipients(default_to)

    def enviar(
        self,
        asunto: str,
        mensaje: str,
        destinatarios: Union[str, List[str], None] = None,
        tipo_error: str = None,
        contexto: dict = None
    ):
        # 🔹 Siempre usa default, pero mantiene compatibilidad futura
        if destinatarios:
            to_list = self._parse_recipients(destinatarios)
        else:
            to_list = self.default_to

        if not to_list:
            logger.warning("⚠️ No se encontró ningún destinatario válido → correo omitido.")
            return

        self._send_smtp(asunto, mensaje, to_list)


    def _parse_recipients(self, value: Union[str, List[str], None]) -> List[str]:
        if not value:
            return []

        if isinstance(value, str):
            parts = [x.strip() for x in value.split(",") if x.strip()]
        elif isinstance(value, (set, tuple)):
            parts = list(value)
        else:
            parts = value

        patron = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
        validos = [p for p in parts if patron.match(p)]
        invalidos = [p for p in parts if not patron.match(p)]

        for invalido in invalidos:
            logger.warning(f"⚠️ Correo inválido ignorado: {invalido}")

        return validos


    def _send_smtp(self, asunto: str, mensaje: str, destinatarios: List[str]):
        if not all([self.host, self.user, self.password]):
            logger.error("❌ Variables SMTP incompletas. Verifica MAIL_HOST, MAIL_USER y MAIL_PASSWORD.")
            return

        email = EmailMessage()
        email["From"] = self.sender
        email["To"] = ", ".join(destinatarios)
        email["Subject"] = asunto
        email.set_content(mensaje)

        try:
            with smtplib.SMTP(self.host, self.port) as smtp:
                if self.use_tls:
                    smtp.starttls()
                smtp.login(self.user, self.password)
                smtp.send_message(email)
                logger.info(f"📧 Correo enviado exitosamente → {', '.join(destinatarios)}")
        except Exception as e:
            logger.error(f"❌ Error enviando correo: {e}", exc_info=True)

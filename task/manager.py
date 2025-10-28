import logging
import json
import time
from time import perf_counter, sleep

from application.use_cases.preparar_contexto import PreparadorDeContextos
from infrastructure.database.adapters.vista_sql_adapter import VistaSQLAdapter
from infrastructure.services.mail_service import MailService
from core.actions.migracion_action import MigracionActions
from shared.tools.exceptions import RPAExceptions
from shared.tools.app_tools import AppTools
from shared.tools.flow_loader import FlowLoader
from config.images import ImagePaths
from config.config import EnvConfig

logger = logging.getLogger(__name__)


class TaskManagerMigracion:

    def __init__(self):
        self.flow_loader = FlowLoader()
        self.app_tools = AppTools()
        self.imagenes = ImagePaths.get_all()
        self.variables_base = self._cargar_variables_base()
        self.adapter = VistaSQLAdapter()
        self.preparador = PreparadorDeContextos()
        self.mail_service = MailService()

        # Configuración general
        self.lote_max = 30
        self.reintentos_max = 3
        self.delay_entre_migraciones = 1
        self.delay_sin_pendientes = 30
        self.espera_post_logout = 60
        self.espera_reinicio = 300

    def _cargar_variables_base(self):
        vb = {
            "terminal_ruta": EnvConfig.TERMINAL_RUTA,
            "terminal_user": EnvConfig.TERMINAL_USER,
            "terminal_password": EnvConfig.TERMINAL_PASSWORD,
            "terminal_log": EnvConfig.TERMINAL_LOG,
            "bccs_user": EnvConfig.BCCS_USER,
            "bccs_password": EnvConfig.BCCS_PASSWORD,
            "sms_user": EnvConfig.SMS_USER,
            "sms_password": EnvConfig.SMS_PASSWORD,
            "sms_url": EnvConfig.SMS_URL,
            "desktop_url": EnvConfig.DESKTOP_URL,
            "desktop_proccess": EnvConfig.DESKTOP_PROCCESS,
        }
        safe = {k: ("****" if "PASS" in k else v) for k, v in vb.items()}
        logger.info("🔧 Variables base cargadas:\n" + json.dumps(safe, indent=2, ensure_ascii=False))
        return vb

    def ejecutar(self):
        logger.info("🚀 Servicio de migraciones iniciado...")
        t0 = perf_counter()
        exitos, fallos = 0, 0

        while True:
            try:
                # 1️⃣ Pendientes
                if not self.adapter.hay_pendientes_para_bot():
                    logger.info("🟡 No hay migraciones pendientes. Esperando ciclo...")
                    time.sleep(self.espera_post_logout)
                    continue

                # 2️⃣ Login
                migracion_mgr = MigracionActions(self.variables_base, {})
                if not migracion_mgr.ejecutar_inicio():
                    raise RPAExceptions.LoginException("Fallo en login inicial.")

                logger.info("✅ Sesión iniciada correctamente.")
                lote_actual = 0

                # 3️⃣ Ciclo activo
                while True:
                    if not self.adapter.hay_pendientes_para_bot():
                        logger.info("⏸ Sin pendientes. Cerrando sesión temporalmente...")
                        migracion_mgr.ejecutar_final()
                        time.sleep(self.espera_post_logout)
                        break

                    registro = self.adapter.obtener_siguiente_migracion()
                    if not registro:
                        time.sleep(self.delay_sin_pendientes)
                        continue

                    # 4️⃣ Preparar contexto
                    try:
                        contexto = self.preparador.preparar(registro)
                    except Exception as e:
                        fallos += 1
                        logger.error(f"❌ Error preparando contexto: {e}", exc_info=True)
                        continue

                    id_sharepoint = contexto.get("id_sharepoint", "N/A")

                    # 5️⃣ Ejecutar migración
                    for intento in range(1, self.reintentos_max + 1):
                        try:
                            migracion = MigracionActions(self.variables_base, contexto)
                            if migracion.ejecutar():
                                exitos += 1
                                logger.info(f"✅ Migración completada - ID {id_sharepoint} (Intento {intento})")
                                break

                        except RPAExceptions.ErrorBaseException as e:
                            fallos += 1
                            self._reportar_excepcion(e, id_sharepoint, t0, exitos, fallos)
                            return  # Detiene el servicio

                        except Exception as e:
                            fallos += 1
                            self._reportar_excepcion(e, id_sharepoint, t0, exitos, fallos)
                            return  # Detiene el servicio

                    # 6️⃣ Fin de lote
                    lote_actual += 1
                    if lote_actual >= self.lote_max:
                        logger.info("📦 Lote completo. Logout temporal...")
                        migracion_mgr.ejecutar_final()
                        time.sleep(5)
                        break

                    time.sleep(self.delay_entre_migraciones)

            except KeyboardInterrupt:
                logger.warning("🟥 Servicio detenido manualmente por el usuario.")
                break

            except Exception as e:
                fallos += 1
                self._reportar_excepcion(e, "GLOBAL", t0, exitos, fallos)
                break

        duracion = perf_counter() - t0
        logger.info(f"🏁 Servicio detenido. Éxitos: {exitos}, Fallos: {fallos}, Tiempo total: {duracion:.2f}s")

    def _reportar_excepcion(self, e: Exception, id_ref: str, t0: float, exitos: int, fallos: int):

        bot_name = getattr(EnvConfig, "BOT_NAME", None) or self.variables_base.get("terminal_log", "BOT_DESCONOCIDO")

        tipo_error = "ERROR_GENERAL"
        mensaje = str(e)
        if isinstance(e, RPAExceptions.ErrorBaseException):
            tipo_error = getattr(e, "tipo_error", e.__class__.__name__)
            mensaje = str(e)

        logger.critical(f"🚨 {tipo_error} en {id_ref} ({bot_name}): {mensaje}")

        try:
            asunto = f"[RPA - {bot_name}] 🚨 {tipo_error} - Ejecución detenida"
            cuerpo = (
                f"El proceso de migraciones del bot *{bot_name}* fue detenido automáticamente.\n\n"
                f"🆔 ID afectado: {id_ref}\n"
                f"💻 Tipo de error: {tipo_error}\n"
                f"📋 Detalle técnico: {mensaje}\n\n"
                f"📊 Procesados hasta ahora: {exitos + fallos}\n"
                f"⏱️ Tiempo total: {perf_counter() - t0:.2f} segundos.\n\n"
                f"⚙️ Variables base:\n"
                f"• Terminal: {self.variables_base.get('terminal_ruta')}\n"
                f"• Usuario: {self.variables_base.get('terminal_user')}\n"
            )

            self.mail_service.enviar(
                asunto=asunto,
                mensaje=cuerpo,
                tipo_error=tipo_error,
                contexto={"id_sharepoint": id_ref, "bot_name": bot_name}
            )
            logger.info(f"📨 Correo de error enviado ({tipo_error}) → {bot_name} → ID {id_ref}")

        except Exception as mail_err:
            logger.error(f"❌ Fallo al enviar correo: {mail_err}", exc_info=True)


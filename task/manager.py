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
        self.reintentos_max = 3              # intentos por registro ante falla TÉCNICA
        self.delay_entre_migraciones = 1
        self.delay_sin_pendientes = 30
        self.espera_post_logout = 60
        self.espera_recuperacion = 10        # espera entre logout y login de recuperación
        self.max_registros_con_fallas = 3    # freno sistémico: N registros consecutivos con fallas

    def _cargar_variables_base(self):
        vb = {
            "guacamole_user": EnvConfig.GUACAMOLE_USER,
            "guacamole_password": EnvConfig.GUACAMOLE_PASSWORD,
            "guacamole_url": EnvConfig.GUACAMOLE_URL,
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
        registros_consecutivos_con_fallas = 0

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
                    # Los reintentos aplican SOLO a fallas TÉCNICAS (excepciones).
                    # Los cierres de negocio mapeados (reclamo, observada, etc.)
                    # retornan True desde MigracionActions y NO se reintentan.
                    registro_con_fallas = False

                    for intento in range(1, self.reintentos_max + 1):
                        try:
                            migracion = MigracionActions(self.variables_base, contexto)
                            if migracion.ejecutar():
                                exitos += 1
                                logger.info(f"✅ Registro atendido - ID {id_sharepoint} (Intento {intento})")
                            else:
                                # Camino defensivo: cierre gestionado dentro de la acción.
                                exitos += 1
                                logger.info(f"📋 Registro cerrado por negocio - ID {id_sharepoint}")
                            break

                        except Exception as e:
                            # Normalizar: todo lo no tipificado se trata como técnico.
                            if not isinstance(e, RPAExceptions.ErrorBaseException):
                                e = RPAExceptions.FlujoException(f"{e.__class__.__name__}: {e}")
                            tipo = getattr(e, "tipo_error", "generico")
                            registro_con_fallas = True

                            # 🛑 Guardarraíl: si la migración ya tocó el sistema
                            # remoto, NO se reintenta (riesgo de doble migración).
                            if contexto.get("migracion_ejecutada"):
                                fallos += 1
                                self._reportar_excepcion(
                                    e, id_sharepoint, t0, exitos, fallos,
                                    motivo=("La migración pudo haberse aplicado en el sistema remoto. "
                                            "REQUIERE REVISIÓN MANUAL — no se reintenta para evitar doble migración.")
                                )
                                return

                            logger.warning(
                                f"🛠️ Falla técnica [{tipo}] en ID {id_sharepoint} "
                                f"(intento {intento}/{self.reintentos_max}): {e}"
                            )

                            if intento >= self.reintentos_max:
                                fallos += 1
                                self._reportar_excepcion(
                                    e, id_sharepoint, t0, exitos, fallos,
                                    motivo=f"El registro agotó {self.reintentos_max} intentos técnicos."
                                )
                                return

                            # ♻️ Recuperación a estado conocido: logout + login.
                            if not self._recuperar_sesion(migracion_mgr):
                                fallos += 1
                                self._reportar_excepcion(
                                    e, id_sharepoint, t0, exitos, fallos,
                                    motivo="No se pudo recuperar la sesión (logout+login) tras la falla técnica."
                                )
                                return

                            # Contexto limpio para el reintento (sin contaminación).
                            contexto = self.preparador.preparar(registro)

                    # 🚦 Freno sistémico: N registros consecutivos con fallas
                    # técnicas (aunque se hayan recuperado) = entorno inestable.
                    if registro_con_fallas:
                        registros_consecutivos_con_fallas += 1
                        if registros_consecutivos_con_fallas >= self.max_registros_con_fallas:
                            fallos += 1
                            self._reportar_excepcion(
                                RPAExceptions.ComunicacionException(
                                    "Entorno inestable: fallas técnicas en registros consecutivos."
                                ),
                                "SISTEMICO", t0, exitos, fallos,
                                motivo=(f"{registros_consecutivos_con_fallas} registros consecutivos "
                                        "sufrieron fallas técnicas. Posible caída de RDP/BCCS.")
                            )
                            return
                    else:
                        registros_consecutivos_con_fallas = 0

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

    def _recuperar_sesion(self, migracion_mgr: MigracionActions) -> bool:
        """Vuelve la aplicación remota a un estado conocido: logout + login."""
        logger.info("♻️ Recuperando sesión (logout + login)...")
        try:
            migracion_mgr.ejecutar_final()  # best-effort: captura errores internamente
        except Exception:
            logger.warning("⚠️ Logout de recuperación falló; se intenta login igualmente.")

        time.sleep(self.espera_recuperacion)

        try:
            if migracion_mgr.ejecutar_inicio():
                logger.info("✅ Sesión recuperada correctamente.")
                return True
        except Exception as e:
            logger.error(f"❌ Login de recuperación falló: {e}", exc_info=True)
        return False

    def _reportar_excepcion(self, e: Exception, id_ref: str, t0: float,
                            exitos: int, fallos: int, motivo: str = ""):

        bot_name = getattr(EnvConfig, "BOT_NAME", None) or self.variables_base.get("terminal_log", "BOT_DESCONOCIDO")

        tipo_error = "ERROR_GENERAL"
        mensaje = str(e)
        if isinstance(e, RPAExceptions.ErrorBaseException):
            tipo_error = getattr(e, "tipo_error", e.__class__.__name__)
            mensaje = str(e)

        env_key = getattr(e, "env_key", "MAIL_DEFAULT")
        destinatarios = getattr(EnvConfig, env_key, None) or EnvConfig.MAIL_DEFAULT

        logger.critical(f"🚨 {tipo_error} en {id_ref} ({bot_name}): {mensaje}")

        try:
            asunto = f"[RPA - {bot_name}] 🚨 {tipo_error.upper()} - Ejecución detenida"
            cuerpo = (
                f"El proceso de migraciones del bot *{bot_name}* fue detenido automáticamente.\n\n"
                f"🆔 ID afectado: {id_ref}\n"
                f"💻 Tipo de error: {tipo_error}\n"
                + (f"📌 Motivo: {motivo}\n" if motivo else "")
                + f"📋 Detalle técnico: {mensaje}\n\n"
                f"📊 Éxitos: {exitos} | Fallos: {fallos}\n"
                f"⏱️ Tiempo total: {perf_counter() - t0:.2f} segundos.\n\n"
                f"⚙️ Variables base:\n"
                f"• Terminal: {self.variables_base.get('terminal_ruta')}\n"
                f"• Usuario: {self.variables_base.get('terminal_user')}\n"
            )

            self.mail_service.enviar(
                asunto=asunto,
                mensaje=cuerpo,
                destinatarios=destinatarios,
                tipo_error=tipo_error,
                contexto={"id_sharepoint": id_ref, "bot_name": bot_name}
            )
            logger.info(f"📨 Correo de error enviado ({tipo_error}) → {destinatarios} → ID {id_ref}")

        except Exception as mail_err:
            logger.error(f"❌ Fallo al enviar correo: {mail_err}", exc_info=True)


from core.action_base.action_base import ActionBase

class PasoPostAPreAction(ActionBase):
    def __init__(self, variables_base, contexto):
        super().__init__(variables_base, contexto, flow_name="paso_post_a_pre", executor_type="desktop")

    def ejecutar(self):
        self.logger.info("🚀 Iniciando paso_post_a_pre action...")
        self.hora_inicio()

        try:
            # 🧩 Paso 1: Validación inicial
            self.executor.ejecutar_bloque("validation")

            # ✅ Caso 1: No hubo errores → ejecutar flujo principal
            if not self.executor.contexto.get("existe_error", False):
                self.executor.ejecutar_bloque("flow_post_a_pre")
                return True

            # ⚠️ Caso 2: Hubo error → verificar tipo
            mensaje_error = self.executor.contexto.get("mensaje_error", "")
            self.contexto["existe_error"] = True

            if "CUENTA ESTA BLOQUEADA" in mensaje_error.upper():
                # 🔐 Manejo especial de bloqueo
                self.logger.info("🔐 Cuenta bloqueada detectada. Ejecutando flujo de desbloqueo...")
                self.executor.ejecutar_bloque("reboot_validation")
                self.executor.ejecutar_bloque("flow_desbloqueo")

                # Reintento después del desbloqueo
                self.logger.info("🔄 Reintentando validación y flujo post a pre...")
                self.executor.ejecutar_bloque("validation")
                self.executor.ejecutar_bloque("flow_post_a_pre")
                return True

            else:
                self.logger.info("📝 Error distinto a bloqueo. Reiniciando validación...")
                self.executor.ejecutar_bloque("reboot_validation")

                id_sharepoint = self.contexto.get("id_sharepoint")
                self.contexto["linea_migrada"] = True
                self.contexto["mensaje_memo"] = f"Baja Realizada por otro Canal - ID solicitud: {id_sharepoint}"
                self.contexto["baja_realizada"] = "Baja Realizada por Otro Canal"
                self.registrar_observacion("La baja ya fue realizada por otro canal")

                return True

        except Exception as e:
            self.manejar_excepcion(e)
            try:
                self.executor.ejecutar_bloque("reboot_validation")
            except Exception:
                self.logger.warning("⚠️ Falló también reboot_validation", exc_info=True)

            raise  

        finally:
            self.hora_fin()

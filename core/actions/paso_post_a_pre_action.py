from core.action_base.action_base import ActionBase

class PasoPostAPreAction(ActionBase):
    def __init__(self, variables_base, contexto):
        super().__init__(variables_base, contexto, flow_name="paso_post_a_pre", executor_type="desktop")

    def ejecutar(self):
        self.logger.info("🚀 Iniciando paso_post_a_pre action...")
        self.hora_inicio()

        try:
            # 🧩 PASO 1: Validación inicial
            self.executor.ejecutar_bloque("validation")

            # ✅ CASO 1: Sin errores → continuar con el flujo normal
            if not self.contexto.get("existe_error", False):
                self.executor.ejecutar_bloque("flow_post_a_pre")
                return True

            mensaje_error = self.contexto.get("mensaje_error", "").upper()
            self.contexto["existe_error"] = True
            id_sharepoint = self.contexto.get("id_sharepoint")

            if "CUENTA ESTA BLOQUEADA" in mensaje_error:
                self.logger.info("🔐 Cuenta bloqueada detectada. Ejecutando flujo de desbloqueo...")

                self.executor.ejecutar_bloque("reboot_validation")
                self.executor.ejecutar_bloque("flow_desbloqueo")

                # Reintento tras desbloqueo
                self.logger.info("🔄 Reintentando validación y flujo post a pre...")
                self.executor.ejecutar_bloque("validation")
                self.executor.ejecutar_bloque("flow_post_a_pre")
                return True

            if "EL MOTIVO DE REGISTRACION EN IDCTL ES INVALIDO PARA ESTE PROCESO" in mensaje_error:
                self.logger.warning("⚠️ Motivo IDCTL inválido — cierre con reclamo.")
                self.executor.ejecutar_bloque("reboot_validation")

                self.contexto["linea_migrada"] = False
                self.contexto["mensaje_memo"] = f"Baja observada - ID solicitud: {id_sharepoint}"
                self.contexto["baja_realizada"] = "Baja Observada"
                self.registrar_observacion("La baja no se realizó — IDCTL está en COR")

                return False

            # ❌ CUALQUIER OTRO ERROR → cierre con reclamo
            self.logger.info("📝 Error distinto a bloqueo. Reiniciando validación...")
            self.executor.ejecutar_bloque("reboot_validation")
            self.contexto["linea_migrada"] = False
            self.contexto["mensaje_memo"] = f"Baja observada - ID solicitud: {id_sharepoint}"
            self.contexto["baja_realizada"] = "Baja Observada"
            self.registrar_observacion(f"La baja no realizada — error: {mensaje_error}")

            return False  # 👈 ERROR → debe cortar el proceso, NO continuar

        except Exception as e:
            self.manejar_excepcion(e)
            try:
                self.executor.ejecutar_bloque("reboot_validation")
            except Exception:
                self.logger.warning("⚠️ Falló también reboot_validation", exc_info=True)
            raise

        finally:
            self.hora_fin()

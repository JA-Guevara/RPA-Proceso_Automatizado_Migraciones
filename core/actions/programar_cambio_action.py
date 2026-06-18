from core.action_base.action_base import ActionBase

class ProgramarCambioAction(ActionBase):
    def __init__(self, variables_base, contexto):
        super().__init__(variables_base, contexto, flow_name="programar_cambio")

    def ejecutar(self):
        self.logger.info("🚀 Iniciando programar_cambio action...")
        self.hora_inicio()

        try:
            self.executor.ejecutar_bloque("validation")

            existe_error = self.executor.contexto.get("existe_error", False)
            mensaje_error = (self.executor.contexto.get("mensaje_error") or "").upper().strip()

            if not existe_error:
                self.logger.info("✅ Validación exitosa, ejecutando flujo post a pre...")
                self.executor.ejecutar_bloque("flow_post_a_pre")
                return True

            self.contexto["existe_error"] = True
            self.contexto["mensaje_error"] = mensaje_error

            if "CUENTA ESTA BLOQUEADA" in mensaje_error:
                self.logger.warning("🔐 Cuenta bloqueada detectada. Ejecutando flujo de desbloqueo...")
                self.executor.ejecutar_bloque("desbloqueo")

                self.logger.info("🔄 Reintentando validación y flujo post a pre después del desbloqueo...")
                self.executor.ejecutar_bloque("validation")

                if not self.executor.contexto.get("existe_error", False):
                    self.executor.ejecutar_bloque("flow_post_a_pre")
                    return True
                else:
                    self.logger.error("❌ Reintento fallido tras desbloqueo. Se procede a reboot_validation...")
                    self.executor.ejecutar_bloque("reboot_validation")
                    return False

            else:
                self.logger.warning(f"⚠️ Error detectado en ProgramarCambioAction: {mensaje_error}")
                self.executor.ejecutar_bloque("reboot_validation")
                self.registrar_observacion(f"Error detectado: {mensaje_error}")
                return False

        except Exception as e:
            self.manejar_excepcion(e)
            return False

        finally:
            self.hora_fin()



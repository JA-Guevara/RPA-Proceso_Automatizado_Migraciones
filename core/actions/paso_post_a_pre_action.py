from core.action_base.action_base import ActionBase

class PasoPostAPreAction(ActionBase):
    def __init__(self, variables_base, contexto):
        super().__init__(variables_base, contexto, flow_name="paso_post_a_pre")

    def ejecutar(self):
        self.logger.info("🚀 Iniciando paso_post_a_pre action...")
        self.hora_inicio()

        try:
            self.executor.ejecutar_bloque("validation")

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

                self.logger.info("🔄 Reintentando validación y flujo post a pre...")
                self.executor.ejecutar_bloque("validation")
                self.executor.ejecutar_bloque("flow_post_a_pre")
                return True

            if "EL MOTIVO DE REGISTRACION EN IDCTL ES INVALIDO PARA ESTE PROCESO" in mensaje_error:
                self.logger.warning("⚠️ Motivo IDCTL inválido — cierre con reclamo.")
                self.executor.ejecutar_bloque("reboot_validation")

                self.contexto["linea_error_migracion"] = True
                self.contexto["mensaje_memo"] = f"Baja observada - ID solicitud: {id_sharepoint}"
                self.contexto["baja_realizada"] = "Baja Observada"
                self.registrar_observacion("La baja no se realizó — IDCTL está en COR")

                return False

            self.logger.info("📝 Error distinto a bloqueo. Reiniciando validación...")
            self.executor.ejecutar_bloque("reboot_validation")
            self.contexto["linea_error_migracion"] = True
            self.contexto["mensaje_memo"] = f"Baja observada - ID solicitud: {id_sharepoint}"
            self.contexto["baja_realizada"] = "Baja Observada"
            self.registrar_observacion(f"La baja no realizada — error: {mensaje_error}")

            return False

        except Exception as e:
            self.manejar_excepcion(e)
            try:
                self.executor.ejecutar_bloque("reboot_validation")
            except Exception:
                self.logger.warning("⚠️ Falló también reboot_validation", exc_info=True)
            raise

        finally:
            self.hora_fin()



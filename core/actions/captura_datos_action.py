from core.action_base.action_base import ActionBase

class CapturaDatosAction(ActionBase):

    def __init__(self, variables_base, contexto):
        super().__init__(variables_base, contexto,
                         flow_name="captura_datos")

    def ejecutar(self):
        self.logger.info("🚀 Iniciando captura_datos action...")
        self.hora_inicio()

        try:
            self.executor.ejecutar_bloque("flow")

            if self.contexto.get("existe_error_captura", False):
                self.logger.warning("⚠️ Error en captura de fecha, reintentando una vez...")

                self.contexto["existe_error_captura"] = False

                self.executor.ejecutar_bloque("flow")

            if self.contexto.get("existe_error_captura", False):
                mensaje = self.contexto.get(
                    "mensaje_error",
                    "Error desconocido en captura de fecha"
                )

                self.logger.error(f"❌ CapturaDatosAction finaliza con error: {mensaje}")

                self.contexto.update({
                    "estado_final": "ERROR_CAPTURA_FECHA",
                    "observaciones_rpa": mensaje
                })

                return False

            return True

        except Exception as e:
            self.manejar_excepcion(e)
            self.contexto.update({
                "estado_final": "ERROR_TECNICO_CAPTURA",
                "observaciones_rpa": str(e)
            })
            return False

        finally:
            self.hora_fin()
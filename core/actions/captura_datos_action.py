from core.action_base.action_base import ActionBase


class CapturaDatosAction(ActionBase):

    def __init__(self, variables_base, contexto):
        super().__init__(
            variables_base,
            contexto,
            flow_name="captura_datos",
        )

    def ejecutar(self) -> bool:
        self.logger.info("🚀 Iniciando CapturaDatosAction...")
        self.hora_inicio()

        try:
            self.contexto["existe_error_captura"] = False
            self.contexto.pop("mensaje_error", None)

            self.executor.ejecutar_bloque("flow")
            
            if self.contexto.get("existe_error_captura", False):
                primer_error = self.contexto.get(
                    "mensaje_error",
                    "Error desconocido capturando la fecha",
                )

                self.logger.warning(
                    "⚠️ Error capturando fecha: %s. "
                    "Reintentando una vez...",
                    primer_error,
                )
                self.contexto["existe_error_captura"] = False
                self.contexto.pop("mensaje_error", None)

                self.executor.ejecutar_bloque("flow")

            if self.contexto.get("existe_error_captura", False):
                mensaje = self.contexto.get(
                    "mensaje_error",
                    "Error desconocido en captura de fecha",
                )

                self.contexto.update({
                    "estado_final": "ERROR_CAPTURA_FECHA",
                    "validacion_exitosa": False,
                })
                self.registrar_observacion(
                    mensaje,
                    tipo="error",
                )

                self.logger.error(
                    "❌ CapturaDatosAction finaliza con error controlado: %s",
                    mensaje,
                )

                return False
            self.contexto["existe_error_captura"] = False
            self.contexto.pop("mensaje_error", None)

            self.logger.info(
                "✅ CapturaDatosAction finalizó correctamente."
            )
            return True

        except Exception as e:
            self.contexto.update({
                "estado_final": "ERROR_TECNICO_CAPTURA",
                "validacion_exitosa": False,
            })

            self.registrar_observacion(
                f"Error técnico durante la captura: {e}",
                tipo="error",
            )

            # Este método registra y vuelve a lanzar la excepción.
            self.manejar_excepcion(e)

        finally:
            self.hora_fin()
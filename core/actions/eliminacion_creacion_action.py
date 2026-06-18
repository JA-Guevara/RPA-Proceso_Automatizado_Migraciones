from core.action_base.action_base import ActionBase

class EliminacionCreacionAction(ActionBase):
    def __init__(self, variables_base, contexto):
        super().__init__(variables_base, contexto, flow_name="eliminacion_creacion")

    def ejecutar(self):
        self.logger.info("🚀 Iniciando eliminacion_creacion action...")
        self.hora_inicio()

        try:
            self.executor.ejecutar_bloque("flow")
            self.contexto["servicios_asignados_rpa"] = (
                self.contexto.get("servicios_asignados_rpa", "") + "Eliminacion y Creacion de cuenta, "
            )
            return True

        except Exception as e:
            self.manejar_excepcion(e)
            try:
                self.executor.ejecutar_bloque("reboot_eliminacion_creacion")
            except Exception:
                self.logger.warning("⚠️ Falló también reboot_eliminacion_creacion", exc_info=True)
            raise  

        finally:
            self.hora_fin()



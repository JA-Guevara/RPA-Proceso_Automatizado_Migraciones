from core.action_base.action_base import ActionBase

class CargaReclamosAction(ActionBase):
    def __init__(self, variables_base, contexto):
        super().__init__(variables_base, contexto, flow_name="carga_reclamos")

    def ejecutar(self):
        self.logger.info("🚀 Iniciando carga_reclamos action...")
        self.hora_inicio()

        try:
            self.executor.ejecutar_bloque("flow")
            return True

        except Exception as e:
            self.manejar_excepcion(e)
            try:
                self.executor.ejecutar_bloque("reboot_carga_reclamos")
            except Exception:
                self.logger.warning("⚠️ Falló también reboot_carga_reclamos", exc_info=True)

            raise  

        finally:
            self.hora_fin()



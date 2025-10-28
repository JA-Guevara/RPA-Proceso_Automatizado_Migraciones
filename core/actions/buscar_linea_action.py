from core.action_base.action_base import ActionBase

class BuscarLineaAction(ActionBase):
    def __init__(self, variables_base, contexto):
        super().__init__(variables_base, contexto, flow_name="buscar_linea", executor_type="desktop")

    def ejecutar(self, modo="entrar"):  
        self.logger.info("🚀 Iniciando BuscarLineaAction...")
        self.hora_inicio()
        try:
            if modo == "salir":
                self.logger.info("⬅️ Modo salir: ejecutando bloque salir_buscar_linea")
                self.executor.ejecutar_bloque("salir_buscar_linea")
            else:
                self.logger.info("➡️ Modo entrar: ejecutando bloque flow")
                self.executor.ejecutar_bloque("flow")
            return True

        except Exception as e:
            self.manejar_excepcion(e)
            raise  
            
        finally:
            self.hora_fin()

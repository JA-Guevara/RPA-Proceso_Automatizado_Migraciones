from core.action_base.action_base import ActionBase

class EliminacionServiciosAction(ActionBase):
    def __init__(self, variables_base, contexto):
        super().__init__(variables_base, contexto, flow_name="eliminacion_servicios")

    def ejecutar(self):
        self.logger.info("🚀 Iniciando eliminacion_servicios action...")
        self.hora_inicio()
        try:
            # 1️⃣ Abrir ventana de servicios y confirmar presencia de pantalla_servicios_icon
            self.executor.ejecutar_bloque("open_servicios")

            if not self.contexto.get("servicios_successful", False):
                self.logger.warning("⚠️ No se pudo acceder a la pantalla de servicios de BCCS tras los reintentos.")
                self.executor.ejecutar_bloque("reboot_validation")
                self.contexto["linea_error_migracion"] = True
                self.contexto["baja_realizada"] = "Baja Observada"
                id_sp = self.contexto.get("id_sharepoint", "")
                self.contexto["mensaje_memo"] = f"Baja observada - ID solicitud: {id_sp}"
                self.registrar_observacion("La baja no se realizó — no se pudo acceder a la pantalla de servicios en BCCS")
                return False

            # 2️⃣ Con la pantalla confirmada, buscar si la línea tiene la restricción
            self.executor.ejecutar_bloque("check_restriccion")

            if self.contexto.get("existeRestringirNav", False):
                self.logger.info("✅ Restricción detectada → ejecutando flow_eliminacion")
                self.executor.ejecutar_bloque("flow_eliminacion")
                self.contexto["servicios_eliminados_rpa"] = self.contexto.get("servicios_eliminados_rpa", "") + "Restringir Navegación sin Nominación"
                return True
            else:
                self.logger.info("📌 Sin restricciones presentes → ejecutando reboot_validation")
                self.executor.ejecutar_bloque("reboot_validation")
                self.contexto["servicios_eliminados_rpa"] = self.contexto.get("servicios_eliminados_rpa", "") 
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



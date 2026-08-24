from core.action_base.action_base import ActionBase
from shared.tools.clipboard import specs

class ValidationIdctlActualAction(ActionBase):
    def __init__(self, variables_base, contexto):
        super().__init__(variables_base, contexto, flow_name="validation_idctl_actual")
        self.executor._action_extraer_validar_plan_programado = self.extraer_validar_plan_programado

    def ejecutar(self):
        self.logger.info("🚀 Iniciando validation_idctl_actual action...")
        self.hora_inicio()
        try:
            self.executor.ejecutar_bloque("validation")

            idctl_actual = self.contexto.get("idctl_actual_rpa", "").strip().upper()
            ocr_fallo = self.contexto.get("existe_error_ocr_idctl_actual_rpa", False)
            self.logger.info(f"🔍 IDCTL detectada: '{idctl_actual}' (ocr_fallo={ocr_fallo})")

            # Con "" fuera de palabras_validas en el flow, un OCR ilegible ya no
            # se confunde con "campo vacio, todo bien".
            if ocr_fallo:
                self.contexto["mensaje_memo"] = (
                    f"Baja Observada - ID solicitud: {self.contexto.get('id_sharepoint')}"
                )
                self.contexto["baja_realizada"] = "Baja Observada"
                self.registrar_observacion(
                    "No se pudo leer el Motivo de Registracion (IDCTL) - OCR ilegible.",
                    tipo="error",
                )
                return False

            if idctl_actual != "COR":
                self.logger.info("✅ IDCTL no es 'COR', continúa el proceso.")
                self.executor.ejecutar_bloque("flow_plan_programado")

                existe_cambio_pendiente = self.contexto.get("existe_cambio_pendiente_rpa", False)
                if existe_cambio_pendiente:
                    self.logger.info("🔄 Cambio de plan pendiente detectado, ejecutando flujo de cambio de plan...")
                    self.executor.ejecutar_bloque("flow_cambio_plan")

                return True

            else:
                id_sharepoint = self.contexto.get("id_sharepoint")
                self.contexto["mensaje_memo"] = f"Baja Observada - ID solicitud: {id_sharepoint}"
                self.registrar_observacion("El Motivo de Registración en IDCTL es inválido para este proceso")
                self.contexto["baja_realizada"] = "Baja Observada"
                return False

        except Exception as e:
            self.manejar_excepcion(e)
            try:
                self.logger.warning("🔁 Ejecutando reboot_validation como fallback...")
                self.executor.ejecutar_bloque("reboot_validation")
            except Exception:
                self.logger.warning("⚠️ Falló también reboot_validation", exc_info=True)
            raise  

        finally:
            self.hora_fin()


    def extraer_validar_plan_programado(self, paso):
        self.logger.info("🔍 Ejecutando acción personalizada: extraer_validar_plan_programado")

        try:
            ruta, nombre = self.executor._resolver_imagen(paso.get("target"))

            self.clicker.hacer_clic(
                target=ruta,
                offset_x=paso.get("offset_x", 0),
                offset_y=paso.get("offset_y", 0),
                clicks=paso.get("clicks", 1),
                nombre_logico=nombre,
                usar_imagen=paso.get("usar_imagen", True),
                raise_error=paso.get("raise_error", True),
                transitorio=paso.get("transitorio", False),
            )

            self.app_tools.esperar(1)
            self.app_tools.presionar_tecla_real("up")
            self.app_tools.presionar_tecla_real("up")

            texto = self.basic_tools.copiar_texto_actual(
                seleccionar_todo=False,
                limpiar=True,
                mayusculas=False,
                usar_real=True,
                spec=specs.PLAN_PROGRAMADO,
            )

            self.logger.info(f"📋 Texto copiado (primeras 300 chars):\n{texto[:300]}...")

            lineas = texto.splitlines()
            pendiente_detectado = False

            for linea in lineas:
                columnas = linea.split("\t")

                if len(columnas) >= 5:
                    estado = columnas[4].strip().upper()

                    if "PENDIENTE" in estado:
                        pendiente_detectado = True
                        break

            self.contexto["existe_cambio_pendiente_rpa"] = pendiente_detectado

            if pendiente_detectado:
                self.logger.warning("⚠️ Se encontró al menos un registro con estado 'Pendiente'")
            else:
                self.logger.info("✅ No se encontraron registros pendientes")

            return pendiente_detectado

        except Exception as e:
            self.logger.error(f"❌ Error en extraer_validar_plan_programado: {e}", exc_info=True)
            self.contexto["existe_cambio_pendiente_rpa"] = False
            return False
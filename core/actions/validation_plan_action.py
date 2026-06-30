from core.action_base.action_base import ActionBase
from infrastructure.database.adapters.planes_adapter import PlanesSQLAdapter


class ValidationPlanAction(ActionBase):
    def __init__(self, variables_base, contexto):
        super().__init__(variables_base, contexto, flow_name="validation_plan")
        self.plan_adapter = PlanesSQLAdapter()

    def ejecutar(self, modo="extraer_inicial"):
        self.logger.info("🚀 Iniciando ValidationPlanAction en modo: %s", modo)
        self.hora_inicio()

        try:
            if modo == "extraer_inicial":
                return self._validar_plan_inicial()

            if modo == "extraer_final":
                return self._validar_plan_final()

            self.logger.error("❌ Modo no reconocido: %s", modo)
            self.contexto.update({"plan_valido": False, "validacion_exitosa": False})
            return False

        except Exception as e:
            self.contexto.update({"plan_valido": False, "validacion_exitosa": False})
            self.manejar_excepcion(e)
            raise

        finally:
            self.hora_fin()

    def _validar_plan_inicial(self) -> bool:
        self.executor.ejecutar_bloque("extraer_plan_actual")

        if self.contexto.get("existe_error_captura_plan", False):
            self.logger.warning("⚠️ Error capturando plan_actual → Reintentando extracción...")
            self.contexto["existe_error_captura_plan"] = False
            self.executor.ejecutar_bloque("extraer_plan_actual")

        plan_actual_rpa = self.contexto.get("plan_actual_rpa", "")
        tipo_baja = self.contexto.get("tipo_baja")
        id_tipo_baja = self.contexto.get("id_tipo_baja")
        id_tipo_lista = self.contexto.get("id_tipo_lista")
        id_sharepoint = self.contexto.get("id_sharepoint")

        ok_inicio = self.plan_adapter.es_plan_valido(id_tipo_lista, plan_actual_rpa, "INICIAL")

        if ok_inicio:
            self.logger.info("✅ Plan '%s' habilitado para lista %s (tipo_baja=%s)", plan_actual_rpa, id_tipo_lista, tipo_baja)
            self.contexto.update({
                "plan_valido": True,
                "validacion_exitosa": True,
                "mensaje_memo": "",
                "baja_realizada": ""
            })
            return True

        ok_final = self.plan_adapter.es_plan_valido(id_tipo_lista, plan_actual_rpa, "FINAL")

        if ok_final:
            self.logger.info("ℹ️ Plan '%s' válido como FINAL → migrado por otro canal.", plan_actual_rpa)
            self.contexto.update({
                "plan_valido": True,
                "validacion_exitosa": False,
                "mensaje_memo": f"Baja Realizada por otro Canal - ID solicitud: {id_sharepoint}",
                "baja_realizada": "Baja Realizada por Otro Canal"
            })
            self.registrar_observacion("Línea ya migrada por otro canal antes de ejecución del bot")
            return False

        diagnostico = self.plan_adapter.diagnosticar_plan(id_tipo_lista, plan_actual_rpa)

        motivo = self._construir_motivo_plan_no_valido(
            diagnostico=diagnostico,
            nombre_plan=plan_actual_rpa,
            id_tipo_lista=id_tipo_lista,
            tipo_baja=tipo_baja,
            id_tipo_baja=id_tipo_baja,
            etapa="INICIAL ni FINAL"
        )

        self.logger.warning("❌ %s", motivo)
        self.contexto.update({
            "plan_valido": False,
            "validacion_exitosa": False,
            "mensaje_memo": f"Baja observada - ID solicitud: {id_sharepoint}",
            "baja_realizada": "Baja Observada"
        })
        self.registrar_observacion(motivo)
        return False

    def _validar_plan_final(self) -> bool:
        self.executor.ejecutar_bloque("extraer_plan_asignado")

        if self.contexto.get("existe_error_captura_plan", False):
            self.logger.warning("⚠️ Error capturando plan_asignado → Reintentando extracción...")
            self.contexto["existe_error_captura_plan"] = False
            self.executor.ejecutar_bloque("extraer_plan_asignado")

        plan_asignado_rpa = self.contexto.get("plan_asignado_rpa", "")
        tipo_baja = self.contexto.get("tipo_baja")
        id_tipo_baja = self.contexto.get("id_tipo_baja")
        id_tipo_lista = self.contexto.get("id_tipo_lista")
        id_sharepoint = self.contexto.get("id_sharepoint")

        self.logger.info("📥 Plan final extraído: %s", plan_asignado_rpa)

        ok_final = self.plan_adapter.es_plan_valido(id_tipo_lista, plan_asignado_rpa, "FINAL")

        if ok_final:
            self.logger.info("✅ Validación final correcta | asignado=%s", plan_asignado_rpa)
            self.contexto.update({
                "plan_valido": True,
                "validacion_exitosa": True,
                "mensaje_memo": f"{tipo_baja} - ID solicitud: {id_sharepoint}",
                "baja_realizada": "Baja Procesada"
            })
            self.registrar_observacion("Migración realizada correctamente")
            return True

        diagnostico = self.plan_adapter.diagnosticar_plan(id_tipo_lista, plan_asignado_rpa)

        motivo = self._construir_motivo_plan_no_valido(
            diagnostico=diagnostico,
            nombre_plan=plan_asignado_rpa,
            id_tipo_lista=id_tipo_lista,
            tipo_baja=tipo_baja,
            id_tipo_baja=id_tipo_baja,
            etapa="FINAL"
        )

        plan_inicial_valido = self.contexto.get("plan_valido", False)

        if plan_inicial_valido:
            self.logger.warning("⚠️ Validación final no exitosa, pero plan inicial era válido. Motivo: %s", motivo)
            self.contexto.update({
                "plan_valido": True,
                "validacion_exitosa": False,
                "mensaje_memo": f"Baja observada - ID solicitud: {id_sharepoint}",
                "baja_realizada": "Baja Observada"
            })
            self.registrar_observacion(motivo)
            return True

        self.logger.warning("🚫 Validación final fallida y plan no válido → cierre con reclamo. Motivo: %s", motivo)
        self.contexto.update({
            "plan_valido": False,
            "validacion_exitosa": False,
            "mensaje_memo": f"Baja observada - ID solicitud: {id_sharepoint}",
            "baja_realizada": "Baja Observada"
        })
        self.registrar_observacion(motivo)
        return False


    def _construir_motivo_plan_no_valido(
        self,
        diagnostico,
        nombre_plan,
        id_tipo_lista,
        tipo_baja,
        id_tipo_baja,
        etapa,
    ) -> str:
        nombre_plan_limpio = str(nombre_plan or "").strip()

        if diagnostico.error_consulta:
            return "No fue posible consultar el catálogo de planes."

        if not diagnostico.entrada_valida:
            return "No fue posible validar el plan extraído."

        if not diagnostico.existe:
            return f"Plan no encontrado en catálogo: {nombre_plan_limpio}"

        if not diagnostico.existe_para_lista:
            return f"Plan no habilitado para este proceso: {nombre_plan_limpio}"

        return f"Plan no habilitado como {etapa}: {nombre_plan_limpio}"
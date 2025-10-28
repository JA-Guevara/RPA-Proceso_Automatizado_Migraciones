from core.action_base.action_base import ActionBase
from infrastructure.database.adapters.planes_adapter import PlanesSQLAdapter

class ValidationPlanAction(ActionBase):
    def __init__(self, variables_base, contexto):
        super().__init__(variables_base, contexto, flow_name="validation_plan", executor_type="desktop")
        self.plan_adapter = PlanesSQLAdapter()

    def ejecutar(self, modo="extraer_inicial"):
        self.logger.info(f"🚀 Iniciando ValidationPlanAction en modo: {modo}")
        self.hora_inicio()

        try:
            if modo == "extraer_inicial":
                # 🔹 Ejecutar bloque de extracción
                self.executor.ejecutar_bloque("extraer_plan_actual")

                plan_actual_rpa = self.contexto.get("plan_actual_rpa", "")
                tipo_baja = self.contexto.get("tipo_baja")
                id_tipo_baja = self.contexto.get("id_tipo_baja")
                id_tipo_lista = self.contexto.get("id_tipo_lista")
                id_sharepoint = self.contexto.get("id_sharepoint")

                # --- Validación de plan INICIAL ---
                ok_inicio = self.plan_adapter.es_plan_valido(id_tipo_baja, id_tipo_lista, plan_actual_rpa, "INICIAL")

                if ok_inicio:
                    self.logger.info(f"✅ Plan {plan_actual_rpa} habilitado para lista {id_tipo_lista} (tipo_baja={tipo_baja})")
                    self.contexto.update({
                        "plan_valido": True,
                        "validacion_exitosa": True,
                        "mensaje_memo": "",
                        "baja_realizada": ""
                    })
                    return True

                # 🔁 No es válido como INICIAL → verificamos FINAL
                ok_final = self.plan_adapter.es_plan_valido(id_tipo_baja, id_tipo_lista, plan_actual_rpa, "FINAL")

                if ok_final:
                    self.logger.info(f"ℹ️ Plan '{plan_actual_rpa}' válido como FINAL → migrado por otro canal.")
                    self.contexto.update({
                        "plan_valido": True,
                        "validacion_exitosa": False,
                        "mensaje_memo": f"Baja Realizada por otro Canal - ID solicitud: {id_sharepoint}",
                        "baja_realizada": "Baja Realizada por Otro Canal"
                    })
                    self.registrar_observacion("Línea ya migrada por otro canal antes de ejecución del bot")
                    return False

                # ❌ No es válido ni INICIAL ni FINAL
                self.logger.warning(f"❌ Plan '{plan_actual_rpa}' no habilitado ni como INICIAL ni FINAL.")
                self.contexto.update({
                    "plan_valido": False,
                    "validacion_exitosa": False,
                    "mensaje_memo": f"Baja observada - ID solicitud: {id_sharepoint}",
                    "baja_realizada": "Baja Observada"
                })
                self.registrar_observacion("Plan no habilitado para migración (inicial/final)")
                return False

            elif modo == "extraer_final":
                # 🔹 Validación final del plan asignado
                self.executor.ejecutar_bloque("extraer_plan_asignado")

                plan_asignado_rpa = self.contexto.get("plan_asignado_rpa", "")
                tipo_baja = self.contexto.get("tipo_baja")
                id_tipo_baja = self.contexto.get("id_tipo_baja")
                id_tipo_lista = self.contexto.get("id_tipo_lista")
                id_sharepoint = self.contexto.get("id_sharepoint")

                self.logger.info(f"📥 Plan final extraído: {plan_asignado_rpa}")

                ok_final = self.plan_adapter.es_plan_valido(id_tipo_baja, id_tipo_lista, plan_asignado_rpa, "FINAL")

                if ok_final:
                    self.logger.info(f"✅ Validación final correcta | asignado={plan_asignado_rpa}")
                    self.contexto.update({
                        "plan_valido": True,
                        "validacion_exitosa": True,
                        "mensaje_memo": f"{tipo_baja} - ID solicitud: {id_sharepoint}",
                        "baja_realizada": "Baja Procesada"
                    })
                    self.registrar_observacion("Migración realizada correctamente")
                    return True

                else:
                    plan_inicial_valido = self.contexto.get("plan_valido", False)
                    if plan_inicial_valido:
                        self.logger.warning("⚠️ Validación final no exitosa, pero plan inicial era válido.")
                        self.contexto.update({
                            "plan_valido": True,
                            "validacion_exitosa": False,
                            "mensaje_memo": f"Baja observada - ID solicitud: {id_sharepoint}",
                            "baja_realizada": "Baja Observada"
                        })
                        self.registrar_observacion("Plan final no se reflejó correctamente.")
                        return True
                    else:
                        self.logger.warning("🚫 Validación final fallida y plan no válido → cierre con reclamo.")
                        self.contexto.update({
                            "plan_valido": False,
                            "validacion_exitosa": False,
                            "mensaje_memo": f"Baja observada - ID solicitud: {id_sharepoint}",
                            "baja_realizada": "Baja Observada"
                        })
                        self.registrar_observacion("Plan final no coincide con las reglas de negocio.")
                        return False

            else:
                self.logger.error(f"❌ Modo no reconocido: {modo}")
                self.contexto.update({
                    "plan_valido": False,
                    "validacion_exitosa": False
                })
                return False

        except Exception as e:
            self.manejar_excepcion(e)
            self.contexto.update({
                "plan_valido": False,
                "validacion_exitosa": False
            })
            raise  

        finally:
            self.hora_fin()

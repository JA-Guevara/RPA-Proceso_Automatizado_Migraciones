import pyperclip
from core.action_base.action_base import ActionBase

class ValidationEstadoControladoAction(ActionBase):
    def __init__(self, variables_base, contexto):
        super().__init__(variables_base, contexto,
                         flow_name="validation_estado_controlado")
        self.executor._action_extraer_validar_controlado = self.extraer_situacion_ventas

    def ejecutar(self):
        self.logger.info("🚀 Iniciando validation_estado_controlado action...")
        self.hora_inicio()

        try:
            self.executor.ejecutar_bloque("validation")
            situacion = self.contexto.get("situacion", "").strip().upper()
            cns_cancelado = self.contexto.get("cnsCancelado", True)

            if situacion != "PROPIO":
                self.logger.info(f"🔍 Situación detectada: {situacion} — iniciando validación CNS...")
                self.executor.ejecutar_bloque("flow - validacionCNS")

                if cns_cancelado:
                    self.logger.info("✅ Validación OK: CNS cancelado y situación distinta de PROPIO.")
                    self.executor.ejecutar_bloque("flow - cambioPropio")
                    self.contexto.update({
                        "situacion_cuenta_anterior_rpa": situacion,
                        "situacion_cuenta_posterior_rpa": "PROPIO",
                        "baja_realizada": ""
                    })
                    return True
                else:
                    self.logger.warning("⚠️ CNS no cancelado → cierre con reclamo.")
                    self.contexto.update({
                        "baja_realizada": "Baja Observada",
                        "mensaje_memo": f"Baja Observada - CNS no cancelado - ID solicitud: {self.contexto.get('id_sharepoint')}"
                    })
                    return False
            else:
                self.logger.info("✅ Situación es 'PROPIO', no se requiere validación adicional.")
                self.contexto.update({
                    "situacion_cuenta_anterior_rpa": situacion,
                    "situacion_cuenta_posterior_rpa": situacion,
                    "baja_realizada": ""
                })
                return True

        except Exception as e:
            self.manejar_excepcion(e)
            try:
                self.logger.warning("🔁 Ejecutando reboot_validation como fallback...")
                self.executor.ejecutar_bloque("reboot_validation")
            except Exception as err:
                self.logger.warning(f"⚠️ Error al ejecutar reboot_validation: {err}", exc_info=True)

            raise  

        finally:
            self.hora_fin()

    def extraer_situacion_ventas(self, paso):
        self.logger.info("🔍 Ejecutando acción personalizada: extraer_situacion_ventas")

        try:
            ruta, nombre = self.executor._resolver_imagen(paso.get("target"))

            self.clicker.hacer_clic(
                target=ruta,
                offset_x=paso.get("offset_x", 0),
                offset_y=paso.get("offset_y", 0),
                clicks=paso.get("clicks", 2),
                nombre_logico=nombre,
                usar_imagen=paso.get("usar_imagen", True),
                raise_error=paso.get("raise_error", True),
                transitorio=paso.get("transitorio", False),
            )

            self.app_tools.esperar(0.2)
            self.app_tools.presionar_tecla_real("up")

            texto = self.basic_tools.copiar_texto_actual(
                seleccionar_todo=False,
                limpiar=True,
                mayusculas=True,
                usar_real=True,
                timeout=12.0,
            )

            if not texto:
                self.logger.warning("⚠️ No se pudo capturar texto para validar CNS.")
                self.contexto["cnsCancelado"] = False
                self.contexto["mensaje_memo"] = (
                    f"Baja Observada - No se pudo capturar CNS - "
                    f"ID solicitud: {self.contexto.get('id_sharepoint')}"
                )
                self.contexto["baja_realizada"] = "Baja Observada"
                return

            lineas = [line.strip() for line in texto.splitlines() if line.strip()]
            self.logger.info(f"📋 Texto capturado: {len(lineas)} líneas detectadas")

            nro_cuenta = self.contexto.get("nro_linea", "").strip()
            id_sharepoint = self.contexto.get("id_sharepoint")
            valor_residual = str(self.contexto.get("valor_residual", "0")).strip().replace(",", ".")
            tipo_cns = self.contexto.get("tipo_cns", "CNS").strip().upper()

            encontrado = False

            for linea in lineas:
                partes = linea.split()

                if len(partes) < 4:
                    continue

                tipo = partes[0].strip().upper()
                cuenta = partes[5].strip() if len(partes) > 5 else ""
                saldo = partes[-2].replace(",", ".") if len(partes) > 2 else ""
                estado = partes[-1].strip().upper() if len(partes) > 1 else ""

                if tipo == tipo_cns and cuenta == nro_cuenta:
                    match_saldo = saldo == valor_residual
                    match_estado = estado == "CANCELADO"

                    self.contexto["cnsCancelado"] = match_saldo and match_estado
                    encontrado = True
                    break

            if not encontrado:
                self.contexto["cnsCancelado"] = False
                self.contexto["mensaje_memo"] = (
                    f"Baja Observada - No se encontró CNS - "
                    f"ID solicitud: {id_sharepoint}"
                )
                self.contexto["baja_realizada"] = "Baja Observada"

            else:
                if not self.contexto["cnsCancelado"]:
                    self.contexto["mensaje_memo"] = (
                        f"Baja Observada - CNS no se encuentra cancelado - "
                        f"ID solicitud: {id_sharepoint}"
                    )
                    self.contexto["baja_realizada"] = "Baja Observada"
                else:
                    self.contexto["mensaje_memo"] = ""

            self.logger.info(
                f"✅ Resultado CNS: Cancelado = {self.contexto['cnsCancelado']} "
                f"| Mensaje: '{self.contexto['mensaje_memo']}'"
            )

        except Exception as e:
            self.logger.error(f"❌ Error al extraer situación de ventas: {e}", exc_info=True)
            raise
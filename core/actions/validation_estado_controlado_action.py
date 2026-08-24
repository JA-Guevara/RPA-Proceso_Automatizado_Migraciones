from core.action_base.action_base import ActionBase
from shared.tools.clipboard import specs


class ValidationEstadoControladoAction(ActionBase):

    def __init__(self, variables_base, contexto):
        super().__init__(
            variables_base,
            contexto,
            flow_name="validation_estado_controlado"
        )

        self.executor._action_extraer_validar_controlado = (
            self.extraer_situacion_ventas
        )

    def ejecutar(self):
        self.logger.info(
            "🚀 Iniciando validation_estado_controlado action..."
        )

        self.hora_inicio()

        try:
            self.executor.ejecutar_bloque("validation")

            situacion = (
                self.contexto.get("situacion", "")
                .strip()
                .upper()
            )
            self.contexto["situacion_cuenta_anterior_rpa"] = situacion

            self.logger.info(
                f"🔎 Situación detectada: {situacion}"
            )

            if situacion != "PROPIO":

                self.logger.info(
                    f"🔍 Situación '{situacion}' distinta de PROPIO "
                    f"→ iniciando validación CNS..."
                )

                self.executor.ejecutar_bloque(
                    "flow - validacionCNS"
                )

                cns_cancelado = self.contexto.get(
                    "cnsCancelado",
                    False
                )

                if isinstance(cns_cancelado, str):
                    cns_cancelado = (
                        cns_cancelado.strip().lower()
                        in ("true", "1", "si", "sí")
                    )
                else:
                    cns_cancelado = bool(cns_cancelado)

                self.logger.info(
                    f"🔎 cnsCancelado tras la validación = "
                    f"{cns_cancelado}"
                )

                if cns_cancelado:

                    self.logger.info(
                        "✅ Validación OK: "
                        "CNS cancelado y situación distinta de PROPIO."
                    )

                    self.executor.ejecutar_bloque(
                        "flow - cambioPropio"
                    )

                    self.contexto.update({
                        "situacion_cuenta_anterior_rpa": situacion,
                        "situacion_cuenta_posterior_rpa": "PROPIO",
                        "baja_realizada": "",
                        "mensaje_memo": "",
                    })

                    return True

                else:

                    self.logger.warning(
                        "⚠️ CNS no cancelado → cierre con reclamo."
                    )

                    id_sharepoint = self.contexto.get(
                        "id_sharepoint",
                        ""
                    )

                    mensaje_cns = self.contexto.get(
                        "mensaje_memo",
                        ""
                    ).strip()

                    if not mensaje_cns:
                        mensaje_cns = (
                            "Baja Observada - "
                            "CNS no cancelado - "
                            f"ID solicitud: {id_sharepoint}"
                        )

                    self.contexto.update({
                        "baja_realizada": "Baja Observada",
                        "mensaje_memo": mensaje_cns,
                        "mensaje_observacion_rpa": self._agregar_observacion(
                            mensaje_cns
                        ),
                    })

                    self.logger.info(
                        f"📝 Observación CNS registrada: {mensaje_cns}"
                    )

                    return False

            else:

                self.logger.info(
                    "✅ Situación es 'PROPIO', "
                    "no se requiere validación adicional."
                )

                self.contexto.update({
                    "situacion_cuenta_anterior_rpa": situacion,
                    "situacion_cuenta_posterior_rpa": situacion,
                    "baja_realizada": "",
                    "mensaje_memo": "",
                })

                return True

        except Exception as e:

            self.manejar_excepcion(e)

            try:
                self.logger.warning(
                    "🔁 Ejecutando reboot_validation como fallback..."
                )

                self.executor.ejecutar_bloque(
                    "reboot_validation"
                )

            except Exception as err:

                self.logger.warning(
                    f"⚠️ Error al ejecutar reboot_validation: {err}",
                    exc_info=True
                )

            raise

        finally:
            self.hora_fin()

    def extraer_situacion_ventas(self, paso):

        self.logger.info(
            "🔍 Ejecutando acción personalizada: "
            "extraer_situacion_ventas"
        )

        try:

            ruta, nombre = self.executor._resolver_imagen(
                paso.get("target")
            )

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
                spec=specs.CNS,
            )

            self.logger.info(
                f"📋 Texto capturado: {texto}"
            )

            if not texto:

                self.logger.warning(
                    "⚠️ No se pudo capturar texto "
                    "para validar CNS."
                )

                mensaje = (
                    "Baja Observada - "
                    "No se pudo capturar CNS - "
                    f"ID solicitud: "
                    f"{self.contexto.get('id_sharepoint', '')}"
                )

                self.contexto.update({
                    "cnsCancelado": False,
                    "mensaje_memo": mensaje,
                    "baja_realizada": "Baja Observada",
                    "mensaje_observacion_rpa": (
                        self._agregar_observacion(mensaje)
                    ),
                })

                return

            lineas = [
                line.strip()
                for line in texto.splitlines()
                if line.strip()
            ]

            self.logger.info(
                f"📋 Texto capturado: "
                f"{len(lineas)} líneas detectadas"
            )

            nro_cuenta = (
                str(
                    self.contexto.get(
                        "nro_linea",
                        ""
                    )
                )
                .strip()
            )

            id_sharepoint = self.contexto.get(
                "id_sharepoint",
                ""
            )

            valor_residual = (
                str(
                    self.contexto.get(
                        "valor_residual",
                        "0"
                    )
                )
                .strip()
                .replace(",", ".")
            )

            tipo_cns = (
                self.contexto.get(
                    "tipo_cns",
                    "CNS"
                )
                .strip()
                .upper()
            )

            self.logger.info(
                f"🔎 Datos para validación CNS | "
                f"tipo={tipo_cns} | "
                f"cuenta={nro_cuenta} | "
                f"saldo esperado={valor_residual}"
            )

            encontrado = False

            for linea in lineas:

                partes = linea.split()

                self.logger.info(
                    f"🔎 Analizando línea CNS: {partes}"
                )

                if len(partes) < 2:

                    self.logger.warning(
                        f"⚠️ Línea ignorada por cantidad "
                        f"insuficiente de columnas: {linea}"
                    )

                    continue

                tipo = partes[0].strip().upper()

                cuenta = (
                    partes[5].strip()
                    if len(partes) > 5
                    else ""
                )

                estado = partes[-1].strip().upper()

                saldo = ""

                for valor in reversed(partes[:-1]):

                    valor_limpio = (
                        valor.strip()
                        .replace(",", ".")
                    )

                    if self._es_numero(valor_limpio):

                        saldo = valor_limpio
                        break

                self.logger.info(
                    f"🔎 Evaluando CNS | "
                    f"tipo={tipo} | "
                    f"cuenta={cuenta} | "
                    f"saldo={saldo} | "
                    f"estado={estado}"
                )

                if tipo != tipo_cns:

                    self.logger.info(
                        f"⏭️ Tipo descartado: "
                        f"{tipo} != {tipo_cns}"
                    )

                    continue

                if cuenta != nro_cuenta:

                    self.logger.info(
                        f"⏭️ Cuenta descartada: "
                        f"{cuenta} != {nro_cuenta}"
                    )

                    continue

                encontrado = True

                match_saldo = (
                    saldo == valor_residual
                )

                match_estado = (
                    estado == "CANCELADO"
                )

                cns_cancelado = (
                    match_saldo and match_estado
                )

                self.logger.info(
                    f"🎯 CNS encontrado | "
                    f"cuenta_ok=True | "
                    f"saldo_ok={match_saldo} | "
                    f"estado_ok={match_estado} | "
                    f"cnsCancelado={cns_cancelado}"
                )

                self.contexto["cnsCancelado"] = (
                    cns_cancelado
                )

                if not cns_cancelado:

                    mensaje = (
                        "Baja Observada - "
                        "CNS no se encuentra cancelado - "
                        f"ID solicitud: {id_sharepoint}"
                    )

                    self.contexto.update({
                        "mensaje_memo": mensaje,
                        "baja_realizada": "Baja Observada",
                        "mensaje_observacion_rpa": (
                            self._agregar_observacion(mensaje)
                        ),
                    })

                else:

                    self.contexto.update({
                        "mensaje_memo": "",
                    })

                    self.logger.info(
                        "✅ CNS encontrado, saldo correcto "
                        "y estado CANCELADO."
                    )

                break

            if not encontrado:

                self.contexto["cnsCancelado"] = False

                mensaje = (
                    "Baja Observada - "
                    "No se encontró CNS - "
                    f"ID solicitud: {id_sharepoint}"
                )

                self.contexto.update({
                    "mensaje_memo": mensaje,
                    "baja_realizada": "Baja Observada",
                    "mensaje_observacion_rpa": (
                        self._agregar_observacion(mensaje)
                    ),
                })

                self.logger.warning(
                    f"⚠️ {mensaje}"
                )

            self.logger.info(
                "✅ Resultado CNS: "
                f"Cancelado = "
                f"{self.contexto.get('cnsCancelado', False)} "
                f"| Mensaje = "
                f"'{self.contexto.get('mensaje_memo', '')}' "
                f"| Observación = "
                f"'{self.contexto.get('mensaje_observacion_rpa', '')}'"
            )

        except Exception as e:

            self.logger.error(
                f"❌ Error al extraer situación de ventas: {e}",
                exc_info=True
            )

            self.contexto["cnsCancelado"] = False

            raise

    @staticmethod
    def _es_numero(valor):

        if not valor:
            return False

        try:
            float(valor)
            return True
        except (ValueError, TypeError):
            return False

    def _agregar_observacion(self, nueva_observacion):

        nueva_observacion = (
            str(nueva_observacion or "")
            .strip()
        )

        if not nueva_observacion:
            return self.contexto.get(
                "mensaje_observacion_rpa",
                ""
            )

        observacion_actual = (
            str(
                self.contexto.get(
                    "mensaje_observacion_rpa",
                    ""
                )
            )
            .strip()
        )

        if not observacion_actual:
            return nueva_observacion

        if nueva_observacion in observacion_actual:
            return observacion_actual

        return (
            f"{observacion_actual} | "
            f"{nueva_observacion}"
        )
import pyperclip
from core.action_base.action_base import ActionBase

class ValidationFormaPagoAction(ActionBase):
    def __init__(self, variables_base, contexto):
        super().__init__(variables_base, contexto, flow_name="validation_forma_pago", executor_type="desktop")
        self.executor._action_extraer_validar_forma_pago = self.extraer_validar_forma_pago

    def ejecutar(self):
        self.logger.info("🚀 Iniciando validation_forma_pago action...")
        self.hora_inicio()

        try:
            # 1. Extraer valor actual desde pantalla y guardar en el contexto
            self.executor.ejecutar_bloque("validation")

            # 2. Obtener el valor del contexto (no de variables_base)
            forma_actual = self.contexto.get("forma_pago_rpa", "").strip().upper()
            self.logger.info(f"🔍 Forma de pago detectada: '{forma_actual}'")

            if forma_actual == "CREDITO" or forma_actual == "":
                self.logger.info("✅ Forma de pago ya es '' o CREDITO. No se requiere cambio.")
                self.contexto["forma_pago_anterior_rpa"] = forma_actual
                self.contexto["forma_pago_posterior_rpa"] = forma_actual
                
                return True

            # 3. Si es diferente, ejecutar bloque de corrección (flow)
            self.logger.info("🔁 Forma de pago distinta de CREDITO. Ejecutando cambio...")
            self.executor.ejecutar_bloque("flow")

            self.contexto["forma_pago_anterior_rpa"] = forma_actual
            self.contexto["forma_pago_posterior_rpa"] = "CREDITO"
            return True

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

    def extraer_validar_forma_pago(self, paso):
        self.logger.info("🔍 Ejecutando acción personalizada: extraer_validar_forma_pago")
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
                transitorio=paso.get("transitorio", False)
            )

            self.app_tools.esperar(0.2)
            self.app_tools.presionar_tecla_real("up")
            self.app_tools.presionar_combinacion_real("ctrl", "c")
            self.app_tools.esperar(0.2)

            texto = pyperclip.paste().strip().upper()
            self.logger.info(f"📋 Texto original copiado:\n{texto[:300]}...")

            # ✅ Buscar número de cuenta desde el contexto (no de variables_base)
            nro_cuenta = str(
                self.contexto.get("nro_cuenta") or 
                self.contexto.get("nro_linea", "")
            ).strip().upper()

            if not nro_cuenta:
                self.logger.warning("⚠️ Número de cuenta no encontrado en el contexto.")
                return texto

            # 🔎 Buscar línea que contenga CET y el número de cuenta
            lineas = texto.splitlines()
            fila_objetivo = -1
            linea_objetiva = ""

            for i, linea in enumerate(lineas):
                if "CET" in linea and nro_cuenta in linea:
                    fila_objetivo = i
                    linea_objetiva = linea
                    break

            if fila_objetivo >= 0:
                self.logger.info(f"✅ Coincidencia con 'CET' y número de cuenta encontrada en línea {fila_objetivo + 1}")
                self.app_tools.presionar_tecla_real("down", repeticiones=fila_objetivo + 1)

                # 🧠 Guardar en el contexto
                self.contexto["fila_contratos_encontrada"] = fila_objetivo + 1
                self.contexto["linea_contratos"] = linea_objetiva
            else:
                self.logger.warning("❌ No se encontró ninguna línea que contenga tanto 'CET' como el número de cuenta.")

            return texto

        except Exception as e:
            self.logger.error(f"❌ Error en extraer_validar_forma_pago: {e}", exc_info=True)
            return ""

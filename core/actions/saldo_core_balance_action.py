import pyperclip
from core.action_base.action_base import ActionBase

class SaldoCoreBalanceAction(ActionBase):
    def __init__(self, variables_base, contexto):
        super().__init__(variables_base, contexto, flow_name="saldo_core_balance")
        self.executor._action_extraer_y_validar_billetera = self.extraer_y_validar_billetera

    def ejecutar(self):
        self.logger.info("🚀 Iniciando saldo_core_balance action...")
        self.hora_inicio()

        try:
            self.executor.ejecutar_bloque("validation")

            validacion_exitosa = self.contexto.get("billetera_successful", False)

            if validacion_exitosa:
                self.logger.info("✅ Validación exitosa. Ejecutando flujo principal...")
                self.executor.ejecutar_bloque("flow")
                return True
            else:
                self.logger.warning("⚠️ Validación fallida. Ejecutando bloque de reinicio...")
                self.contexto["mensaje_memo"] = "DSP *LINEA* FEATURE (DSPCDOM)"
                self.executor.ejecutar_bloque("reboot_validation")
                return False

        except Exception as e:
            self.manejar_excepcion(e)
            raise  

        finally:
            self.hora_fin()

    def extraer_y_validar_billetera(self, paso):
        
        self.logger.info("🔍 Ejecutando acción personalizada: extraer_y_validar_billetera")
        campo_destino = paso.get("campo_destino", "billetera_filtrada")
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
            self.app_tools.esperar(0.2)
            self.app_tools.presionar_combinacion_real(
                "ctrl",
                "shift",
                "PgDn",
                repeticiones=5,
            )
            texto = self.basic_tools.copiar_texto_actual(
                seleccionar_todo=False,
                limpiar=True,
                mayusculas=True,
                usar_real=True,
                timeout=15.0,
            )

            if not texto:
                self.contexto[campo_destino] = None
                self.logger.warning(
                    f"⚠️ No se pudo extraer texto de billetera, se guarda NULL en '{campo_destino}'"
                )
                return None

            self.logger.info("🔍 Billetera extraida: " + texto[:500])

            texto = texto.replace("= ", ";").replace(", EXPIRATION:", ";")

            billeteras_excluidas = {
                "MB_PLAN",
                "DATA_PLAN",
                "MIN_PLAN",
                "SMS_PLAN",
                "FUP_ILIMITADO",
                "FREE_ILIMITADO",
                "FUP_TETHERING",
                "FREE_TETHERING",
                "FREE_ TETHERING",
                "FUP_ TETHERING",
            }

            resultado = []

            for linea in texto.splitlines():
                partes = linea.strip().split(";")

                if len(partes) == 3:
                    billetera, valor_str, fecha = partes
                    billetera = billetera.strip().upper()

                    try:
                        valor = float(valor_str.replace(",", "."))
                    except ValueError:
                        continue

                    if valor > 0 and billetera not in billeteras_excluidas:
                        resultado.append(f"{billetera};{valor};{fecha}")

            if resultado:
                resultado_filtrado = "|".join(resultado)
                self.contexto[campo_destino] = resultado_filtrado

                self.logger.info(
                    f"📥 Guardado en contexto '{campo_destino}': '{resultado_filtrado}'"
                )

                return resultado_filtrado

            self.contexto[campo_destino] = None
            self.logger.info(
                f"⚠️ No se encontraron billeteras válidas, se guarda NULL en '{campo_destino}'"
            )
            return None

        except Exception as e:
            error_msg = f"ERROR_EXTRAER_BILLETERA: {str(e)}"
            self.contexto[campo_destino] = error_msg
            self.logger.error(f"❌ {error_msg}", exc_info=True)
            return error_msg
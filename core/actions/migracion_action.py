import logging
from shared.tools.time_tools import TimeTools
from shared.tools.exceptions import RPAExceptions
from infrastructure.database.adapters.estado_migracion_adapter import EstadoSQLAdapter
from infrastructure.database.adapters.migraciones_adapter import MigracionesSQLAdapter

from core.actions.login_action import LoginAction
from core.actions.buscar_linea_action import BuscarLineaAction
from core.actions.validation_plan_action import ValidationPlanAction
from core.actions.validation_consumo_action import ValidationConsumoAction
from core.actions.validation_estado_cuenta_action import ValidationEstadoCuentaAction
from core.actions.validation_forma_pago_action import ValidationFormaPagoAction
from core.actions.captura_datos_action import CapturaDatosAction
from core.actions.validation_estado_controlado_action import ValidationEstadoControladoAction
from core.actions.paso_post_a_pre_action import PasoPostAPreAction

from core.actions.validation_idctl_actual_action import ValidationIdctlActualAction
from core.actions.verificar_servicio_ldi_900_action import VerificarServicioLdi_900Action
from core.actions.crear_servicio_fflte_action import CrearServicioFflteAction
from core.actions.programar_cambio_action import ProgramarCambioAction

from core.actions.saldo_core_balance_action import SaldoCoreBalanceAction
from core.actions.eliminacion_servicios_action import EliminacionServiciosAction
from core.actions.eliminacion_creacion_action import EliminacionCreacionAction

from core.actions.derivacion_sms_action import DerivacionSmsAction
from core.actions.carga_reclamos_action import CargaReclamosAction
from core.actions.logout_action import LogoutAction


class MigracionActions:
    def __init__(self, variables_base: dict, contexto: dict):
        self.variables_base = variables_base
        self.contexto = contexto or {}
        self.estado_adapter = EstadoSQLAdapter()
        self.migracion_adapter = MigracionesSQLAdapter()
        self.logger = logging.getLogger(self.__class__.__name__)

    def ejecutar_inicio(self) -> bool:
        self.logger.info("🔐 Ejecutando login inicial...")
        try:
            return LoginAction(self.variables_base, self.contexto).ejecutar()
        except Exception as e:
            self.logger.error(f"❌ Error en ejecutar_inicio: {e}", exc_info=True)
            return False

    def ejecutar_final(self) -> bool:
        self.logger.info("🔒 Ejecutando logout final...")
        try:
            return LogoutAction(self.variables_base, self.contexto).ejecutar()
        except Exception as e:
            self.logger.error(f"❌ Error en ejecutar_final: {e}", exc_info=True)
            return False

    def ejecutar(self) -> bool:
        try:
            TimeTools.marcar_hora_inicio(self.contexto, self.__class__.__name__, self.logger)
            self._buscar_linea_entrar()
            if self.contexto.get("existe_error_qvantel", False):
                self.logger.warning("⚠️ Error QVANTEL detectado — cierre inmediato.")
                self._cerrar_con_reclamo_inicial()
                return True


            if not self._validar_plan_inicial():
                validacion_exitosa = self.contexto.get("validacion_exitosa", False)
                plan_valido = self.contexto.get("plan_valido", False)

                if not validacion_exitosa or not plan_valido:
                    self.logger.warning("🚫 Validación de plan inicial fallida → cierre con reclamo.")
                    return self._cerrar_con_reclamo()

            if not self._validar_consumo():
                deuda = self.contexto.get("facturas_pendientes_rpa", 0)
                if deuda > 0:
                    return self._cerrar_con_reclamo()

            if not self._validar_estado_cuenta():
                estado = self.contexto.get("estado_extraido_rpa", "").upper()
                error_cambio_estado = self.contexto.get("error_de_estado", False)

                if estado in ("PO", "PP") or error_cambio_estado:
                    self.logger.warning("⚠️ Estado inválido o error detectado, cerrando con reclamo.")
                    return self._cerrar_con_reclamo()


            if not self._validar_forma_pago():
                return self._cerrar_con_reclamo()

            if not self._captura_de_datos():
                return self._cerrar_con_reclamo()

            if not self._validar_estado_controlado():
                cns_cancelado = self.contexto.get("cnsCancelado", False)
                if not cns_cancelado:
                    return self._cerrar_con_reclamo()

            tipo = self.contexto.get("tipo_baja")
            if tipo == "Migración de Post Pago a Pre Pago":
                self.logger.info("🚀 Iniciando Migración de Post Pago a Pre Pago")
                if not self._migracion_post_pre3():
                    return True

            elif tipo == "Cambio de Post Pago a Pre Pago R":
                self.logger.info("🚀 Iniciando Migración de Post Pago a Pre Pago")
                if not self._migracion_post_preR():
                    return True

            if not self._validar_plan_final():
                validacion_exitosa = self.contexto.get("validacion_exitosa", False)
                plan_valido = self.contexto.get("plan_valido", False)
                if not validacion_exitosa and plan_valido:
                    return True  
                elif not validacion_exitosa and not plan_valido:
                    return self._cerrar_con_reclamo()
                else:
                    self.logger.info("✅ Validación final exitosa, continuando flujo.")

            return self._finalizar_ok()


        except RPAExceptions.ErrorBaseException:
            raise
        except Exception as e:
            self.logger.error(f"❌ Error no controlado en MigracionActions: {e}", exc_info=True)
            raise RPAExceptions.FlujoException(
                f"{e.__class__.__name__}: {e}", contexto=self.contexto
            )

    def _buscar_linea_entrar(self) -> bool:
        return BuscarLineaAction(self.variables_base, self.contexto).ejecutar(modo="entrar")

    def _captura_de_datos(self) -> bool:
        return CapturaDatosAction(self.variables_base, self.contexto).ejecutar()

    def _validar_plan_inicial(self) -> bool:
        return ValidationPlanAction(self.variables_base, self.contexto).ejecutar(modo="extraer_inicial")

    def _validar_plan_final(self) -> bool:
        return ValidationPlanAction(self.variables_base, self.contexto).ejecutar(modo="extraer_final")

    def _validar_consumo(self) -> bool:
        return ValidationConsumoAction(self.variables_base, self.contexto).ejecutar()

    def _validar_estado_cuenta(self) -> bool:
        return ValidationEstadoCuentaAction(self.variables_base, self.contexto).ejecutar()

    def _validar_estado_controlado(self) -> bool:
        return ValidationEstadoControladoAction(self.variables_base, self.contexto).ejecutar()

    def _validar_forma_pago(self) -> bool:
        return ValidationFormaPagoAction(self.variables_base, self.contexto).ejecutar()

    def _derivacion_sms(self) -> bool:
        return DerivacionSmsAction(self.variables_base, self.contexto).ejecutar()

    def _migracion_post_pre3(self) -> bool:
        SaldoCoreBalanceAction(self.variables_base, self.contexto).ejecutar()
        self.contexto["migracion_ejecutada"] = True
        PasoPostAPreAction(self.variables_base, self.contexto).ejecutar()
        if self.contexto.get("linea_error_migracion", False):
            self._cerrar_con_reclamo()
            return False
        EliminacionServiciosAction(self.variables_base, self.contexto).ejecutar()
        EliminacionCreacionAction(self.variables_base, self.contexto).ejecutar()
        return True


    def _migracion_post_preR(self) -> bool:
        ValidationIdctlActualAction(self.variables_base, self.contexto).ejecutar()
        VerificarServicioLdi_900Action(self.variables_base, self.contexto).ejecutar()
        self.contexto["migracion_ejecutada"] = True
        CrearServicioFflteAction(self.variables_base, self.contexto).ejecutar()
        ProgramarCambioAction(self.variables_base, self.contexto).ejecutar()
        return True

    def _cerrar_con_reclamo(self) -> bool:
        CargaReclamosAction(self.variables_base, self.contexto).ejecutar()
        TimeTools.marcar_hora_fin(self.contexto, self.__class__.__name__, self.logger)
        self.estado_adapter.actualizar_estado_migracion(self.contexto)
        self.migracion_adapter.registrar_detalle(self.contexto)

        return self._buscar_linea_salir()

    def _cerrar_con_reclamo_inicial(self) -> bool:
        TimeTools.marcar_hora_fin(self.contexto, self.__class__.__name__, self.logger)
        self.estado_adapter.actualizar_estado_migracion(self.contexto)
        self.migracion_adapter.registrar_detalle(self.contexto)
        return True

    def _buscar_linea_salir(self) -> bool:
        try:
            BuscarLineaAction(self.variables_base, self.contexto).ejecutar(modo="salir")
        except Exception as e:
            self.logger.error(f"⚠️ Falla técnica al salir de la línea (registro ya persistido): {e}")
            self._anexar_observacion(f"Falla técnica al salir de pantalla: {e}")
        return True

    def _finalizar_ok(self) -> bool:
        try:
            CargaReclamosAction(self.variables_base, self.contexto).ejecutar()
        except Exception as e:
            self.logger.error(f"⚠️ Falla técnica en carga de reclamo post-migración: {e}", exc_info=True)
            self._anexar_observacion(f"Migración OK; falló carga de reclamo: {e}")

        try:
            self._derivacion_sms()
        except Exception as e:
            self.logger.error(f"⚠️ Falla técnica en derivación SMS post-migración: {e}", exc_info=True)
            self.contexto["notificacion_baja_rpa"] = False
            self._anexar_observacion(f"Migración OK; falló derivación SMS: {e}")

        TimeTools.marcar_hora_fin(self.contexto, self.__class__.__name__, self.logger)
        self.estado_adapter.actualizar_estado_migracion(self.contexto)
        self.migracion_adapter.registrar_detalle(self.contexto)
        return self._buscar_linea_salir()

    def _anexar_observacion(self, mensaje: str):
        previa = (self.contexto.get("mensaje_observacion_rpa") or "").strip()
        self.contexto["mensaje_observacion_rpa"] = f"{previa} | {mensaje}" if previa else mensaje
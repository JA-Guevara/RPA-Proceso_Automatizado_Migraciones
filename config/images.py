import os
from config.config import IMAGES_DIR

def ruta(*args):
    return os.path.join(IMAGES_DIR, *args)

class ImagePaths:
    LOGIN = {
        "user_field": ruta("login", "user_field.png"),
        "password_field": ruta("login", "password_field.png"),
        "log_field": ruta("login", "log_field.png"),
        "ok_button": ruta("login", "ok_button.png"),
        
        "BCCS_icons": ruta("login", "BCCS_icons.png"),
        "user_BCCS_field": ruta("login", "user_BCCS_field.png"),
        "password_BCCS_field": ruta("login", "password_BCCS_field.png"),
        "ok_BCCS_button": ruta("login", "ok_BCCS_button.png"),
        
        "telefonia_icons": ruta("login", "telefonia_icons.png"),
        "modulos_BCCS": ruta("login", "modulos_BCCS.png"),
    
        "busqueda_button": ruta("login", "busqueda_button.png")

    }

    BUSCAR_LINEA = {
        "inicial_busqueda": ruta("buscar_linea", "inicial_busqueda.png"),
        "busqueda_button": ruta("buscar_linea", "busqueda_button.png"),
        "nro_linea_field": ruta("buscar_linea", "nro_cuenta_field.png"),
        "procesar_button": ruta("buscar_linea", "procesar_button.png"),
        "salir_BCCS_button": ruta("buscar_linea", "salir_BCCS_button.png")
    }

    VALIDACION_PLAN = {
        "tipo_plan_field": ruta("validations", "validation_plan", "tipo_plan_field.png")
    }

    VALIDACION_CONSUMO = {
        "consumo_button": ruta("validations", "validation_consumo", "consumo_button.png"),
        "estado_contable": ruta("validations", "validation_consumo", "estado_contable.png"),

    }

    VALIDACION_ESTADO_CUENTA = {
        "estado_cuenta_field": ruta("validations", "validation_estado_cuenta", "estado_cuenta_field.png"),
        "cambio_cuenta_icon": ruta("validations", "validation_estado_cuenta", "cambio_cuenta_icon.png"),
        "nuevo_estado_field": ruta("validations", "validation_estado_cuenta", "nuevo_estado_field.png"),
        "estado_posterior_field": ruta("validations", "validation_estado_cuenta", "estado_posterior_field.png"),
        "posicion_button": ruta("validations", "validation_estado_cuenta", "posicion_button.png"),
        "selecionar_button": ruta("validations", "validation_estado_cuenta", "selecionar_button.png"),
        "procesar_button": ruta("validations", "validation_estado_cuenta", "procesar_button.png"),

        "modificacion_button": ruta("validations", "validation_estado_cuenta", "modificacion_button.png"),
        "cuenta_button": ruta("validations", "validation_estado_cuenta", "cuenta_button.png"),
        "pre-eliminacion_button": ruta("validations", "validation_estado_cuenta", "pre-eliminacion_button.png"),
        "levantar_pre-eliminado_button": ruta("validations", "validation_estado_cuenta", "levantar_pre-eliminado_button.png"),
        "procesar_button2": ruta("validations", "validation_estado_cuenta", "procesar_button.png"),
    }

    VALIDACION_FORMA_PAGO = {
        "forma_pago_field": ruta("validations", "validation_forma_pago", "forma_pago_field.png"),
        "modificaciones_button": ruta("validations", "validation_forma_pago", "modificaciones_button.png"),
        "contrato_button": ruta("validations", "validation_forma_pago", "contrato_button.png"),
        "cambio_forma_pago_button": ruta("validations", "validation_forma_pago", "cambio_forma_pago_button.png"),

        "contrato_column": ruta("validations", "validation_forma_pago", "contrato_column.png"),
        "procesar_button": ruta("validations", "validation_forma_pago", "procesar_button.png"),
        "forma_pago_option": ruta("validations", "validation_forma_pago", "forma_pago_option.png"),
        "credito_option": ruta("validations", "validation_forma_pago", "credito_option.png"),
        "tipo_documento_field": ruta("validations", "validation_forma_pago", "tipo_documento_field.png"),
        "yes_buton": ruta("validations", "validation_forma_pago", "yes_buton.png"),
        "ok_button": ruta("validations", "validation_forma_pago", "ok_button.png"),
        "cancelar_button": ruta("validations", "validation_forma_pago", "cancelar_button.png")
    }

    VALIDACION_ESTADO_CONTROLADO = {
        "situacion_field": ruta("validations", "validation_estado_controlado", "situacion_field.png"),
        "ventas_button": ruta("validations", "validation_estado_controlado", "ventas_button.png"),
        "fecha_comercial_button": ruta("validations", "validation_estado_controlado", "fecha_comercial_button.png"),
        
        "cambio_equipo_icon": ruta("validations", "validation_estado_controlado", "cambio_equipo_icon.png"),
        "sin_Cpte_button": ruta("validations", "validation_estado_controlado", "sin_Cpte_button.png"),

        "propios_option": ruta("validations", "validation_estado_controlado", "propios_option.png"),
        "producto_field_in": ruta("validations", "validation_estado_controlado", "producto_field_in.png"),
        "ident_induvidual_field_in": ruta("validations", "validation_estado_controlado", "ident_induvidual_field_in.png"),
        "subtipo_cuenta_field_in": ruta("validations", "validation_estado_controlado", "subtipo_cuenta_field_in.png"),
        "procesar_button": ruta("validations", "validation_estado_controlado", "procesar_button.png")
    }

    SALDO_CORE_BALANCE = {
        "informacion_swich_icon": ruta("saldo_core_balance", "informacion_swich_icon.png"),
        "tipo_cosulta_field": ruta("saldo_core_balance", "tipo_cosulta_field.png"),
        "casilla_prepago_option": ruta("saldo_core_balance", "casilla_prepago_option.png"),
        "aceptar_button": ruta("saldo_core_balance", "aceptar_button.png"),
        "estado_field": ruta("saldo_core_balance", "estado_field.png"),
        "successfull_message": ruta("saldo_core_balance", "successfull_message.png"),
        
        "refrescar_datos_icon": ruta("saldo_core_balance", "refrescar_datos_icon.png"),
        "respuesta_datos_icon": ruta("saldo_core_balance", "respuesta_datos_icon.png"),
        "inicio_billetera_text": ruta("saldo_core_balance", "inicio_billetera_text.png"),
        "cancelar_button": ruta("saldo_core_balance", "cancelar_button.png"),
        "salir_button": ruta("saldo_core_balance", "salir_button.png")
    }

    CARGA_RECLAMOS = {
        "reclamos_icon": ruta("carga_reclamos", "reclamos_icon.png"),
        "motivo_field": ruta("carga_reclamos", "motivo_field.png"),
        "cargar_memo_icon": ruta("carga_reclamos", "cargar_memo_icon.png"),
        "cargar_memo_field": ruta("carga_reclamos", "cargar_memo_field.png"),
        "aceptar_button": ruta("carga_reclamos", "aceptar_button.png"),
        "crear_button": ruta("carga_reclamos", "crear_button.png")

    }
    
    CAPTURA_DATOS = {
        "fecha_habil_field": ruta("captura_datos", "fecha_habil_field.png"),
        "cuenta_button": ruta("captura_datos", "cuenta_button.png"),
        "ident_individual_field": ruta("captura_datos", "ident_individual_field.png"),
        "tipo_cuenta_field": ruta("captura_datos", "tipo_cuenta_field.png"),
        "producto_field": ruta("captura_datos", "producto_field.png"),
        "salir_button": ruta("captura_datos", "salir_button.png")
    }
    
    PASO_POST_A_PRE = {
        "procesos_button": ruta("paso_post_a_pre", "procesos_button.png"),
        "paso_cuenta_option": ruta("paso_post_a_pre", "paso_cuenta_option.png"),
        
        "plan_comercial_field": ruta("paso_post_a_pre", "plan_comercial_field.png"),
        "plan_consumo_field": ruta("paso_post_a_pre", "plan_consumo_field.png"),
        "codigo_motivo_field": ruta("paso_post_a_pre", "codigo_motivo_field.png"),
        "descripcion_column": ruta("paso_post_a_pre", "descripcion_column.png"),
        "migracion_option": ruta("paso_post_a_pre", "migracion_option.png"),
        "seleccionar_button": ruta("paso_post_a_pre", "seleccionar_button.png"),
        "migracion_postpago_option": ruta("paso_post_a_pre", "migracion_postpago_option.png"),
        "procesar_button": ruta("paso_post_a_pre", "procesar_button.png"),

    }
    
    LIBERACION_CUENTA = {
        "image_error": ruta("liberacion_cuenta", "image_error.png"),
        
        "procesos_button": ruta("liberacion_cuenta", "procesos_button.png"),
        "liberar_cuenta_option": ruta("liberacion_cuenta", "liberar_cuenta_option.png"),
        "aceptar_button": ruta("liberacion_cuenta", "aceptar_button.png"),
        "ok_button": ruta("liberacion_cuenta", "ok_button.png"),
    }
    
    ELIMINACION_SERVICIOS = {
        "servicios_button": ruta("eliminacion_servicios", "servicios_button.png"),
        "servicio_column": ruta("eliminacion_servicios", "servicio_column.png"),
        
        "restringir_nav_option_a": ruta("eliminacion_servicios", "restringir_nav_option_a.png"),
        "restringir_nav_option_b": ruta("eliminacion_servicios", "restringir_nav_option_b.png"),
        "restringir_nav_option_a2": ruta("eliminacion_servicios", "restringir_nav_option_a2.png"),
        "restringir_nav_option_b2": ruta("eliminacion_servicios", "restringir_nav_option_b2.png"),
        
        "edicion_servicios_icon": ruta("eliminacion_servicios", "edicion_servicios_icon.png"),
        "descripcion_servicio_column": ruta("eliminacion_servicios", "descripcion_servicio_column.png"),
        "eliminar_servicio_icon": ruta("eliminacion_servicios", "eliminar_servicio_icon.png"),
        "suprimir_button": ruta("eliminacion_servicios", "suprimir_button.png"),
        "yes_button": ruta("eliminacion_servicios", "yes_button.png"),
        "procesar_button": ruta("eliminacion_servicios", "procesar_button.png"),
        "salir_button": ruta("eliminacion_servicios", "salir_button.png")
    }
    
    VALIDATION_IDCTL_ACTUAL = {
        "idctl_actual_field": ruta("validations", "validation_idctl_actual", "idctl_actual_field.png"),
        "plan_consumo_button": ruta("validations", "validation_idctl_actual", "plan_consumo_button.png"),
        "cambio_plan_button": ruta("validations", "validation_idctl_actual", "cambio_plan_button.png"),
        "salir_button": ruta("validations", "validation_idctl_actual", "salir_button.png"),
        
        "cambio_plan_icon": ruta("validations", "validation_idctl_actual", "cambio_plan_icon.png"),
        "eliminar_plan_button": ruta("validations", "validation_idctl_actual", "eliminar_plan_button.png")
    }
    
    VERIFICAR_CREAR_SERVICIO = {
        "servicios_button": ruta("varificar_crear_servicios", "servicios_button.png"),
        "servicio_column": ruta("varificar_crear_servicios", "servicio_column.png"),
        "LDL_LDN_900_option_a": ruta("varificar_crear_servicios", "LDL_LDN_900_option_a.png"),
        "LDL_LDN_900_option_b": ruta("varificar_crear_servicios", "LDL_LDN_900_option_b.png"),
        
        "LDL_LDN_900_option_a2": ruta("varificar_crear_servicios", "LDL_LDN_900_option_a2.png"),
        "LDL_LDN_900_option_b2": ruta("varificar_crear_servicios", "LDL_LDN_900_option_b2.png"),
        
        "edicion_servicios_icon": ruta("varificar_crear_servicios", "edicion_servicios_icon.png"),
        
        "eliminar_servicios_icon": ruta("varificar_crear_servicios", "eliminar_servicios_icon.png"),
        "suprimir_button": ruta("varificar_crear_servicios", "suprimir_button.png"),
        "yes_button": ruta("varificar_crear_servicios", "yes_button.png"),

        
        "descripcion_column": ruta("varificar_crear_servicios", "descripcion_column.png"),
        "alcance_llamada_option_a": ruta("varificar_crear_servicios", "alcance_llamada_option_a.png"),
        "alcance_llamada_option_b": ruta("varificar_crear_servicios", "alcance_llamada_option_b.png"),
        
        "cod_column": ruta("varificar_crear_servicios", "cod_column.png"),
        "factura_fija_option_a": ruta("varificar_crear_servicios", "factura_fija_option_a.png"),
        "factura_fija_option_b": ruta("varificar_crear_servicios", "factura_fija_option_b.png"),
        "procesar_button": ruta("varificar_crear_servicios", "procesar_button.png"),
        "salir_button": ruta("varificar_crear_servicios", "salir_button.png"),
        
        "FFLTE_option_a": ruta("varificar_crear_servicios", "FFLTE_option_a.png"),
        "FFLTE_option_b": ruta("varificar_crear_servicios", "FFLTE_option_b.png"),

    }
    
    PROGRAMAR_CAMBIO = {
        "modificaciones_button": ruta("programar_cambio", "modificaciones_button.png"),
        "cuenta_option": ruta("programar_cambio", "cuenta_option.png"),
        "plan_comercial_option": ruta("programar_cambio", "plan_comercial_option.png"),
        "plan_comercial_field": ruta("programar_cambio", "plan_comercial_field.png"),
        "procesar_button": ruta("programar_cambio", "procesar_button.png"),
        "plan_consumo_field": ruta("programar_cambio", "plan_consumo_field.png"),
        "tipos_plan_lista": ruta("programar_cambio", "tipos_plan_lista.png"),
        "inmediato_option": ruta("programar_cambio", "inmediato_option.png"),
        "si_button": ruta("programar_cambio", "si_button.png"),
    }

    ELIMINACION_CREACION = {
        "procesos_manuales_icon": ruta("eliminacion_creacion", "procesos_manuales_icon.png"),
        "eliminacion_creacion_option": ruta("eliminacion_creacion", "eliminacion_creacion_option.png"),
        "procesar_button": ruta("eliminacion_creacion", "procesar_button.png"),
        "ok_button": ruta("eliminacion_creacion", "ok_button.png"),
    }
    
    LOGOUT = {
        "salir_BCCS_button": ruta("logout", "salir_BCCS_button.png"),
        "salir_menu_button": ruta("logout", "salir_menu_button.png")
    }

    @classmethod
    def get_all(cls):
        return {
            "login": cls.LOGIN,
            "logout" : cls.LOGOUT,
            "liberacion_cuenta" : cls.LIBERACION_CUENTA,
            "buscar_linea" : cls.BUSCAR_LINEA,
            "validacion_plan" : cls.VALIDACION_PLAN,
            "validacion_consumo" : cls.VALIDACION_CONSUMO,
            "validacion_estado_cuenta" : cls.VALIDACION_ESTADO_CUENTA,
            "validacion_forma_pago" : cls.VALIDACION_FORMA_PAGO,
            "validacion_estado_controlado" : cls.VALIDACION_ESTADO_CONTROLADO,
            "saldo_core_balance" : cls.SALDO_CORE_BALANCE,
            "carga_reclamos" : cls.CARGA_RECLAMOS,
            "captura_datos" : cls.CAPTURA_DATOS,
            "paso_post_a_pre" : cls.PASO_POST_A_PRE,
            "validacion_idctl_actual": cls.VALIDATION_IDCTL_ACTUAL,
            "varificar_crear_servicios": cls.VERIFICAR_CREAR_SERVICIO,
            "eliminacion_creacion" : cls.ELIMINACION_CREACION,
            "eliminacion_servicios" : cls.ELIMINACION_SERVICIOS,
            "programar_cambio" : cls.PROGRAMAR_CAMBIO
            
        }

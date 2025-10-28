class WebSelectors:
    LOGIN = {
        "username_input": "#loginForm\\:username",
        "password_input": "#loginForm\\:password",
        "login_button": "#loginForm\\:submit"
    }

    DERIVACION = {
        "derivaciones_menu": "#j_id25\\:j_id45",
        "nro_cuenta_field": "#frmEnviarSMS\\:nrocuentaField\\:nrocuenta",
        "tipo_plantilla_menu":"#frmEnviarSMS\\:tipoIdField\\:tipoID",
        "baja_post_pago_option": "#frmEnviarSMS\\:listPlantillasID > option:nth-child(6)",
        "button_agregar": "#frmEnviarSMS\\:j_id184",
        "button_enviar": "#frmEnviarSMS\\:j_id195"
    }

    LOGOUT = {
        "button_logout": "#j_id25\\:j_id26 > tbody > tr > td:nth-child(8)"
    }

    @classmethod
    def get_all(cls):
        return {
            "login": cls.LOGIN,
            "derivacion": cls.DERIVACION,
            "logout": cls.LOGOUT
        }

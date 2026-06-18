from dataclasses import dataclass


@dataclass(frozen=True)
class Selector:
    locator: str

    def __str__(self) -> str:
        return self.locator


class WebSelectors:
    class SmsBajas:
        USERNAME = Selector("#loginForm\\:username")
        PASSWORD = Selector("#loginForm\\:password")
        LOGIN_BUTTON = Selector("#loginForm\\:submit")

        DERIVACIONES_MENU = Selector("#j_id25\\:j_id45")
        OPCION_DERIVAR_CONSULTA = Selector("a[href='/derivacion/Form/derivarSMSv2.seam']")
        NRO_CUENTA = Selector("#frmEnviarSMS\\:nrocuentaField\\:nrocuenta")
        TIPO_PLANTILLA_MENU = Selector("#frmEnviarSMS\\:tipoIdField\\:tipoID")
        BAJA_POST_PAGO_OPTION = Selector("#frmEnviarSMS\\:listPlantillasID > option:nth-child(6)")
        PLANTILLA_SELECT = Selector("#frmEnviarSMS\\:listPlantillasID")
        PLANTILLA_CONFIRMACION_BAJA = "945"
        BTN_AGREGAR = Selector("#frmEnviarSMS\\:j_id184")
        BTN_ENVIAR = Selector("#frmEnviarSMS\\:j_id195")

        BTN_LOGOUT = Selector("#j_id25\\:j_id26 > tbody > tr > td:nth-child(8)")

    class Conexion:
        
        USERNAME = Selector("input[name='username']")
        PASSWORD = Selector("input[name='password']")
        LOGIN_BUTTON = Selector("input.login[type='submit'][value='Iniciar Sesión']")
        CONTINUAR_BUTTON = Selector("button.button:has-text('Continuar')")
        DESKTOP_READY = Selector("")
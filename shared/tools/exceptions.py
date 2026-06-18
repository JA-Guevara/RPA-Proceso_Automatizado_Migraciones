class RPAExceptions:

    class ErrorBaseException(Exception):
        tipo = "generico"
        env_key = "MAIL_DEFAULT"

        def __init__(self, mensaje: str, contexto: dict | None = None):
            super().__init__(mensaje)
            self.mensaje = mensaje        
            self.contexto = contexto or {}
            self.tipo_error = getattr(self, "tipo", "generico") 

        def __str__(self):
            return self.mensaje

    class InterfazException(ErrorBaseException):
        tipo = "interfaz"
        env_key = "MAIL_INTERFAZ"
    class DatosException(ErrorBaseException):
        tipo = "datos"
        env_key = "MAIL_DATOS"
    class LoginException(ErrorBaseException):
        tipo = "login"
        env_key = "MAIL_LOGIN"
    class FlujoException(ErrorBaseException):
        tipo = "flujo"
        env_key = "MAIL_FLUJO"
    class ComunicacionException(ErrorBaseException):
        tipo = "comunicacion"
        env_key = "MAIL_COMUNICACION"


    class ClickException(InterfazException):
        tipo = "click"
    class ImagenNoEncontradaException(InterfazException):
        tipo = "imagen_no_encontrada"
    class RegionNoEncontradaException(InterfazException):
        tipo = "region_no_encontrada"
    class EntradaTextoException(InterfazException):
        tipo = "entrada_texto"


    class SesionInvalidaException(LoginException):
        tipo = "sesion_invalida"
    class UsuarioBloqueadoException(LoginException):
        tipo = "usuario_bloqueado"
    class ContrasenaIncorrectaException(LoginException):
        tipo = "contrasena_incorrecta"


    class ConexionFallidaException(ComunicacionException):
        tipo = "conexion_fallida"
    class ServicioNoDisponibleException(ComunicacionException):
        tipo = "servicio_no_disponible"
    class TiempoEsperaExcedidoException(ComunicacionException):
        tipo = "timeout"



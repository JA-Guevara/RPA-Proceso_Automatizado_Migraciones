import logging
from shared.tools.click_tools import ClickTools
from shared.tools.extraction_tools import ExtractionTools
from shared.tools.service_tools import ServiceTools
from shared.tools.app_tools import AppTools
from shared.tools.basic_tools import BasicTools
from shared.tools.exceptions import RPAExceptions

logger = logging.getLogger(__name__)

class DesktopExecutor:
    def __init__(
        self,
        flow: dict,
        image_map: dict = None,
        variables_base: dict = None,
        contexto: dict = None,
        delay_default: float = 0.5
    ):
        self.flow_data = flow
        self.image_map = image_map or {}  
        self.variables_base = variables_base or {}  
        self.contexto = contexto if contexto is not None else {}
        self.delay_default = delay_default
        self.variables = {**self.variables_base, **self.contexto}

        self.clicker = ClickTools()
        self.extractor = ExtractionTools()
        self.app_tools = AppTools()
        self.basic_tools = BasicTools()
        self.service_tools = ServiceTools(executor=self, contexto=self.contexto)

        # 🔒 Nunca loguear credenciales en claro
        safe_vars = {
            k: ("****" if any(s in k.lower() for s in ("pass", "pwd", "secret", "token")) else v)
            for k, v in self.variables_base.items()
        }
        logger.info(f"📙️ Variables base: {safe_vars}")
        logger.info(f"📦 Contexto inicial: {self.contexto}")

    # ------------------- Ejecutor -------------------

    def ejecutar_bloque(self, bloque: str):
        pasos = self.flow_data.get(bloque, [])

        if not isinstance(pasos, list):
            mensaje = f"El bloque '{bloque}' no contiene una lista de pasos válida."
            logger.error(f"❌ {mensaje}")
            raise RPAExceptions.FlujoException(mensaje)

        logger.info(f"🚀 Ejecutando bloque: {bloque} ({len(pasos)} pasos)")

        for indice, paso_original in enumerate(pasos, start=1):
            action = paso_original.get("action") or paso_original.get("tipo") or "SIN_ACTION"

            try:
                paso = self._reemplazar_variables(
                    paso=paso_original,
                    bloque=bloque,
                    indice=indice,
                    total=len(pasos),
                    action=action,
                )

                handler = getattr(self, f"_action_{action}", None)

                if not handler:
                    mensaje = (
                        f"Acción desconocida en flow. "
                        f"Bloque='{bloque}', paso={indice}/{len(pasos)}, action='{action}'."
                    )
                    logger.warning(f"⚠️ {mensaje}")
                    raise RPAExceptions.FlujoException(mensaje)

                logger.info(f"▶️ Ejecutando paso {indice}/{len(pasos)} | bloque={bloque} | action={action}")
                handler(paso)

            except RPAExceptions.ErrorBaseException:
                raise

            except Exception as e:
                mensaje = (
                    f"Error ejecutando paso del flow. "
                    f"Bloque='{bloque}', paso={indice}/{len(pasos)}, action='{action}', "
                    f"detalle={e}"
                )
                logger.error(f"❌ {mensaje}", exc_info=True)
                raise RPAExceptions.FlujoException(mensaje)


    def _parse_value(self, value, *, bloque: str, indice: int, total: int, action: str, campo: str):
        if isinstance(value, str) and value.startswith("$"):
            variable_name = value[1:]

            if variable_name in self.contexto:
                return str(self.contexto[variable_name])

            if variable_name in self.variables_base:
                return str(self.variables_base[variable_name])

            disponibles_base = ", ".join(sorted(self.variables_base.keys())) or "(vacío)"
            disponibles_contexto = ", ".join(sorted(self.contexto.keys())) or "(vacío)"

            mensaje = (
                f"Variable requerida no encontrada. "
                f"Bloque='{bloque}', paso={indice}/{total}, action='{action}', "
                f"campo='{campo}', variable='${variable_name}'. "
                f"Disponibles variables_base=[{disponibles_base}]. "
                f"Disponibles contexto=[{disponibles_contexto}]."
            )

            logger.error(f"❌ {mensaje}")
            raise RPAExceptions.FlujoException(mensaje)

        return value


    def _reemplazar_variables(self, paso: dict, *, bloque: str, indice: int, total: int, action: str) -> dict:
        return {
            key: self._parse_value(
                value,
                bloque=bloque,
                indice=indice,
                total=total,
                action=action,
                campo=key,
            )
            for key, value in paso.items()
        }

    def _resolver_imagen(self, target_key: str):
        if isinstance(target_key, tuple):
            logger.error(f"🚨 _resolver_imagen recibió una TUPLA en lugar de string: {target_key}")
            # romper aquí para ver quién lo manda
            raise TypeError(f"_resolver_imagen recibió tupla: {target_key}")

        if not target_key:
            return None, None

        if "." in target_key:
            grupo, clave = target_key.split(".")
            ruta = self.image_map.get(grupo, {}).get(clave, target_key)
            return ruta, target_key

        ruta = self.image_map.get(target_key, target_key)
        return ruta, target_key


    # ------------------- Acciones -------------------

    def _action_click(self, paso):
        ruta, nombre = self._resolver_imagen(paso.get("target"))
        self.clicker.hacer_clic(
            target=ruta,
            nombre_logico=nombre,
            offset_x=paso.get("offset_x", 0),
            offset_y=paso.get("offset_y", 0),
            clicks=paso.get("clicks", 1),
            transitorio=paso.get("transitorio", False),
            raise_error=paso.get("raise_error", True),
            timeout=paso.get("timeout")
        )

    def _action_fill(self, paso):
        ruta, nombre = self._resolver_imagen(paso.get("target"))
        self.clicker.clic_y_escribir(
            ruta, paso.get("value", ""), nombre_logico=nombre,
            delay=paso.get("delay", self.delay_default),
            offset_x=paso.get("offset_x", 0), offset_y=paso.get("offset_y", 0),
            transitorio=paso.get("transitorio", False),
            raise_error=paso.get("raise_error", True),
            timeout=paso.get("timeout")
        )

    def _action_clipboard_fill(self, paso):
        # Nota: antes llamaba a un método inexistente en ClickTools
        # (escribir_texto_clipboard); se redirige a clic_y_escribir,
        # que es clic + escritura vía clipboard.
        ruta, nombre = self._resolver_imagen(paso.get("target"))
        self.clicker.clic_y_escribir(
            ruta, paso.get("value", ""), nombre_logico=nombre,
            delay=paso.get("delay", self.delay_default),
            transitorio=paso.get("transitorio", False),
            raise_error=paso.get("raise_error", True),
            timeout=paso.get("timeout")
        )

    def _action_click_y_escribir(self, paso):
        ruta, nombre = self._resolver_imagen(paso.get("target"))
        self.clicker.clic_y_escribir(
            ruta, paso.get("value", ""), nombre_logico=nombre,
            offset_x=paso.get("offset_x", 0), offset_y=paso.get("offset_y", 0),
            delay=paso.get("delay", self.delay_default), clicks=paso.get("clicks", 1),
            transitorio=paso.get("transitorio", False),
            raise_error=paso.get("raise_error", True),
            timeout=paso.get("timeout")
        )

    def _action_click_escribir(self, paso):
        ruta, nombre = self._resolver_imagen(paso.get("target"))
        self.clicker.clic_y_escribir_tradicional(
            ruta, paso.get("value", ""), nombre_logico=nombre,
            offset_x=paso.get("offset_x", 0), offset_y=paso.get("offset_y", 0),
            delay=paso.get("delay", self.delay_default), clicks=paso.get("clicks", 1),
            transitorio=paso.get("transitorio", False),
            raise_error=paso.get("raise_error", True),
            timeout=paso.get("timeout")
        )

    def _action_press_key(self, paso):
        self.app_tools.presionar_tecla(
            paso.get("target"), paso.get("repeticiones", 1)
        )

    def _action_press_keys(self, paso):
        teclas = paso.get("target")
        if not isinstance(teclas, list):
            teclas = [teclas]
        self.app_tools.presionar_combinacion(
            *teclas, repeticiones=paso.get("repeticiones", 1)
        )

    def _action_extract_y_asignar(self, paso):
        ruta, nombre = self._resolver_imagen(paso.get("target"))
        self.extractor.extraer_numero_dinamico(
            imagen=ruta,
            contexto=self.contexto,
            nombre_logico=nombre,
            campo_destino=paso.get("campo_destino"),
            offset_x=paso.get("offset_x", 0),
            offset_y=paso.get("offset_y", 0),
            clicks=paso.get("clicks", 1),
            transitorio=paso.get("transitorio", False)
        )

    def _action_extract_fecha_y_antiguedad(self, paso):
        ruta, nombre = self._resolver_imagen(paso.get("target"))
        self.extractor.extraer_fecha_y_antiguedad(
            imagen=ruta,
            contexto=self.contexto,
            nombre_logico=nombre,
            campo_fecha=paso.get("campo_fecha"),
            campo_antiguedad=paso.get("campo_antiguedad"),
            offset_x=paso.get("offset_x", 0),
            offset_y=paso.get("offset_y", 0),
            clicks=paso.get("clicks", 1),
            transitorio=paso.get("transitorio", False)
        )

    def _action_iniciar_app(self, paso):
        ruta = paso.get("ruta") or self.variables_base.get("ruta_sap")
        self.app_tools.iniciar_aplicacion_directa(
            ruta, paso.get("wait_time", 5)
        )

    def _action_cerrar_app(self, paso):
        nombre_app = paso.get("nombre") or self.variables_base.get("nombre_app")
        self.app_tools.cerrar_proceso_remoto(
            nombre_app, paso.get("wait_time", 2)
        )

    def _action_wait(self, paso):
        self.app_tools.esperar(
            paso.get("wait_time", 1)
        )

    def _action_extraer_texto_con_destino(self, paso: dict):
        campo_destino = paso.get("campo_destino")
        if not campo_destino:
            logger.warning("⚠️ No se especificó 'campo_destino' en el paso.")
            return

        imagen_referencia, nombre_logico = self._resolver_imagen(paso.get("target"))
        nombre_region = paso.get("nombre_region", nombre_logico or campo_destino or "region_ocr")
        palabras_validas = paso.get("palabras_validas", [])

        texto = self.extractor.extraer_texto_de_region(
            nombre_region=nombre_region,
            imagen_referencia=imagen_referencia,
            nombre_logico=nombre_logico,
            offset_x=int(paso.get("offset_x", 0)),
            offset_y=int(paso.get("offset_y", 0)),
            ancho=int(paso.get("ancho", 0)),
            alto=int(paso.get("alto", 0)),
            transitorio=paso.get("transitorio", False),
            ensure_focus=paso.get("ensure_focus", False), 
            stable_wait=float(paso.get("stable_wait", 0.15)),
            palabras_validas=palabras_validas, 
            umbral_similitud=float(paso.get("umbral_similitud", 0.8))
        )
        self.contexto[campo_destino] = texto
        logger.info(f"📥 Guardado en contexto '{campo_destino}': '{texto}'")

    def _action_extraer_y_validar_plan(self, paso: dict):
        campo_destino = paso.get("campo_destino")
        if not campo_destino:
            logger.warning("⚠️ No se especificó 'campo_destino' en el paso.")
            return

        imagen_referencia, nombre_logico = self._resolver_imagen(paso.get("target"))
        nombre_region = paso.get("nombre_region", nombre_logico or campo_destino)

        texto = self.extractor.extraer_y_validar_plan(
            nombre_region=nombre_region,
            imagen_referencia=imagen_referencia,
            offset_x=int(paso.get("offset_x", 0)),
            offset_y=int(paso.get("offset_y", 0)),
            clicks=int(paso.get("clicks", 1)),
            contexto=self.contexto,
            transitorio=paso.get("transitorio", False),
            nombre_logico=nombre_logico
        )

        self.contexto[campo_destino] = texto
        logger.info(f"📥 Guardado en contexto '{campo_destino}': '{texto}'")
        
    def _action_extraer_y_validar_imagen(self, paso):
        ruta, nombre = self._resolver_imagen(paso.get("target"))
    
        self.extractor.extraer_y_validar_imagen(
            ruta_imagen=ruta,
            nombre_logico=nombre,
            contexto=self.contexto,
            timeout=paso.get("timeout", 3)
        )


        
    def _action_buscar_y_seleccionar_servicio(self, paso):
        target = paso.get("target", {})

        referencia = target.get("referencia")           
        imagenes = target.get("imagenes", [])         

        # 🔹 Ahora sí llamamos a ServiceTools
        self.service_tools.buscar_y_seleccionar_servicio(
            referencia=referencia,
            imagenes=imagenes,
            contexto=self.contexto,
            key_contexto=target.get("key_contexto", "resultado_busqueda"),
            clicks_ref=paso.get("clicks_referencia", paso.get("clicks", 1)),
            clicks_img=paso.get("clicks_imagen", paso.get("clicks", 1)),
            offset_x=paso.get("offset_x", 0),
            offset_y=paso.get("offset_y", 0),
            usar_imagen=paso.get("usar_imagen", True),
            raise_error=paso.get("raise_error", True),
            transitorio=target.get("transitorio", False),
            max_intentos=paso.get("max_intentos", 4)
        )
        
            
    def _action_buscar_y_seleccionar(self, paso):
        target = paso.get("target", {})

        referencia = target.get("referencia")
        imagenes = target.get("imagenes", [])

        self.service_tools.buscar_y_seleccionar(
            referencia=referencia,
            imagenes=imagenes,
            contexto=self.contexto,
            key_contexto=target.get("key_contexto", "resultado_busqueda"),
            clicks_ref=paso.get("clicks_referencia", paso.get("clicks", 1)),
            offset_x=paso.get("offset_x", 0),
            offset_y=paso.get("offset_y", 0),
            usar_imagen=paso.get("usar_imagen", True),
            raise_error=paso.get("raise_error", True),
            transitorio=target.get("transitorio", False),
            timeout=paso.get("timeout", 2),           
            max_intentos=paso.get("max_intentos", 1)
        )

                
    def _action_buscar_y_seleccionar_reintento(self, paso):
        target = paso.get("target", {})

        referencia = target.get("referencia")           
        imagenes = target.get("imagenes", [])         
        
        self.service_tools.buscar_y_seleccionar_reintento(
            referencia=referencia,
            imagenes=imagenes,
            contexto=self.contexto,
            key_contexto=target.get("key_contexto", "resultado_busqueda"),
            clicks_ref=paso.get("clicks_referencia", paso.get("clicks", 1)),
            clicks_img=paso.get("clicks_imagen", paso.get("clicks", 1)),
            offset_x=paso.get("offset_x", 0),
            offset_y=paso.get("offset_y", 0),
            usar_imagen=paso.get("usar_imagen", True),
            raise_error=paso.get("raise_error", True),
            transitorio=target.get("transitorio", False),
            max_intentos=paso.get("max_intentos", 4)
        )

    def _action_extraer_validar_error(self, paso: dict):

        ruta, nombre = self._resolver_imagen(paso.get("target"))

        self.extractor.extraer_validar_error(
            ruta_imagen=ruta,
            nombre_logico=nombre,
            contexto=self.contexto,
            offset_x=int(paso.get("offset_x", 0)),
            offset_y=int(paso.get("offset_y", 0)),
            clicks=int(paso.get("clicks", 1)),
            usar_imagen=paso.get("usar_imagen", True),
            raise_error=paso.get("raise_error", True),
            transitorio=paso.get("transitorio", False),
            timeout=int(paso.get("timeout", 2))
        )
        
    def _action_existe_imagen_error(self, paso):
        ruta, nombre = self._resolver_imagen(paso.get("target"))
        self.extractor.existe_imagen_error(
            ruta_imagen=ruta,
            nombre_logico=nombre,
            contexto=self.contexto,
            offset_x=int(paso.get("offset_x", 0)),
            offset_y=int(paso.get("offset_y", 0)),
            clicks=int(paso.get("clicks", 1)),
            usar_imagen=paso.get("usar_imagen", True),
            raise_error=paso.get("raise_error", True),
            transitorio=paso.get("transitorio", False),
            timeout=int(paso.get("timeout", 2))
        )


import logging
from typing import Optional, Tuple
from shared.tools.click_tools import ClickTools
from shared.tools.extraction_tools import ExtractionTools
from shared.tools.region_locator import RegionLocator
from shared.tools.app_tools import AppTools
from shared.tools.exceptions import RPAExceptions
from shared.tools.basic_tools import BasicTools

logger = logging.getLogger(__name__)

class ServiceTools:
    def __init__(self, executor, contexto: dict):
        self.executor = executor
        self.contexto = contexto
        self.clicker = ClickTools()
        self.extractor = ExtractionTools()
        self.region_locator = RegionLocator()
        self.app_tools = AppTools()
        self.basic_tools = BasicTools()

    def buscar_y_seleccionar_servicio(
    self,
    referencia: Optional[str],   # string de referencia (ej: "grupo.clave")
    imagenes: list,              # lista de strings (ej: ["grupo.clave1", "grupo.clave2"])
    contexto: dict,
    key_contexto: str,
    clicks_ref: int = 1,
    clicks_img: int = 1,
    offset_x: int = 0,
    offset_y: int = 0,
    usar_imagen: bool = True,
    raise_error: bool = True,
    transitorio: bool = False,
    max_intentos: int = 4
) -> bool:
        try:
            # Paso 0: clic inicial en la referencia
            if referencia:
                ruta_ref, nombre_ref = self.executor._resolver_imagen(referencia)
                logger.info(f"🎯 Centrando puntero en referencia: {nombre_ref}")
                self.clicker.hacer_clic(
                    target=ruta_ref,
                    offset_x=offset_x,
                    offset_y=offset_y,
                    clicks=clicks_ref,
                    nombre_logico=nombre_ref,
                    usar_imagen=usar_imagen,
                    raise_error=raise_error,
                    transitorio=False
                )
                self.app_tools.esperar(0.3)

            # Paso 1: intentar encontrar imágenes en ciclos
            for intento in range(max_intentos):
                for img in imagenes:  # img es string, se resuelve aquí
                    ruta_img, nombre_img = self.executor._resolver_imagen(img)

                    if self.extractor.imagen_esta_presente(
                        ruta_img, nombre_img, timeout=2, transitorio=transitorio
                    ):
                        logger.info(f"✅ Imagen encontrada: {nombre_img}")
                        self.clicker.hacer_clic(
                            target=ruta_img,
                            offset_x=offset_x,
                            offset_y=offset_y,
                            clicks=clicks_img,
                            nombre_logico=nombre_img,
                            usar_imagen=usar_imagen,
                            raise_error=raise_error,
                            transitorio=transitorio
                        )
                        contexto[key_contexto] = True
                        return True

                logger.info(
                    f"🔄 Intento {intento+1}/{max_intentos}: no se encontraron imágenes, presionando PgDn..."
                )
                self.app_tools.presionar_tecla_real("PgDn")
                self.app_tools.esperar(0.5)

            # No encontrado
            logger.info(f"❌ No se detectó {key_contexto} tras {max_intentos} intentos.")
            contexto[key_contexto] = False
            return False

        except Exception as e:
            logger.error(f"❌ Error en buscar_y_seleccionar_servicio: {e}", exc_info=True)
            contexto[key_contexto] = False
            return False
        
        
    def buscar_y_seleccionar(
    self,
    referencia: Optional[str],        # Imagen donde se hará clic si se detecta algo
    imagenes: list,                   # Lista de imágenes para detección
    contexto: dict,
    key_contexto: str,
    clicks_ref: int = 1,
    offset_x: int = 0,
    offset_y: int = 0,
    usar_imagen: bool = True,
    raise_error: bool = True,
    transitorio: bool = False,
    timeout: int = 2,                 # ⬅️ Timeout configurable
    max_intentos: int = 1             # ⬅️ Cantidad de reintentos
) -> bool:

        try:
            # 1️⃣ Validación de referencia
            if not referencia:
                logger.error("⚠️ No se especificó imagen de referencia.")
                contexto[key_contexto] = False
                return False

            ruta_ref, nombre_ref = self.executor._resolver_imagen(referencia)
            logger.info(f"🎯 Referencia base para clic: {nombre_ref}")

            # 2️⃣ Intentos para encontrar alguna imagen objetivo
            for intento in range(1, max_intentos + 1):
                logger.info(f"🔍 Intento {intento}/{max_intentos}: buscando imágenes objetivo...")

                # Recorrer cada imagen posible
                for img in imagenes:
                    ruta_img, nombre_img = self.executor._resolver_imagen(img)

                    # Verificación de presencia
                    if self.extractor.imagen_esta_presente(
                        ruta_img,
                        nombre_img,
                        timeout=timeout,
                        transitorio=transitorio
                    ):
                        logger.info(f"✅ Imagen detectada: {nombre_img}")

                        # 3️⃣ CLIC ÚNICAMENTE EN LA REFERENCIA
                        click_ok = self.clicker.hacer_clic(
                            target=ruta_ref,
                            offset_x=offset_x,
                            offset_y=offset_y,
                            clicks=clicks_ref,
                            nombre_logico=nombre_ref,
                            usar_imagen=usar_imagen,
                            raise_error=raise_error,
                            transitorio=transitorio
                        )

                        if not click_ok:
                            logger.warning(f"⚠️ No se pudo hacer clic en referencia '{nombre_ref}'.")
                            contexto[key_contexto] = False
                            return False

                        contexto[key_contexto] = True
                        return True

                # ➜ Si no se encontró ninguna imagen, esperar antes del siguiente intento
                logger.info("🔄 No se detectó imagen. Reintentando...")
                self.app_tools.esperar(0.8)

            # 4️⃣ Si no se encontró nada tras todos los intentos
            logger.warning(f"❌ No se detectó ninguna imagen válida tras {max_intentos} intentos.")
            contexto[key_contexto] = False
            return False

        except Exception as e:
            logger.error(f"💥 Error en buscar_y_seleccionar: {e}", exc_info=True)
            contexto[key_contexto] = False
            return False

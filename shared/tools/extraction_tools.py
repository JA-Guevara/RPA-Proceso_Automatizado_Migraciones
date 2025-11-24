import pyautogui
import pyperclip
import pytesseract
import unicodedata
import logging
import datetime
import os
import re
import cv2
import time
import numpy as np
from typing import Optional, Tuple
from dateutil.parser import parse
import difflib
from typing import Optional, List
from shared.tools.app_tools import AppTools
from shared.tools.click_tools import ClickTools
from shared.tools.basic_tools import BasicTools
from shared.tools.region_locator import RegionLocator

logger = logging.getLogger(__name__)

class ExtractionTools:
    def __init__(self, writer=None, default_delay: float = 1.0, default_confidence: float = 0.9, timeout: int = 30):
        self.writer = writer
        self.default_delay = default_delay
        self.default_confidence = default_confidence
        self.timeout = timeout
        self.app_tools = AppTools()
        self.clicker = ClickTools()
        self.basic_tools = BasicTools()
        self.region = RegionLocator()
        pytesseract.pytesseract.tesseract_cmd = r"C:\Users\torricoslo\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
        

    def normalizar_ocr(self, texto: str) -> str:
        """Limpieza avanzada del texto OCR."""
        texto = texto.upper()
        texto = unicodedata.normalize('NFKD', texto)
        texto = re.sub(r'[^A-Z0-9 ]', '', texto)  # Solo letras, números y espacios
        texto = re.sub(r'\s+', ' ', texto).strip()
        return texto

    def extraer_texto_de_region(
        self,
        nombre_region: str,
        imagen_referencia: Optional[str] = None,
        offset_x: int = 0,
        offset_y: int = 0,
        ancho: int = 0,
        alto: int = 0,
        transitorio: bool = False,
        nombre_logico: Optional[str] = None,
        ensure_focus: bool = False,
        stable_wait: float = 0.15,
        palabras_validas: Optional[List[str]] = None,
        umbral_similitud: float = 0.75
    ) -> str:

        try:
            # === 1️⃣ Localizar región ===
            if imagen_referencia:
                pos = self.clicker.buscar_imagen(
                    imagen_referencia,
                    nombre_logico=nombre_logico or nombre_region,
                    transitorio=transitorio
                )
                if not pos:
                    logger.warning(f"⚠️ Imagen de referencia '{imagen_referencia}' no encontrada.")
                    return ""
                left, top, w_ref, h_ref = map(int, pos)
                x = left + offset_x
                y = top + offset_y
                ancho = ancho or w_ref
                alto = alto or h_ref
            else:
                x, y = int(offset_x), int(offset_y)
                ancho, alto = int(ancho), int(alto)

            if ancho <= 0 or alto <= 0:
                logger.warning(f"⚠️ Región inválida (ancho={ancho}, alto={alto}) en '{nombre_region}'.")
                return ""

            if ensure_focus:
                try:
                    pyautogui.click(x + ancho // 2, y + alto // 2)
                except Exception:
                    pass
            time.sleep(stable_wait)

            logger.info(f"🖼️ Capturando región '{nombre_region}': (x={x}, y={y}, w={ancho}, h={alto})")

            # === 2️⃣ Captura y preprocesamiento (suave) ===
            screenshot = pyautogui.screenshot(region=(x, y, ancho, alto))
            screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            img_gray = cv2.cvtColor(screenshot_cv, cv2.COLOR_BGR2GRAY)
            img_resized = cv2.resize(img_gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            _, img_thresh = cv2.threshold(img_resized, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # Guardar imagen debug
            ts = int(time.time() * 1000)
            dbg_dir = os.path.join("assets", "images_debug")
            os.makedirs(dbg_dir, exist_ok=True)
            cv2.imwrite(os.path.join(dbg_dir, f"ocr_{nombre_region}_{ts}.png"), img_thresh)

            # === 3️⃣ OCR ===
            config = r'--psm 7 --oem 3'
            texto_crudo = pytesseract.image_to_string(img_thresh, config=config).strip()
            texto_normalizado = self.normalizar_ocr(texto_crudo)
            logger.info(f"🧠 OCR '{nombre_region}': '{texto_crudo}' → '{texto_normalizado}'")

            # === 4️⃣ Validación semántica (con trazas) ===
            if palabras_validas:
                logger.info(f"🧩 Validación semántica activada: palabras={palabras_validas}, umbral={umbral_similitud}")
                mejores = []
                for palabra in palabras_validas:
                    similitud = difflib.SequenceMatcher(None, texto_normalizado, palabra.upper()).ratio()
                    mejores.append((palabra, round(similitud, 3)))
                    logger.info(f"   🔹 Comparando '{texto_normalizado}' ↔ '{palabra.upper()}': similitud={similitud:.3f}")

                # Elegir la mejor coincidencia
                palabra_mejor, puntaje = max(mejores, key=lambda x: x[1])
                if puntaje >= umbral_similitud:
                    if texto_normalizado != palabra_mejor.upper():
                        logger.info(f"🔄 Corrección OCR: '{texto_normalizado}' → '{palabra_mejor.upper()}' (confianza {puntaje:.2f})")
                    texto_normalizado = palabra_mejor.upper()
                else:
                    logger.warning(f"⚠️ Ninguna coincidencia supera el umbral ({umbral_similitud}); texto sin corrección.")

            logger.info(f"📋 Texto final '{nombre_region}': '{texto_normalizado}'")
            return texto_normalizado

        except Exception as e:
            logger.error(f"❌ Error OCR en región '{nombre_region}': {e}", exc_info=True)
            return ""

    def imagen_esta_presente(
    self,
    ruta_imagen: str,
    nombre_logico: Optional[str] = None,
    timeout: int = 2,
    confidence: float = 0.9,
    transitorio: bool = False
) -> bool:
        nombre_logico = nombre_logico or ruta_imagen
        start = time.time()

        while time.time() - start < timeout:
            try:
                pos = pyautogui.locateOnScreen(ruta_imagen, confidence=confidence)
                if pos:
                    region = (pos.left, pos.top, pos.width, pos.height)

                    if not transitorio:
                        # Solo guarda si no es transitorio
                        self.region.guardar_region(nombre_logico, region)
                        logger.debug(
                            f"✅ Imagen encontrada y región guardada: {ruta_imagen} [{nombre_logico}] {region}"
                        )
                    else:
                        logger.debug(
                            f"👀 Imagen encontrada (transitorio, no se guarda región): {ruta_imagen} [{nombre_logico}]"
                        )

                    return True
            except Exception as e:
                logger.debug(f"⚠️ Error al buscar imagen {ruta_imagen}: {e}")
            time.sleep(0.2)

        logger.info(f"⚠️ Imagen no encontrada [{nombre_logico}]")
        return False


    def extraer_fecha_y_antiguedad(self, imagen: str, contexto: dict,
                                offset_x: int = 0, offset_y: int = 0,
                                clicks: int = 2, nombre_logico: str = None,
                                campo_fecha: str = None, campo_antiguedad: str = None,
                                transitorio: bool = False):

        try:
            # --- clic y lectura ---
            self.clicker.hacer_clic(
                target=imagen,
                clicks=clicks,
                offset_x=offset_x,
                offset_y=offset_y,
                nombre_logico=nombre_logico or imagen,
                transitorio=transitorio
            )

            texto = self.basic_tools.copiar_texto_actual().strip()
            texto = texto.replace("...", "").replace("\n", "").strip()

            # --- VALIDAR SOLO QUE SEA FECHA EN CUALQUIER FORMATO ---
            try:
                fecha_valida = parse(texto, dayfirst=False, yearfirst=False)
            except:
                contexto["existe_error_captura"] = True
                logger.warning(f"⚠️ Texto extraído NO es una fecha: '{texto}'")
                return False

            # ✔ si es fecha → normalizar a YYYY-MM-DD
            fecha_str = fecha_valida.strftime("%Y-%m-%d")
            contexto["existe_error_captura"] = False

            if campo_fecha:
                contexto[campo_fecha] = fecha_str
                logger.info(f"📅 Fecha válida extraída: {fecha_str}")

            # --- Calcular antigüedad ---
            if campo_antiguedad:
                anios, meses, dias = self.basic_tools.calcular_antiguedad(fecha_str)
                contexto[f"{campo_antiguedad}_meses_rpa"] = meses
                contexto["codigo_plan_consumo_asignados_rpa"] = 186 if meses > 6 else 184
                logger.info(f"📆 Antigüedad: {anios} años, {meses} meses, {dias} días")

            return True

        except Exception as e:
            logger.error(f"❌ Error en extraer_fecha_y_antiguedad: {e}", exc_info=True)
            contexto["existe_error_captura"] = True
            return False

    def extraer_validar_error(
    self,ruta_imagen: str,nombre_logico: str,contexto: dict, offset_x: int = 0, offset_y: int = 0, clicks: int = 1, usar_imagen: bool = True, raise_error: bool = True, transitorio: bool = False, timeout: int = 2) -> bool:
        try:
            # Paso 1: verificar si la imagen aparece en pantalla
            if not self.imagen_esta_presente(ruta_imagen, nombre_logico, timeout=timeout):
                logger.info(f"✅ No se detectó error [{nombre_logico}] en pantalla.")
                contexto["existe_error"] = False
                return False

            # Paso 2: hacer clic en la imagen encontrada
            self.clicker.hacer_clic(
                target=ruta_imagen,
                offset_x=offset_x,
                offset_y=offset_y,
                clicks=clicks,
                nombre_logico=nombre_logico,
                usar_imagen=usar_imagen,
                raise_error=raise_error,
                transitorio=transitorio
            )

            # Paso 3: copiar texto
            self.app_tools.presionar_combinacion_real("ctrl", "c")
            self.app_tools.esperar(0.2)

            texto = pyperclip.paste().strip()
            lineas = texto.splitlines()
            mensaje_error = lineas[-1] if lineas else "ERROR NO DETECTADO"
            mensaje_error = mensaje_error.strip()

            # Paso 4: guardar en contexto
            contexto["mensaje_error"] = mensaje_error
            contexto["existe_error"] = True

            logger.warning(f"⚠️ Error detectado: {mensaje_error}")
            return True

        except Exception as e:
            logger.error(f"❌ Error en extraer_validar_error [{nombre_logico}]: {e}", exc_info=True)
            contexto["existe_error"] = False
            return False
        
        
        
    def extraer_y_validar_imagen(
    self,
    ruta_imagen: str,
    nombre_logico: str,
    contexto: dict,
    timeout: int = 2
) -> bool:

        try:
            if self.imagen_esta_presente(ruta_imagen, nombre_logico, timeout=timeout):
                # Imagen encontrada → validación positiva
                logger.info(f"✅ Imagen detectada: '{nombre_logico}'")
                contexto["imagen_encontrada"] = True
                contexto["mensaje_imagen"] = f"Imagen visible: '{nombre_logico}'"
                return True
            else:
                # Imagen no encontrada → detener flujo
                logger.warning(f"🚫 No se detectó imagen visual: '{nombre_logico}'")
                contexto["imagen_encontrada"] = False
                contexto["mensaje_imagen"] = f"No se detectó imagen: '{nombre_logico}'"
                return False

        except Exception as e:
            mensaje_error = f"❌ Error interno al validar imagen [{nombre_logico}]: {e}"
            logger.error(mensaje_error, exc_info=True)
            contexto["imagen_encontrada"] = False
            contexto["mensaje_imagen"] = mensaje_error
            return False

    def extraer_numero_dinamico(self, imagen: str, contexto: dict, offset_x: int = 0, offset_y: int = 0,
                             clicks: int = 2, nombre_logico: str = None, campo_destino: str = None,
                             transitorio: bool = False) -> None:
        try:
            exito_clic = self.clicker.hacer_clic(
                target=imagen,
                clicks=clicks,
                offset_x=offset_x,
                offset_y=offset_y,
                nombre_logico=nombre_logico or imagen,
                transitorio=transitorio
            )

            if not exito_clic:
                logger.warning(f"⚠️ No se pudo hacer clic en '{imagen}'.")
                return
            texto = self.basic_tools.copiar_texto_actual()
            contexto[campo_destino] = texto
            logger.info(f"📥 Guardado en contexto '{campo_destino}': '{texto}'")

        except Exception as e:
            logger.error(f"❌ Error al extraer número dinámico desde '{imagen}': {e}", exc_info=True)




    def existe_imagen_error(
    self,
    ruta_imagen: str,
    nombre_logico: str,
    contexto: dict,
    offset_x: int = 0,
    offset_y: int = 0,
    clicks: int = 1,
    usar_imagen: bool = True,
    raise_error: bool = True,
    transitorio: bool = False,
    timeout: int = 2
) -> bool:

        try:
            # Paso 1️⃣ - Buscar la imagen en pantalla
            if not self.imagen_esta_presente(ruta_imagen, nombre_logico, timeout=timeout):
                logger.info(f"✅ No se detectó imagen [{nombre_logico}] en pantalla.")
                return False
            # Paso 2️⃣ - Imagen encontrada → hacer clic
            self.clicker.hacer_clic(
                target=ruta_imagen,
                offset_x=offset_x,
                offset_y=offset_y,
                clicks=clicks,
                nombre_logico=nombre_logico,
                usar_imagen=usar_imagen,
                raise_error=raise_error,
                transitorio=transitorio
            )
            logger.warning(f"⚠️ Se detectó imagen: '{nombre_logico}' → clic ejecutado correctamente.")
            return True

        except Exception as e:
            logger.error (f"❌ Error interno al validar y hacer clic [{nombre_logico}]: {e}")


    def extraer_y_validar_plan(
    self,
    nombre_region: str,
    imagen_referencia: Optional[str] = None,
    offset_x: int = 0,
    offset_y: int = 0,
    clicks: int = 1,
    contexto: dict = None,
    transitorio: bool = False,
    nombre_logico: Optional[str] = None,
    limpiar: bool = True
) -> str:

        try:
            if imagen_referencia:
                existe = self.clicker.buscar_imagen(
                    imagen_referencia,
                    nombre_logico=nombre_logico or nombre_region,
                    transitorio=transitorio
                )

                if not existe:
                    if contexto is not None:
                        contexto["existe_error_captura_plan"] = True
                    logger.warning(f"⚠️ [PLAN] Imagen no encontrada → NO se pudo extraer texto.")
                    return ""

            self.clicker.hacer_clic(
                target=imagen_referencia if imagen_referencia else (offset_x, offset_y),
                clicks=clicks,
                offset_x=offset_x,
                offset_y=offset_y,
                usar_imagen=bool(imagen_referencia),
                raise_error=True,
                nombre_logico=nombre_logico or nombre_region,
                transitorio=transitorio
            )

            # === 3. Copiar texto ===
            self.app_tools.presionar_combinacion_real("ctrl", "c")
            self.app_tools.esperar(0.25)

            texto = pyperclip.paste() or ""
            # === 4. Limpieza ===
            if limpiar:
                texto_limpio = texto.strip()
                texto_limpio = texto_limpio.replace("\n", " ").replace("\r", " ").replace("\t", " ")
                texto_limpio = " ".join(texto_limpio.split())
            else:
                texto_limpio = texto
            # === 5. Validaciones ===
            texto_lower = texto_limpio.lower()

            regla_length = len(texto_limpio) <= 100
            regla_plan = "plan" in texto_lower

            logger.info(f"🔍 [PLAN] Limpio y filtrado ' ? {texto_limpio}")

            reglas_validas = regla_length and regla_plan

            if contexto is not None:
                contexto["existe_error_captura_plan"] = not reglas_validas
            if not reglas_validas:
                logger.warning(f"⚠️ [PLAN] Texto NO válido según reglas. Se devolverá igualmente: '{texto_limpio}'")

            return texto_limpio

        except Exception as e:
            logger.error(f"💥 [PLAN] Error al extraer texto en '{nombre_region}': {e}", exc_info=True)
            if contexto is not None:
                contexto["existe_error_captura_plan"] = True
            return ""

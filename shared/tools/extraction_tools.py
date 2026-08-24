import pyautogui
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
from datetime import datetime

import difflib
from typing import Optional, List
from shared.tools.app_tools import AppTools
from shared.tools.click_tools import ClickTools
from shared.tools.basic_tools import BasicTools
from shared.tools.image_locator import default_locator
from shared.tools.clipboard import specs as ESPECS
from config.config import EnvConfig

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
        self.locator = default_locator
        pytesseract.pytesseract.tesseract_cmd = EnvConfig.TESSERACT_PATH


    def normalizar_ocr(self, texto: str) -> str:
        texto = texto.upper()
        texto = unicodedata.normalize('NFKD', texto)
        texto = re.sub(r'[^A-Z0-9 ]', '', texto)
        texto = re.sub(r'\s+', ' ', texto).strip()
        return texto

    @staticmethod
    def _flag_env(nombre: str, default: str = "false") -> bool:
        valor = str(getattr(EnvConfig, nombre, default) or default).strip().lower()
        return valor in ("1", "true", "si", "sí")

    def _marcar_ocr(self, contexto, campo_destino, no_leible: bool, motivo: str = ""):
        """
        Deja constancia de si el OCR pudo leer o no.

        Sin esto, "" significa dos cosas incompatibles: "el campo esta vacio" y
        "no pude leer". Los tres consumidores de OCR de region (forma_pago,
        situacion, idctl_actual) no podian distinguirlas, y por eso un fallo
        tecnico se convertia en un resultado de negocio.
        """
        if contexto is None or not campo_destino:
            return
        contexto[f"existe_error_ocr_{campo_destino}"] = bool(no_leible)
        if no_leible and motivo:
            contexto[f"motivo_error_ocr_{campo_destino}"] = motivo

    def _guardar_evidencia_ocr(self, imagen, nombre_region: str):
        """Evidencia acotada y con poda. Antes se escribia un PNG en CADA
        llamada, sin flag y sin limite de archivos."""
        import glob
        try:
            dbg_dir = os.path.join("storage", "ocr_debug")
            os.makedirs(dbg_dir, exist_ok=True)
            ts = int(time.time() * 1000)
            seguro = re.sub(r"[^A-Za-z0-9._-]+", "_", str(nombre_region))[:40]
            cv2.imwrite(os.path.join(dbg_dir, f"ocr_{seguro}_{ts}.png"), imagen)

            maximo = int(getattr(EnvConfig, "OCR_EVIDENCIA_MAX", 60) or 60)
            archivos = sorted(
                glob.glob(os.path.join(dbg_dir, "ocr_*.png")),
                key=os.path.getmtime, reverse=True,
            )
            for viejo in archivos[maximo:]:
                try:
                    os.remove(viejo)
                except OSError:
                    pass
        except Exception:
            logger.debug("No se pudo guardar evidencia OCR", exc_info=True)

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
        umbral_similitud: float = 0.75,
        contexto: Optional[dict] = None,
        campo_destino: Optional[str] = None,
    ) -> str:

        try:
            if imagen_referencia:
                pos = self.clicker.buscar_imagen(
                    imagen_referencia,
                    nombre_logico=nombre_logico or nombre_region,
                    transitorio=transitorio
                )
                if not pos:
                    logger.warning(f"⚠️ Imagen de referencia '{imagen_referencia}' no encontrada.")
                    self._marcar_ocr(contexto, campo_destino, True, "referencia_no_encontrada")
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
                self._marcar_ocr(contexto, campo_destino, True, "region_invalida")
                return ""

            if ensure_focus:
                try:
                    pyautogui.click(x + ancho // 2, y + alto // 2)
                except Exception:
                    pass
            time.sleep(stable_wait)

            logger.info(f"🖼️ Capturando región '{nombre_region}': (x={x}, y={y}, w={ancho}, h={alto})")

            screenshot = pyautogui.screenshot(region=(x, y, ancho, alto))
            screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            img_gray = cv2.cvtColor(screenshot_cv, cv2.COLOR_BGR2GRAY)
            img_resized = cv2.resize(img_gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            _, img_thresh = cv2.threshold(img_resized, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # Proporcion de "tinta" en el recorte. Con THRESH_BINARY+OTSU el
            # fondo claro queda en 255 y el texto oscuro en 0, asi que los
            # pixeles distintos de cero son fondo.
            #
            # Esto es lo que permite distinguir "el campo esta genuinamente
            # vacio" de "no pude leer el texto que hay". Cuesta un countNonZero,
            # no una segunda pasada de OCR.
            tinta = 1.0 - (cv2.countNonZero(img_thresh) / float(img_thresh.size))
            region_vacia = tinta < float(getattr(EnvConfig, "OCR_UMBRAL_TINTA", 0.005) or 0.005)

            if self._flag_env("OCR_EVIDENCIA"):
                self._guardar_evidencia_ocr(img_thresh, nombre_region)

            config = r'--psm 7 --oem 3'
            texto_crudo = pytesseract.image_to_string(img_thresh, config=config).strip()
            texto_normalizado = self.normalizar_ocr(texto_crudo)
            logger.info(f"🧠 OCR '{nombre_region}': '{texto_crudo}' → '{texto_normalizado}'")

            tri_estado = self._flag_env("OCR_TRI_ESTADO", "true")

            if palabras_validas:
                logger.info(f"🧩 Validación semántica activada: palabras={palabras_validas}, umbral={umbral_similitud}")
                mejores = []
                for palabra in palabras_validas:
                    similitud = difflib.SequenceMatcher(None, texto_normalizado, palabra.upper()).ratio()
                    mejores.append((palabra, round(similitud, 3)))
                    logger.info(f"   🔹 Comparando '{texto_normalizado}' ↔ '{palabra.upper()}': similitud={similitud:.3f}")

                palabra_mejor, puntaje = max(mejores, key=lambda x: x[1])

                if puntaje >= umbral_similitud:
                    if texto_normalizado != palabra_mejor.upper():
                        logger.info(f"🔄 Corrección OCR: '{texto_normalizado}' → '{palabra_mejor.upper()}' (confianza {puntaje:.2f})")
                    texto_normalizado = palabra_mejor.upper()
                    self._marcar_ocr(contexto, campo_destino, False)

                elif region_vacia:
                    # Ninguna palabra coincide PERO el recorte no tiene tinta:
                    # el campo esta realmente vacio, no es un fallo de lectura.
                    logger.info(
                        "⬜ Región '%s' sin tinta (%.4f) → vacío confirmado",
                        nombre_region, tinta,
                    )
                    texto_normalizado = ""
                    self._marcar_ocr(contexto, campo_destino, False)

                else:
                    logger.warning(
                        "⚠️ OCR ilegible en '%s': ninguna coincidencia supera %s "
                        "(mejor=%s@%.2f, tinta=%.4f)",
                        nombre_region, umbral_similitud, palabra_mejor, puntaje, tinta,
                    )
                    self._marcar_ocr(
                        contexto, campo_destino, bool(tri_estado),
                        "sin_coincidencia_con_tinta",
                    )

            else:
                no_leible = (not texto_normalizado) and (not region_vacia)
                if no_leible:
                    logger.warning(
                        "⚠️ OCR vacío con tinta presente en '%s' (tinta=%.4f)",
                        nombre_region, tinta,
                    )
                self._marcar_ocr(
                    contexto, campo_destino, bool(tri_estado and no_leible),
                    "ocr_vacio_con_tinta",
                )

            logger.info(f"📋 Texto final '{nombre_region}': '{texto_normalizado}'")
            return texto_normalizado

        except Exception as e:
            logger.error(f"❌ Error OCR en región '{nombre_region}': {e}", exc_info=True)
            self._marcar_ocr(contexto, campo_destino, True, f"excepcion: {e}")
            return ""

    def imagen_esta_presente(
    self,
    ruta_imagen: str,
    nombre_logico: Optional[str] = None,
    timeout: int = 2,
    confidence: float = 0.9,
    transitorio: bool = False
) -> bool:
        return self.locator.esta_presente(
            ruta_imagen,
            nombre_logico=nombre_logico or ruta_imagen,
            timeout=timeout,
            confidence=confidence,
        )


    def extraer_fecha_y_antiguedad(
        self,
        imagen: str,
        contexto: dict,
        offset_x: int = 0,
        offset_y: int = 0,
        clicks: int = 2,
        nombre_logico: str = None,
        campo_fecha: str = None,
        campo_antiguedad: str = None,
        transitorio: bool = False,
    ) -> bool:
        try:
            self.clicker.hacer_clic(
                target=imagen,
                clicks=clicks,
                offset_x=offset_x,
                offset_y=offset_y,
                nombre_logico=nombre_logico or imagen,
                transitorio=transitorio,
            )

            texto = self.basic_tools.copiar_texto_actual().strip()
            texto = (
                texto
                .replace("...", "")
                .replace("\n", "")
                .replace("\r", "")
                .strip()
            )

            logger.info("📥 Texto capturado fecha: '%s'", texto)

            fechas_invalidas = {
                "",
                "00/00/0000",
                "0/0/0000",
                "00-00-0000",
            }

            if texto in fechas_invalidas:
                mensaje = f"Fecha inválida detectada: '{texto}'"
                logger.error(mensaje)
                contexto["existe_error_captura"] = True
                contexto["mensaje_error"] = mensaje
                return False

            try:
                fecha_valida = datetime.strptime(texto, "%m/%d/%Y")
            except ValueError as error:
                mensaje = (
                    f"Texto extraído no es una fecha válida "
                    f"en formato mes/día/año: '{texto}'. Error: {error}"
                )
                logger.error(mensaje)
                contexto["existe_error_captura"] = True
                contexto["mensaje_error"] = mensaje
                return False

            hoy = datetime.now().date()
            fecha_comparacion = fecha_valida.date()

            logger.info(
                "📅 Fecha interpretada | original='%s' | convertida=%s | hoy=%s",
                texto,
                fecha_comparacion,
                hoy,
            )

            if fecha_comparacion > hoy:
                mensaje = (
                    f"Fecha futura inválida detectada: "
                    f"{fecha_comparacion.strftime('%Y-%m-%d')}"
                )
                logger.error(mensaje)
                contexto["existe_error_captura"] = True
                contexto["mensaje_error"] = mensaje
                return False

            if fecha_valida.year < 2000:
                mensaje = f"Fecha demasiado antigua detectada: {fecha_comparacion}"
                logger.error(mensaje)
                contexto["existe_error_captura"] = True
                contexto["mensaje_error"] = mensaje
                return False

            fecha_str = fecha_valida.strftime("%Y-%m-%d")

            contexto["existe_error_captura"] = False
            contexto.pop("mensaje_error", None)

            if campo_fecha:
                contexto[campo_fecha] = fecha_str
                logger.info("📅 Fecha válida extraída: %s", fecha_str)

            if campo_antiguedad:
                antiguedad = self.basic_tools.calcular_antiguedad(fecha_str)

                if antiguedad is None:
                    mensaje = f"No se pudo calcular antigüedad para: {fecha_str}"
                    logger.error(mensaje)
                    contexto["existe_error_captura"] = True
                    contexto["mensaje_error"] = mensaje
                    return False

                anios, meses, dias = antiguedad

                contexto[f"{campo_antiguedad}_meses_rpa"] = meses
                contexto["codigo_plan_consumo_asignados_rpa"] = (
                    186 if meses > 6 else 184
                )

                logger.info(
                    "📆 Antigüedad: %s años, %s meses totales, %s días",
                    anios,
                    meses,
                    dias,
                )

            return True

        except Exception as error:
            mensaje = (
                f"Error inesperado en extraer_fecha_y_antiguedad: {error}"
            )
            logger.error(mensaje, exc_info=True)
            contexto["existe_error_captura"] = True
            contexto["mensaje_error"] = mensaje
            return False

    def extraer_validar_error(
    self,ruta_imagen: str,nombre_logico: str,contexto: dict, offset_x: int = 0, offset_y: int = 0, clicks: int = 1, usar_imagen: bool = True, raise_error: bool = True, transitorio: bool = False, timeout: int = 2) -> bool:
        try:
            if not self.imagen_esta_presente(ruta_imagen, nombre_logico, timeout=timeout):
                logger.info(f"✅ No se detectó error [{nombre_logico}] en pantalla.")
                contexto["existe_error"] = False
                return False

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

            texto = self.basic_tools.copiar_texto_actual(
                seleccionar_todo=False,
                limpiar=True,
                usar_real=True,
                spec=ESPECS.ERROR_BCCS,
            )
            lineas = texto.splitlines()
            mensaje_error = lineas[-1] if lineas else "ERROR NO DETECTADO"
            mensaje_error = mensaje_error.strip()

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
                logger.info(f"✅ Imagen detectada: '{nombre_logico}'")
                contexto["imagen_encontrada"] = True
                contexto["mensaje_imagen"] = f"Imagen visible: '{nombre_logico}'"
                return True
            else:
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
            if not self.imagen_esta_presente(ruta_imagen, nombre_logico, timeout=timeout):
                logger.info(f"✅ No se detectó imagen [{nombre_logico}] en pantalla.")
                return False
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

            texto = self.basic_tools.copiar_texto_actual(
                seleccionar_todo=False,
                limpiar=False,
                usar_real=True,
                spec=ESPECS.PLAN,
            )
            if limpiar:
                texto_limpio = texto.strip()
                texto_limpio = texto_limpio.replace("\n", " ").replace("\r", " ").replace("\t", " ")
                texto_limpio = " ".join(texto_limpio.split())
            else:
                texto_limpio = texto
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



import os
import json
import time
import logging
from typing import Tuple, Optional, Dict
import pyautogui

BASE_DIR = os.getcwd()
REGION_FOLDER = os.path.join(BASE_DIR, "storage", "data", "region")
os.makedirs(REGION_FOLDER, exist_ok=True)
REGION_FILE = os.path.join(REGION_FOLDER, "regions.json")

class RegionLocator:
    def __init__(self, path_json: str = REGION_FILE):
        self.logger = logging.getLogger(__name__)
        self.path_json = path_json
        self.regiones: Dict[str, Dict[str, int]] = self._cargar_archivo()

    # ---------- Persistencia ----------
    def _cargar_archivo(self) -> Dict[str, Dict[str, int]]:
        if os.path.exists(self.path_json):
            try:
                with open(self.path_json, "r", encoding="utf-8") as f:
                    contenido = f.read().strip()
                    if contenido:
                        return json.loads(contenido)
            except Exception:
                self.logger.error(f"❌ Error al leer regiones: {self.path_json}", exc_info=True)
        return {}

    def _guardar_archivo(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.path_json), exist_ok=True)
            with open(self.path_json, "w", encoding="utf-8") as f:
                json.dump(self.regiones, f, indent=4)
        except Exception:
            self.logger.error(f"❌ Error al guardar regiones: {self.path_json}", exc_info=True)

    def guardar_region(self, nombre_logico: str, region: Tuple[int, int, int, int]) -> None:
        """Guarda/actualiza una región por nombre lógico."""
        if not isinstance(region, (tuple, list)) or len(region) != 4:
            self.logger.error("⚠️ Región inválida: se requiere tupla/lista (x, y, width, height).")
            return
        self.regiones[nombre_logico] = {
            "x": int(region[0]),
            "y": int(region[1]),
            "width": int(region[2]),
            "height": int(region[3]),
        }
        self._guardar_archivo()

    def obtener_region(self, nombre_logico: str) -> Optional[Dict[str, int]]:
        return self.regiones.get(nombre_logico)

    def region_existe(self, nombre_logico: str) -> bool:
        return nombre_logico in self.regiones

    def eliminar_region(self, nombre_logico: str) -> None:
        if nombre_logico in self.regiones:
            del self.regiones[nombre_logico]
            self._guardar_archivo()

    # ---------- Búsqueda con actualización ----------
    def buscar_o_actualizar_region(
        self,
        image_path: str,
        nombre_logico: str,
        confidence: float = 0.90,
        t_region: float = 3.0,
        t_total: float = 8.0,
        sleep_interval: float = 0.10,
    ) -> Optional[Tuple[int, int, int, int]]:

        inicio = time.time()
        pos = None

        # Fase 1: región guardada
        region_data = self.obtener_region(nombre_logico)
        if region_data:
            region_box = (region_data["x"], region_data["y"], region_data["width"], region_data["height"])
            while (time.time() - inicio) < min(t_region, t_total):
                try:
                    pos = pyautogui.locateOnScreen(image_path, confidence=confidence, region=region_box)
                    if pos:
                        return (pos.left, pos.top, pos.width, pos.height)
                except Exception:
                    self.logger.debug("locateOnScreen (región) falló", exc_info=True)
                time.sleep(sleep_interval)

        # Fase 2: pantalla completa
        while (time.time() - inicio) < t_total:
            try:
                pos = pyautogui.locateOnScreen(image_path, confidence=confidence)
                if pos:
                    nueva_region = (pos.left, pos.top, pos.width, pos.height)
                    # Guardar o actualizar SIEMPRE bajo nombre_logico (clave estable)
                    existed = self.region_existe(nombre_logico)
                    self.guardar_region(nombre_logico, nueva_region)
                    if existed:
                        self.logger.info(f"🔁 Región actualizada para '{nombre_logico}': {nueva_region}")
                    else:
                        self.logger.info(f"🆕 Región guardada para '{nombre_logico}': {nueva_region}")
                    return nueva_region
            except Exception:
                self.logger.debug("locateOnScreen (pantalla completa) falló", exc_info=True)
            time.sleep(sleep_interval)

        self.logger.warning(f"❌ Imagen no encontrada (timeout {t_total}s): {image_path} [{nombre_logico}]")
        return None

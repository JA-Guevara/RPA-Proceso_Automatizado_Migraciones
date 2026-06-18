import logging
import subprocess
import time
from typing import Iterable

import psutil
import pyautogui
from pywinauto.keyboard import send_keys

logger = logging.getLogger(__name__)


class AppTools:
    def iniciar_aplicacion_directa(self, ruta, wait_time=5):
        logger.info(f"🚀 Iniciando aplicación: {ruta}")

        try:
            wait_time = self._normalizar_tiempo(wait_time, default=5)
            proceso = subprocess.Popen(ruta)
            time.sleep(wait_time)
            return proceso

        except Exception:
            logger.error(f"❌ Error al iniciar aplicación: {ruta}", exc_info=True)
            return None

    def cerrar_proceso_remoto(self, nombre_proceso, wait_time=5) -> bool:
        wait_time = self._normalizar_tiempo(wait_time, default=5)

        try:
            logger.info(f"🧯 Buscando proceso: {nombre_proceso}")
            procesos = []

            for proc in psutil.process_iter(attrs=["pid", "name"]):
                try:
                    nombre = proc.info.get("name")

                    if nombre and nombre.lower() == str(nombre_proceso).lower():
                        procesos.append(proc)

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if not procesos:
                logger.warning(f"⚠️ No se encontró proceso activo: {nombre_proceso}")
                return False

            for proc in procesos:
                logger.info(f"🚪 Cerrando proceso: {proc.name()} PID={proc.pid}")
                proc.terminate()

                try:
                    proc.wait(timeout=wait_time)
                    logger.info(f"✅ Proceso cerrado: {proc.pid}")

                except psutil.TimeoutExpired:
                    logger.warning(f"⚠️ Proceso no respondió, forzando cierre: {proc.pid}")
                    proc.kill()
                    proc.wait()

            return True

        except Exception:
            logger.error(f"❌ Error al cerrar proceso: {nombre_proceso}", exc_info=True)
            return False

    def cerrar_aplicacion(self, nombre_ventana=None, teclas=("alt", "f4")) -> bool:
        try:
            logger.info(f"❌ Cerrando aplicación: {nombre_ventana or 'ventana actual'}")
            pyautogui.hotkey(*teclas)
            time.sleep(1)
            return True

        except Exception:
            logger.error("❌ Error al cerrar aplicación", exc_info=True)
            return False

    def esperar(self, segundos=1.0) -> bool:
        try:
            segundos = self._normalizar_tiempo(segundos, default=1)
            time.sleep(segundos)
            return True

        except Exception:
            logger.error("❌ Error en espera", exc_info=True)
            return False

    def presionar_tecla(self, tecla: str, repeticiones: int = 1) -> bool:
        try:
            repeticiones = self._normalizar_repeticiones(repeticiones)

            for _ in range(repeticiones):
                pyautogui.press(tecla)
                time.sleep(0.05)

            logger.info(f"✅ Tecla presionada: {tecla} x{repeticiones}")
            return True

        except Exception:
            logger.error(f"❌ Error al presionar tecla: {tecla}", exc_info=True)
            return False

    def presionar_combinacion(self, *teclas, repeticiones: int = 1) -> bool:
        try:
            repeticiones = self._normalizar_repeticiones(repeticiones)

            for _ in range(repeticiones):
                pyautogui.hotkey(*teclas)
                time.sleep(0.05)

            logger.info(f"✅ Combinación presionada: {teclas} x{repeticiones}")
            return True

        except Exception:
            logger.error(f"❌ Error al presionar combinación: {teclas}", exc_info=True)
            return False

    def presionar_tecla_real(self, tecla: str, repeticiones: int = 1) -> bool:
        try:
            repeticiones = self._normalizar_repeticiones(repeticiones)
            secuencia = self._convertir_tecla_real(tecla)

            for _ in range(repeticiones):
                send_keys(secuencia)
                time.sleep(0.05)

            logger.info(f"✅ Tecla real enviada: {tecla} x{repeticiones}")
            return True

        except Exception:
            logger.error(f"❌ Error al enviar tecla real: {tecla}", exc_info=True)
            return False

    def presionar_combinacion_real(self, *teclas: str, repeticiones: int = 1) -> bool:
        try:
            repeticiones = self._normalizar_repeticiones(repeticiones)
            secuencia = self._armar_combinacion_real(teclas)

            for _ in range(repeticiones):
                send_keys(secuencia)
                time.sleep(0.05)

            logger.info(f"✅ Combinación real enviada: {teclas} x{repeticiones}")
            return True

        except Exception:
            logger.error(f"❌ Error al enviar combinación real: {teclas}", exc_info=True)
            return False

    def conectar_rdp(self, *, host, user=None, password=None, wait_time=5) -> bool:
        wait_time = self._normalizar_tiempo(wait_time, default=5)

        if not host:
            raise ValueError("Host RDP no configurado.")

        try:
            if user and password:
                logger.info(f"🔐 Agregando credenciales RDP para: {host}")

                resultado = subprocess.run(
                    ["cmdkey", f"/generic:{host}", f"/user:{user}", f"/pass:{password}"],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                if resultado.returncode != 0:
                    detalle = resultado.stderr or resultado.stdout or "sin detalle"
                    raise RuntimeError(f"cmdkey falló: {detalle}")

            else:
                logger.info(f"🌐 Conectando RDP sin credenciales guardadas: {host}")

            subprocess.Popen(f"mstsc /v:{host}", shell=True)

            logger.info("✅ RDP iniciado correctamente")
            time.sleep(wait_time)
            return True

        except Exception:
            logger.error("❌ Error al iniciar conexión RDP", exc_info=True)
            raise

    def _normalizar_tiempo(self, valor, default=1) -> float:
        if valor is None:
            return float(default)

        try:
            return max(float(valor), 0)

        except (TypeError, ValueError):
            return float(default)

    def _normalizar_repeticiones(self, valor, default=1) -> int:
        if valor is None:
            return int(default)

        try:
            return max(int(valor), 1)

        except (TypeError, ValueError):
            return int(default)

    def _convertir_tecla_real(self, tecla: str) -> str:
        tecla = str(tecla).strip().lower()

        mapa = {
            "enter": "{ENTER}",
            "return": "{ENTER}",
            "tab": "{TAB}",
            "esc": "{ESC}",
            "escape": "{ESC}",
            "backspace": "{BACKSPACE}",
            "delete": "{DELETE}",
            "del": "{DELETE}",
            "insert": "{INSERT}",
            "ins": "{INSERT}",
            "home": "{HOME}",
            "end": "{END}",
            "up": "{UP}",
            "down": "{DOWN}",
            "left": "{LEFT}",
            "right": "{RIGHT}",
            "pgdn": "{PGDN}",
            "pagedown": "{PGDN}",
            "pgup": "{PGUP}",
            "pageup": "{PGUP}",
            "space": "{SPACE}",
            "f1": "{F1}",
            "f2": "{F2}",
            "f3": "{F3}",
            "f4": "{F4}",
            "f5": "{F5}",
            "f6": "{F6}",
            "f7": "{F7}",
            "f8": "{F8}",
            "f9": "{F9}",
            "f10": "{F10}",
            "f11": "{F11}",
            "f12": "{F12}",
        }

        if len(tecla) == 1:
            return tecla

        return mapa.get(tecla, f"{{{tecla.upper()}}}")

    def _armar_combinacion_real(self, teclas: Iterable[str]) -> str:
        modificadores = {
            "ctrl": "^",
            "control": "^",
            "alt": "%",
            "shift": "+",
        }

        prefijo = ""
        teclas_finales = []

        for tecla in teclas:
            tecla_normalizada = str(tecla).strip().lower()

            if tecla_normalizada in modificadores:
                prefijo += modificadores[tecla_normalizada]
            else:
                teclas_finales.append(self._convertir_tecla_real(tecla_normalizada))

        if not teclas_finales:
            raise ValueError(f"Combinación inválida: {tuple(teclas)}")

        if len(teclas_finales) == 1:
            return f"{prefijo}{teclas_finales[0]}"

        return f"{prefijo}({''.join(teclas_finales)})"

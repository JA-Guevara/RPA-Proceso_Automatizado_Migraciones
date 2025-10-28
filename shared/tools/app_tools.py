import pyautogui
import subprocess
import psutil
from pywinauto.application import Application
from pywinauto.keyboard import send_keys

from datetime import datetime
from typing import Union
import time
import logging
import gc

logger = logging.getLogger(__name__)

class AppTools:
    def iniciar_aplicacion_directa(self, ruta, wait_time=5):
        logger.info(f"🚀 Iniciando aplicación directamente: {ruta}")
        try:
            proceso = subprocess.Popen(ruta)
            time.sleep(wait_time)
            gc.collect()
            return proceso
        except Exception as e:
            logger.error(f"❌ Error al iniciar la aplicación '{ruta}': {e}")
            return None

    def cerrar_proceso_remoto(self, nombre_proceso, wait_time: int = 5) -> bool:
        try:
            logger.info(f"🧯 Buscando procesos activos: {nombre_proceso}")
            encontrados = []

            for proc in psutil.process_iter(attrs=["pid", "name", "exe", "cmdline"]):
                try:
                    if proc.info["name"].lower() == nombre_proceso.lower():
                        encontrados.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if not encontrados:
                logger.warning(f"⚠️ No se encontraron procesos '{nombre_proceso}' para cerrar.")
                return False

            for proc in encontrados:
                logger.info(f"🚪 Cerrando proceso RDP: {proc.name()} (PID: {proc.pid})")
                proc.terminate()
                try:
                    proc.wait(timeout=wait_time)
                    logger.info(f"✅ Proceso {proc.pid} cerrado.")
                except psutil.TimeoutExpired:
                    logger.warning(f"⚠️ Proceso {proc.pid} no respondió a terminate(). Forzando kill...")
                    proc.kill()
                    proc.wait()

            return True

        except Exception as e:
            logger.error(f"❌ Error al cerrar proceso '{nombre_proceso}': {e}", exc_info=True)
            return False

    def cerrar_aplicacion(self, nombre_ventana=None, teclas=["alt", "f4"]):
        logger.info(f"❌ Cerrando aplicación (ventana: {nombre_ventana or 'actual'})")
        pyautogui.hotkey(*teclas)
        time.sleep(1)
        gc.collect()

    def esperar(self, segundos: float = 1.0):
        try:
            time.sleep(segundos)
            return True
        except Exception as e:
            logger.error(f"Error en esperar: {e}", exc_info=True)
            return False

    def presionar_tecla(self, tecla: str, repeticiones: int = 1):
        try:
            for _ in range(repeticiones):
                pyautogui.press(tecla)
                logger.info(f"Tecla '{tecla}' presionada {repeticiones} veces.")
            gc.collect()
        except Exception as e:
            logger.error(f"Error al presionar tecla '{tecla}': {e}", exc_info=True)
            gc.collect()

    def presionar_combinacion(self, *teclas, repeticiones: int = 1):
        try:
            for _ in range(repeticiones):
                pyautogui.hotkey(*teclas)
                time.sleep(0.05)
                logger.info(f"Combinación {teclas} presionada {repeticiones} veces.")
            gc.collect()
        except Exception as e:
            logger.error(f"❌ Error al presionar combinación {teclas}: {e}", exc_info=True)
            gc.collect()
            
    def presionar_tecla_real(self, tecla: str, repeticiones: int = 1):
        try:
            for _ in range(repeticiones):
                send_keys("{" + tecla.upper() + "}")
                logger.info(f"✅ Tecla real '{tecla}' enviada con pywinauto.")
        except Exception as e:
            logger.error(f"❌ Error al enviar tecla real '{tecla}': {e}", exc_info=True)
            


    def conectar_rdp(self, *, host, user=None, password=None, wait_time=5):
        try:
            if user and password:
                logger.info(f"🔐 Agregando credenciales para {host} con usuario {user}")
                subprocess.run(["cmdkey", "/generic:" + host, "/user:" + user, "/pass:" + password], shell=True)
            else:
                logger.info(f"🌐 Conectando a RDP en {host} sin credenciales guardadas")

            # ✅ Este método es más compatible
            subprocess.Popen(f"mstsc /v:{host}", shell=True)

            logger.info("✅ RDP iniciado correctamente.")
            time.sleep(wait_time)
        except Exception as e:
            logger.error(f"❌ Error al iniciar conexión RDP: {e}", exc_info=True)
            
    def presionar_combinacion_real(self, *teclas: str, repeticiones: int = 1):
        try:
            special_map = {
                "ctrl": "^",
                "alt": "%",
                "shift": "+"
            }

            for _ in range(repeticiones):
                secuencia = ""
                modificadores = ""
                keys = []

                for tecla in teclas:
                    t = tecla.lower()
                    if t in special_map:
                        modificadores += special_map[t]
                    else:
                        if len(tecla) == 1 and tecla.isalnum():
                            keys.append(tecla.lower())
                        else:
                            keys.append("{" + tecla.upper() + "}") 

                if len(keys) == 1:
                    secuencia = modificadores + keys[0]
                else:
                    secuencia = modificadores + "(".join(keys) + ")"

                send_keys(secuencia)
                time.sleep(0.05)

            logger.info(f"✅ Combinación real {teclas} enviada con pywinauto {repeticiones} vez/veces.")
        except Exception as e:
            logger.error(f"❌ Error en combinación real {teclas}: {e}", exc_info=True)



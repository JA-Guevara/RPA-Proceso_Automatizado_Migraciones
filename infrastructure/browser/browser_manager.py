import os
import json
import shutil
from pathlib import Path
from playwright.async_api import async_playwright


class BrowserManager:
    def __init__(
        self,
        headless: bool = False,
        storage_file: str = "storage/cookies/storage_state.json",
        remember_session: bool = True
    ):
        self.headless = headless
        self.storage_file = storage_file
        self.remember_session = remember_session
        self.playwright = None
        self.browser = None
        self.context = None

    async def init_browser(self):
        """Inicializa Playwright y lanza Chromium si aún no está activo."""
        if not self.playwright:
            self.playwright = await async_playwright().start()
        if not self.browser:
            self.browser = await self.playwright.chromium.launch(headless=self.headless)
        return self.browser

    async def create_browser_context(self):
        """Crea un nuevo contexto con o sin cookies guardadas."""
        await self.init_browser()

        # Asegurar existencia de carpeta de storage
        storage_dir = os.path.dirname(self.storage_file)
        os.makedirs(storage_dir, exist_ok=True)

        if self.remember_session and os.path.exists(self.storage_file):
            try:
                print(f"🧠 Cargando estado de sesión desde {self.storage_file}")
                self.context = await self.browser.new_context(
                    storage_state=self.storage_file,
                    accept_downloads=True
                )
            except Exception as e:
                print(f"⚠️ Error cargando storage_state.json, creando contexto limpio: {e}")
                self.context = await self.browser.new_context(accept_downloads=True)
        else:
            print("🆕 Iniciando contexto limpio (sin cookies guardadas)")
            self.context = await self.browser.new_context(accept_downloads=True)

        return self.context

    async def get_new_page(self):
        """Devuelve una nueva página lista para usarse."""
        if not self.context:
            await self.create_browser_context()
        return await self.context.new_page()

    async def save_storage(self):
        """Guarda cookies/estado de sesión."""
        if self.context and self.remember_session:
            try:
                os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)
                await self.context.storage_state(path=self.storage_file)
                print(f"💾 Estado de sesión guardado en {self.storage_file}")
            except Exception as e:
                print(f"⚠️ Error al guardar storage_state.json: {e}")

    async def close_browser(self, clear_storage: bool = False):
        """Cierra navegador, contexto y opcionalmente limpia sesión."""
        try:
            if self.context:
                await self.save_storage()
                await self.context.close()
                print("✔ Contexto cerrado.")

            if self.browser:
                await self.browser.close()
                self.browser = None
                print("✔ Navegador cerrado.")

            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
                print("✔ Playwright detenido.")

            if clear_storage and os.path.exists(self.storage_file):
                os.remove(self.storage_file)
                print("🧹 Storage eliminado manualmente.")

        except Exception as e:
            print(f"⚠️ Error al cerrar navegador: {e}")

    async def clear_temp_files(self):
        """Elimina carpetas temporales generadas por el usuario o playwright."""
        temp_folder = "user_data"
        if os.path.exists(temp_folder):
            shutil.rmtree(temp_folder, ignore_errors=True)
            print("🧹 Carpeta temporal eliminada.")

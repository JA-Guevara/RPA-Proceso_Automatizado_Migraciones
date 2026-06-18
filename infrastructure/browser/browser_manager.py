import json
import logging
import shutil
from hashlib import md5
from pathlib import Path

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


class BrowserManager:
    def __init__(
        self,
        headless: bool = False,
        storage_file: str = "storage/cookies/storage_state.json",
        remember_session: bool = True,
        launch_args: list | None = None,
        ignore_https_errors: bool = False,
        permissions: list[str] | None = None,
        permission_origin: str | None = None,
    ):
        self.headless = headless
        self.storage_file = Path(storage_file)
        self.remember_session = remember_session
        self.launch_args = launch_args or []
        self.ignore_https_errors = ignore_https_errors

        self._playwright = None
        self._browser = None
        self._context = None
        self.permissions = permissions or []
        self.permission_origin = permission_origin

    async def init_browser(self):
        if self._playwright is None:
            self._playwright = await async_playwright().start()

        if self._browser is None:
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=self.launch_args,
            )

        return self._browser

    async def create_browser_context(self, no_viewport: bool = False):
        if self._context:
            return self._context

        await self.init_browser()
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)

        opciones = {
            "accept_downloads": True,
            "ignore_https_errors": self.ignore_https_errors,
        }

        if no_viewport:
            opciones["no_viewport"] = True

        if self.permissions:
            opciones["permissions"] = self.permissions

        try:
            if self.remember_session and self.storage_file.exists():
                logger.info(f"🧠 Cargando sesión desde {self.storage_file}")
                self._context = await self._browser.new_context(
                    storage_state=str(self.storage_file),
                    **opciones,
                )
            else:
                logger.info("🆕 Contexto limpio")
                self._context = await self._browser.new_context(**opciones)

        except Exception as e:
            logger.warning(f"⚠ Error cargando sesión, creando contexto limpio: {e}")
            self._context = await self._browser.new_context(**opciones)

        if self.permissions:
            if self.permission_origin:
                await self._context.grant_permissions(
                    self.permissions,
                    origin=self.permission_origin,
                )
            else:
                await self._context.grant_permissions(self.permissions)

            logger.info(f"🔐 Permisos navegador concedidos: {self.permissions}")

        return self._context

    async def get_new_page(self):
        if self._context is None:
            await self.create_browser_context()

        return await self._context.new_page()

    async def poner_pantalla_completa(self, page):
        if self.headless:
            logger.info("ℹ️ Fullscreen omitido porque el navegador está en headless")
            return

        if self._context is None:
            logger.warning("⚠️ No existe contexto para aplicar fullscreen")
            return

        cdp = await self._context.new_cdp_session(page)

        try:
            info = await cdp.send("Browser.getWindowForTarget")
            window_id = info["windowId"]

            try:
                await cdp.send(
                    "Browser.setWindowBounds",
                    {
                        "windowId": window_id,
                        "bounds": {"windowState": "fullscreen"},
                    },
                )
            except Exception:
                await cdp.send(
                    "Browser.setWindowBounds",
                    {
                        "windowId": window_id,
                        "bounds": {"windowState": "normal"},
                    },
                )

                await cdp.send(
                    "Browser.setWindowBounds",
                    {
                        "windowId": window_id,
                        "bounds": {"windowState": "fullscreen"},
                    },
                )

            logger.info("🖥️ Navegador en pantalla completa vía CDP")

        finally:
            await cdp.detach()

    async def save_storage(self):
        if not self._context or not self.remember_session:
            return

        try:
            new_state = await self._context.storage_state()
            new_hash = md5(json.dumps(new_state, sort_keys=True).encode()).hexdigest()
            old_hash = self._get_storage_hash()

            if new_hash != old_hash:
                await self._context.storage_state(path=str(self.storage_file))
                logger.info(f"💾 Sesión guardada en {self.storage_file}")
            else:
                logger.info("ℹ Sin cambios en sesión")

        except Exception as e:
            logger.error(f"⚠ Error guardando sesión: {e}")

    def _get_storage_hash(self):
        if not self.storage_file.exists():
            return None

        try:
            old_state = json.loads(self.storage_file.read_text(encoding="utf-8"))
            return md5(json.dumps(old_state, sort_keys=True).encode()).hexdigest()
        except Exception:
            return None

    async def close_browser(self, clear_storage: bool = False):
        try:
            if self._context and self.remember_session:
                await self.save_storage()

            if self._context:
                await self._context.close()
                self._context = None

            if self._browser:
                await self._browser.close()
                self._browser = None

        finally:
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None

            if clear_storage and self.storage_file.exists():
                self.storage_file.unlink()
                logger.info("🧹 Archivo de sesión eliminado")

    async def clear_temp_files(self):
        temp_folder = Path("user_data")

        if temp_folder.exists():
            shutil.rmtree(temp_folder, ignore_errors=True)
            logger.info("🧹 Carpeta temporal eliminada")
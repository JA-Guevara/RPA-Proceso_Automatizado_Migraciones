import asyncio
import logging
import threading
from typing import Awaitable

from infrastructure.browser.browser_manager import BrowserManager

logger = logging.getLogger(__name__)

VIDA_REGISTRO = "registro"
VIDA_SESION = "sesion"


class BrowserSession:
    def __init__(
        self,
        vida: str = VIDA_REGISTRO,
        launch_args: list | None = None,
        headless: bool = False,
        storage_file: str = "storage/cookies/storage_state.json",
        remember_session: bool = True,
        no_viewport: bool = False,
        ignore_https_errors: bool = False,
        fullscreen: bool = False,
        permissions: list | None = None,
        permission_origin: str | None = None,   
    ):
        if vida not in (VIDA_REGISTRO, VIDA_SESION):
            raise ValueError(f"vida desconocida: {vida!r} (use 'registro' o 'sesion')")

        self.vida = vida
        self.launch_args = launch_args or []
        self.headless = headless
        self.storage_file = storage_file
        self.remember_session = remember_session
        self.no_viewport = no_viewport
        self.ignore_https_errors = ignore_https_errors
        self.fullscreen = fullscreen

        self.page = None
        self._browser_manager: BrowserManager | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._abierto = False
        self.permissions = permissions
        self.permission_origin = permission_origin

    def abrir(self) -> "BrowserSession":
        if self._abierto:
            return self

        if self.vida == VIDA_SESION:
            self._arrancar_loop_en_hilo()
        else:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

        self.run(self._abrir_async())
        self._abierto = True
        logger.info(f"🌐 BrowserSession abierta (vida={self.vida})")
        return self

    def run(self, coro: Awaitable):
        if self._loop is None:
            raise RuntimeError("BrowserSession no está abierta. Llame a abrir() primero.")

        if self.vida == VIDA_SESION:
            futuro = asyncio.run_coroutine_threadsafe(coro, self._loop)
            return futuro.result()

        return self._loop.run_until_complete(coro)

    def cerrar(self, clear_storage: bool = False):
        if not self._abierto:
            return

        try:
            self.run(self._cerrar_async(clear_storage))
        except Exception as e:
            logger.warning(f"⚠️ Error cerrando navegador: {e}")
        finally:
            self._cerrar_loop()
            self.page = None
            self._loop = None
            self._thread = None
            self._abierto = False
            logger.info("🧹 BrowserSession cerrada")

    def esta_activa(self) -> bool:
        return self._abierto and self.page is not None and not self.page.is_closed()

    def __enter__(self) -> "BrowserSession":
        return self.abrir()

    def __exit__(self, exc_type, exc, tb):
        self.cerrar()
        return False

    def _arrancar_loop_en_hilo(self):
        self._loop = asyncio.new_event_loop()
        listo = threading.Event()

        def runner():
            asyncio.set_event_loop(self._loop)
            self._loop.call_soon(listo.set)
            self._loop.run_forever()

            try:
                self._loop.run_until_complete(self._loop.shutdown_asyncgens())
            finally:
                self._loop.close()

        self._thread = threading.Thread(
            target=runner,
            name="BrowserSession-loop",
            daemon=True,
        )
        self._thread.start()
        listo.wait()

    def _cerrar_loop(self):
        if self.vida == VIDA_SESION and self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)

            if self._thread:
                self._thread.join(timeout=10)

            return

        if self._loop is not None:
            self._loop.close()
            asyncio.set_event_loop(None)

    async def _abrir_async(self):
        self._browser_manager = BrowserManager(
            headless=self.headless,
            storage_file=self.storage_file,
            remember_session=self.remember_session,
            launch_args=self.launch_args,
            ignore_https_errors=self.ignore_https_errors,
            permissions=self.permissions,
            permission_origin=self.permission_origin,
        )

        await self._browser_manager.create_browser_context(
            no_viewport=self.no_viewport,
        )

        self.page = await self._browser_manager.get_new_page()

        if self.fullscreen:
            await self._browser_manager.poner_pantalla_completa(self.page)

        return self.page

    async def _cerrar_async(self, clear_storage: bool):
        if self._browser_manager:
            await self._browser_manager.close_browser(clear_storage=clear_storage)
            self._browser_manager = None
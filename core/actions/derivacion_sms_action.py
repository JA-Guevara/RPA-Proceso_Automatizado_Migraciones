from core.action_base.web_action_base import WebActionBase
from config.selectors import WebSelectors
from infrastructure.browser.browser_session import BrowserSession


class DerivacionSmsAction(WebActionBase):
    S = WebSelectors.SmsBajas

    def __init__(self,variables_base: dict,contexto: dict | None = None,):
        super().__init__(variables_base, contexto)

    def ejecutar(self) -> bool:
        self.hora_inicio()
        self.logger.info("🌐 Iniciando DerivacionSmsAction")

        try:
            with BrowserSession(vida="registro") as web:
                web.run(self._flujo(web))

            self.contexto["notificacion_baja_rpa"] = True
            self.logger.info("✅ Derivación SMS completada")
            return True

        except Exception as e:
            try:
                self.manejar_excepcion(e)
            except Exception:
                pass
            raise
        finally:
            self.hora_fin()

    async def _flujo(self, web: BrowserSession):
        page = web.page

        await self._login(page)
        await self._derivar(page)
        await self._logout(page)

    async def _login(self, page):
        url = self.var("sms_url")
        usuario = self.var("sms_user")
        password = self.var("sms_password")

        if not url:
            raise ValueError("sms_url no configurado")
        if not usuario:
            raise ValueError("sms_user no configurado")
        if not password:
            raise ValueError("sms_password no configurado")
        self.logger.info("🔐 Iniciando sesión SMS")

        await page.goto(url,timeout=60_000,wait_until="networkidle",)         
        await page.locator(self.S.USERNAME.locator).fill(usuario)
        await page.locator(self.S.PASSWORD.locator).fill(password)
        await page.locator(self.S.LOGIN_BUTTON.locator).click()

        await page.wait_for_load_state("networkidle")

    async def _derivar(self, page):
        nro_linea = self.var("nro_linea")

        if not nro_linea:
            raise ValueError("Falta 'nro_linea' en el contexto.")

        self.logger.info(f"📱 Procesando derivación para línea {nro_linea}")

        await page.locator(self.S.DERIVACIONES_MENU.locator).click()
        await page.locator(self.S.OPCION_DERIVAR_CONSULTA.locator).click()
        await page.locator(self.S.NRO_CUENTA.locator).fill(str(nro_linea))
        await page.locator(self.S.TIPO_PLANTILLA_MENU.locator).select_option(label="Bajas Móvil Post Pago")
        await page.locator(self.S.PLANTILLA_SELECT.locator).select_option(value=self.S.PLANTILLA_CONFIRMACION_BAJA)

        await page.locator(self.S.BTN_AGREGAR.locator).click()
        await page.locator(self.S.BTN_ENVIAR.locator).click()

        await page.wait_for_load_state("networkidle")

        self.logger.info("✅ Derivación enviada")

    async def _logout(self, page):
        self.logger.info("🚪 Cerrando sesión SMS")
        await page.locator(self.S.BTN_LOGOUT.locator).click()
        await page.wait_for_load_state("networkidle")
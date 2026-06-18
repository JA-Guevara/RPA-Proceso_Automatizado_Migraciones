from core.action_base.web_action_base import WebActionBase
from config.selectors import WebSelectors
from infrastructure.remote_desktop.conexion_escritorio import ConexionEscritorio


class LoginEscritorioWebAction(WebActionBase):
    S = WebSelectors.Conexion

    def __init__(self,variables_base: dict,contexto: dict | None = None,):
        super().__init__(variables_base, contexto)
        
    def ejecutar(self) -> bool:
        self.hora_inicio()
        self.logger.info("🌐 Iniciando LoginEscritorioWebAction")

        try:
            conexion = ConexionEscritorio.instancia()
            if not conexion.page:
                raise RuntimeError("No existe una sesión web activa.")

            page = conexion.page
            conexion.run(self._flujo(page))
            self.logger.info("✅ Login escritorio web completado")
            return True

        except Exception as e:
            try:
                self.manejar_excepcion(e)
            except Exception:
                pass
            raise
        finally:

            self.hora_fin()
            
    async def _flujo(self, page):
        await self._login_portal(page)
        await self._validar_inicio(page)
    
    async def _login_portal(self, page):
        self.logger.info("🔐 Login portal remoto")
        
        url = self.var("guacamole_url")
        usuario = self.var("guacamole_user")
        password = self.var("guacamole_password")
        
        await page.goto(url,timeout=60_000,wait_until="domcontentloaded",)   
        await page.locator(self.S.USERNAME.locator).wait_for(state="visible",timeout=30_000,)
        await page.locator(self.S.USERNAME.locator).fill(usuario)
        await page.locator(self.S.PASSWORD.locator).wait_for(state="visible",timeout=30_000,)
        await page.locator(self.S.PASSWORD.locator).fill(password)
        await page.locator(self.S.LOGIN_BUTTON.locator).click()
        await page.locator(self.S.CONTINUAR_BUTTON.locator).wait_for(state="visible",timeout=30_000,)
        await page.locator(self.S.CONTINUAR_BUTTON.locator).click()
        await page.wait_for_timeout(5000)
        
    async def _validar_inicio(self, page):
        self.logger.info("✅ Validando escritorio")
        pass

    
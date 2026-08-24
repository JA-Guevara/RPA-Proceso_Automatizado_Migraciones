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

        # Hook que ya existia vacio y ya se llamaba en el momento exacto:
        # despues del login del portal, antes de esperar_ancla() y del flujo
        # visual. Aca se instala el interceptor de portapapeles.
        #
        # IMPORTANTE: este metodo ya corre DENTRO de conexion.run(), es decir
        # dentro del event loop de la sesion. Por eso se hace
        # `await page.evaluate(...)` directo y NO se usa clipboard_service.
        # Llamar al servicio aca reentraria en conexion.run() sobre el mismo
        # loop y el proceso se cuelga.
        #
        # Regla: conexion.run() solo desde codigo sincronico. Dentro de una
        # corrutina, await page.evaluate() directo.
        from shared.tools.clipboard.tap_js import TAP_INSTALAR

        try:
            salud = await page.evaluate(TAP_INSTALAR) or {}
        except Exception as e:
            self.logger.error("❌ No se pudo evaluar el instalador del tap: %s", e)
            salud = {"ok": False, "motivo": f"evaluate_error: {e}"}

        self.contexto["clipboard_tap_ok"] = bool(salud.get("ok"))
        self.contexto["clipboard_tap_estado"] = salud.get("estadoCliente")
        self.contexto["clipboard_tap_detalle"] = salud

        self.logger.info(
            "📋 Interceptor de portapapeles: ok=%s | motivo=%s | cliente=%s | "
            "tunel=%s | estado=%s | ya_estaba=%s",
            salud.get("ok"), salud.get("motivo"), salud.get("clientPath"),
            salud.get("tunnelHook"), salud.get("estadoCliente"), salud.get("yaEstaba"),
        )

        if not salud.get("ok"):
            raise RuntimeError(
                f"No se pudo instalar el interceptor de portapapeles: "
                f"{salud.get('motivo', 'desconocido')}"
            )

    
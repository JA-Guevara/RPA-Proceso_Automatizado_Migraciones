import logging
from typing import Dict, Any
from playwright.async_api import Page


class WebExecutor:
    def __init__(
        self,
        page: Page = None,
        selectors: dict = None,
        variables_base: dict = None,
        contexto: dict = None,
        browser_manager=None,
        flow: dict = None
    ):
        self.page = page
        self.selectors = selectors or {}
        self.variables_base = variables_base or {}   # 🔹 Config o credenciales fijas
        self.contexto = contexto or {}               # 🔹 Datos dinámicos en ejecución
        self.browser_manager = browser_manager
        self.flow_data = flow or {}

        # Vista combinada solo para evaluación de variables $nombre
        self.variables = {**self.variables_base, **self.contexto}

        self.logger = logging.getLogger(__name__)

        # Logs iniciales
        self.logger.info(f"📙️ Variables base (env/config): {self.variables_base}")
        self.logger.info(f"📦 Contexto inicial: {self.contexto}")

    def resolve_variable(self, value: Any):
        """Reemplaza variables que empiecen con $ con sus valores reales."""
        if isinstance(value, str) and value.startswith("$"):
            key = value[1:]
            resolved = self.contexto.get(key, self.variables_base.get(key))
            if resolved is None:
                self.logger.warning(f"⚠️ Variable '{key}' no encontrada en contexto ni variables base.")
                return ""
            return str(resolved)
        return value

    def _resolver_selector(self, target: str):
        """Busca el selector definido en el archivo de selectores."""
        if not target:
            return None
        if "." in target:
            grupo, campo = target.split(".")
            return self.selectors.get(grupo, {}).get(campo)
        return self.selectors.get(target)

    async def ensure_page(self):
        """Garantiza que exista una página activa."""
        if not self.page:
            context = await self.browser_manager.create_browser_context()
            self.page = await context.new_page()
        return self.page

    async def ejecutar_bloque(self, bloque: str):
        """Ejecuta un bloque del flujo (.json)."""
        await self.ensure_page()
        pasos = self.flow_data.get(bloque, [])
        if not isinstance(pasos, list):
            self.logger.error(f"❌ El bloque '{bloque}' no contiene pasos válidos.")
            return

        self.logger.info(f"🚀 Ejecutando bloque: {bloque} ({len(pasos)} pasos)")
        for paso in pasos:
            paso = {k: self.resolve_variable(v) for k, v in paso.items()}
            action = paso.get("action")

            try:
                handler = getattr(self, f"_action_{action}", None)
                if handler:
                    await handler(paso)
                else:
                    self.logger.warning(f"⚠️ Acción desconocida: {action}")
            except Exception as e:
                self.logger.error(f"❌ Error ejecutando acción '{action}': {e}", exc_info=True)

        # 💾 Guardar sesión solo si hubo cambio
        if getattr(self.browser_manager, "session_changed", False):
            await self.browser_manager.save_storage()
            self.browser_manager.session_changed = False


    async def _action_goto(self, paso):
        url = paso.get("value")
        self.logger.info(f"🌍 Navegando a {url}")
        await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")

    async def _action_click(self, paso):
        selector = self._resolver_selector(paso.get("target"))
        self.logger.info(f"🖱️ Click en {selector}")
        try:
            await self.page.wait_for_selector(selector, timeout=10000)
            await self.page.click(selector, force=True)
            self.logger.info(f"✅ Click realizado en {selector}")
        except Exception as e:
            self.logger.warning(f"⚠️ Intentando click forzado vía JS: {e}")
            await self.page.evaluate(f'''
                const el = document.querySelector("{selector}");
                if (el) el.click();
            ''')

    async def _action_fill(self, paso):
        selector = self._resolver_selector(paso.get("target"))
        valor = paso.get("value", "")
        self.logger.info(f"📝 Llenando {selector} con '{valor}'")
        try:
            elemento = await self.page.wait_for_selector(selector, state="visible", timeout=10000)
            await elemento.scroll_into_view_if_needed()
            await elemento.fill("")
            await elemento.fill(valor)
            self.logger.info(f"✅ Campo llenado: {selector}")
        except Exception as e:
            self.logger.error(f"❌ Error al llenar campo {selector}: {e}")

    async def _action_type(self, paso):
        selector = self._resolver_selector(paso.get("target"))
        valor = paso.get("value", "")
        self.logger.info(f"⌨️ Escribiendo (type) en {selector}: {valor}")
        await self.page.click(selector)
        await self.page.fill(selector, "")
        await self.page.type(selector, valor, delay=100)

    async def _action_wait_for(self, paso):
        selector = self._resolver_selector(paso.get("target"))
        self.logger.info(f"⏳ Esperando selector {selector}")
        await self.page.wait_for_selector(selector)

    async def _action_wait_time(self, paso):
        tiempo = int(paso.get("value", 1000))
        self.logger.info(f"⏳ Esperando {tiempo}ms")
        await self.page.wait_for_timeout(tiempo)

    async def _action_keyboard_press(self, paso):
        tecla = paso.get("value")
        await self.page.keyboard.press(tecla)
        self.logger.info(f"⌨️ Tecla presionada: {tecla}")

    async def _action_seleccionar_opcion_dropdown(self, paso):
        selector = self._resolver_selector(paso.get("target"))
        valor = paso.get("value")

        self.logger.info(f"📂 Intentando seleccionar opción '{valor}' en dropdown: {selector}")
        try:
            await self.page.wait_for_selector(selector, timeout=10000)
            elemento = await self.page.query_selector(selector)
            tag_name = (await (await elemento.get_property("tagName")).json_value()).lower()

            if tag_name == "select":
                await self.page.select_option(selector, label=valor)
                self.logger.info(f"✅ Opción '{valor}' seleccionada en <select>: {selector}")
                return

            self.logger.info(f"📂 Elemento no es <select>. Intentando click y búsqueda por texto.")
            await self.page.click(selector, force=True)

            estrategias = [
                f"//div[contains(@class, 'rich-menu-item')]//a[contains(text(), '{valor}')]",
                f"//a[contains(text(), '{valor}')]",
                f"//span[contains(text(), '{valor}')]"
            ]

            for opcion_xpath in estrategias:
                try:
                    locator = self.page.locator(f"xpath={opcion_xpath}").first
                    await locator.wait_for(state="visible", timeout=3000)
                    await locator.click()
                    self.logger.info(f"✅ Opción '{valor}' seleccionada con XPath: {opcion_xpath}")
                    return
                except Exception:
                    continue

            self.logger.error(f"❌ No se encontró la opción '{valor}' para selector visual {selector}")

        except Exception as e:
            self.logger.error(f"❌ Error inesperado al seleccionar '{valor}' en '{selector}': {e}")

    async def close(self, clear_storage=False):
        """Cierra navegador y contexto ordenadamente."""
        self.logger.info("🧩 Cerrando navegador y guardando estado...")
        try:
            await self.browser_manager.close_browser(clear_storage=clear_storage)
        except Exception as e:
            self.logger.error(f"⚠️ Error al cerrar navegador: {e}")

import asyncio
from core.action_base.action_base import ActionBase

class DerivacionSmsAction(ActionBase):
    def __init__(self, variables_base: dict, contexto: dict = None, flow_name: str = "derivacion_sms"):
        super().__init__(variables_base, contexto or {}, flow_name=flow_name, executor_type="web")

    def ejecutar(self) -> bool:
        return asyncio.run(self._ejecutar_async())

    async def _ejecutar_async(self) -> bool:
        self.hora_inicio()
        self.logger.info("🌐 Iniciando DerivacionSMSAction...")

        try:
            # 🧠 Cargar contexto/navegador
            await self.browser_manager.create_browser_context()
            page = await self.browser_manager.get_new_page()
            self.executor.page = page

            # 🔹 Ejecutar sub-flujos definidos en el flow.json
            for bloque in ["login", "derivacion", "logout"]:
                self.logger.info(f"▶️ Ejecutando sub-flow: {bloque}")
                await self.executor.ejecutar_bloque(bloque)

            self.logger.info("✅ DerivacionSMSAction completada.")
            self.contexto["notificacion_baja_rpa"] = True
            return True

        except Exception as e:
            try:
                self.manejar_excepcion(e)
            except Exception:
                pass
            raise

        finally:
            self.hora_fin()
            # 💾 Guardar sesión y cerrar navegador de forma segura
            try:
                await self.executor.close(clear_storage=False)
            except Exception as e:
                self.logger.warning(f"⚠️ Error cerrando navegador: {e}")

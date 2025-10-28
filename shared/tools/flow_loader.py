from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

class FlowLoader:
    @staticmethod
    def load(flow_name: str) -> dict | None:
        # Definimos la ruta dentro del método estático
        folder_path = Path(__file__).resolve().parent.parent.parent / "flows"
        file_path = folder_path / f"{flow_name}.json"

        if not file_path.exists():
            logger.error(f"❌ Archivo de flujo no encontrado: {file_path}")
            return None

        try:
            with file_path.open("r", encoding="utf-8") as file:
                flow_data = json.load(file)
                logger.info(f"📄 Flujo cargado correctamente: {flow_name}")
                return flow_data
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error al decodificar JSON en {file_path}: {e}")
            return None

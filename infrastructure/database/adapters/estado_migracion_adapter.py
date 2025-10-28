from sqlalchemy import text
from infrastructure.database.database import SessionLocal
from config.config import EnvConfig

class EstadoSQLAdapter:
    def __init__(self):
        self.tabla = EnvConfig.BOT_TABLA_ESTADOS

    def obtener_id_por_nombre(self, nombre_estado: str) -> int | None:
        try:
            with SessionLocal() as db:
                sql = text(f"""
                    SELECT id
                    FROM {self.tabla} WITH (NOLOCK)
                    WHERE nombre = :nombre
                """)
                return db.execute(sql, {"nombre": nombre_estado}).scalar()
        except Exception as e:
            print(f"❌ Error buscando estado '{nombre_estado}' en {self.tabla}: {e}")
            return None

    def obtener_nombre_por_id(self, id_estado: int) -> str | None:
        try:
            with SessionLocal() as db:
                sql = text(f"""
                    SELECT nombre
                    FROM {self.tabla} WITH (NOLOCK)
                    WHERE id = :id_estado
                """)
                return db.execute(sql, {"id_estado": id_estado}).scalar()
        except Exception as e:
            print(f"❌ Error buscando nombre de estado con ID {id_estado}: {e}")
            return None

    def actualizar_estado_migracion(self, contexto: dict) -> bool:
        
        baja_realizada = contexto.get("baja_realizada")
        id_migracion = contexto.get("id_migracion")

        try:
            estado_id = self.obtener_id_por_nombre(baja_realizada)
            if not estado_id:
                print(f"❌ Estado '{baja_realizada}' no encontrado en catálogo")
                return False

            with SessionLocal() as db:
                sql = text("""
                    UPDATE migracion
                    SET id_estado = :estado
                    WHERE id = :id_migracion
                """)
                db.execute(sql, {"estado": estado_id, "id_migracion": id_migracion})
                db.commit()
                print(f"✅ Estado actualizado a '{baja_realizada}' (ID={estado_id}) para migración {id_migracion}")
                return True
        except Exception as e:
            print(f"❌ Error actualizando estado desde contexto: {e}")
            return False

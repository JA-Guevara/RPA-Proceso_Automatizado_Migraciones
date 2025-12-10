from sqlalchemy import text
from infrastructure.database.database import SessionLocal
from config.config import EnvConfig

class PlanesSQLAdapter:
    def __init__(self):
        self.tabla = EnvConfig.BOT_TABLA_PLANES 

    def es_plan_valido(self, id_tipo_lista, nombre_plan: str, tipo: str) -> bool:
        try:
            with SessionLocal() as db:
                sql = text(f"""
                    SELECT TOP (1) 1
                    FROM {self.tabla} WITH (NOLOCK)
                    WHERE id_tipo_lista = TRY_CONVERT(INT, :id_tipo_lista)
                      AND tipo = :tipo
                      AND (
                            nombre_plan = :nombre_plan
                         OR nombre_plan = REPLACE(:nombre_plan, '  ', ' ')
                         OR nombre_plan = REPLACE(REPLACE(:nombre_plan, '  ', ' '), '  ', ' ')
                      )
                """)

                params = {
                    "id_tipo_lista": id_tipo_lista,
                    "nombre_plan": nombre_plan.strip() if nombre_plan else "",
                    "tipo": tipo.strip() if tipo else ""
                }

                row = db.execute(sql, params).first()
                return row is not None

        except Exception as e:
            print(
                f"❌ Error validando plan '{nombre_plan}' "
                f"(tipo_lista={id_tipo_lista}, tipo={tipo}): {e}"
            )
            return False

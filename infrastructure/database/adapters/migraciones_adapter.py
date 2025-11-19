from sqlalchemy import text
from infrastructure.database.database import SessionLocal
from config.config import EnvConfig


class MigracionesSQLAdapter:

    def __init__(self):
        self.tabla = EnvConfig.BOT_TABLA_MIGRACION_DETALLE

    MAPEO = {
        "id_migracion": "id_migracion",
        "fecha_hora_inicio_migracionactions": "fecha_hora_inicio",
        "fecha_hora_fin_migracionactions": "fecha_hora_fin",
        "plan_actual_rpa": "plan_consumo_anterior_rpa",
        "plan_asignado_rpa": "plan_consumo_asignado_rpa",
        "codigo_plan_consumo_asignados_rpa": "codigo_plan_consumo_asignados_rpa",
        "estado_cuenta_anterior_rpa": "estado_cuenta_anterior_rpa",
        "estado_cuenta_posterior_rpa": "estado_cuenta_posterior_rpa",
        "forma_pago_anterior_rpa": "forma_pago_anterior_rpa",
        "forma_pago_posterior_rpa": "forma_pago_posterior_rpa",
        "situacion_cuenta_anterior_rpa": "situacion_cuenta_anterior_rpa",
        "situacion_cuenta_posterior_rpa": "situacion_cuenta_posterior_rpa",
        "servicios_asignados_rpa": "servicios_asignados_rpa",
        "servicios_eliminados_rpa": "servicios_eliminados_rpa",
        "facturas_pendientes_rpa": "facturas_pendientes_rpa",
        "deuda_pendiente": "deuda_pendiente",
        "billetera_prepago_rpa": "billetera_prepago_rpa",
        "antiguedad_meses_rpa": "antiguedad_meses_rpa",
        "notificacion_baja_rpa": "notificacion_baja",
        "fecha_hora_fin_derivacionsmsaction": "fecha_hora_notificacion_baja_rpa",
        "fecha_hora_observacion_rpa": "fecha_hora_observacion_rpa",
        "mensaje_observacion_rpa": "mensaje_observacion_rpa",
    }

    def registrar_detalle(self, contexto: dict):
        try:
            with SessionLocal() as db:
                id_migracion = contexto.get("id_migracion")
                if not id_migracion:
                    print("⚠️ No se encontró 'id_migracion' en el contexto. No se puede registrar.")
                    return

                check_sql = text(f"SELECT COUNT(1) FROM {self.tabla} WHERE id_migracion = :id_migracion")
                existe = db.execute(check_sql, {"id_migracion": id_migracion}).scalar()

                params = {}
                for ctx_key, col_sql in self.MAPEO.items():
                    valor = contexto.get(ctx_key, None)
                    if isinstance(valor, str):
                        valor = valor.strip()
                        if valor == "" or valor.upper().startswith("ERROR_"):
                            valor = None
                    params[col_sql] = valor

                params["id_migracion"] = id_migracion

                if existe:
                    set_clauses_list = []
                    for ctx_key, col_sql in self.MAPEO.items():
                        if col_sql == "id_migracion":
                            continue
                        if params[col_sql] is not None:
                            set_clauses_list.append(f"{col_sql} = :{col_sql}")

                    if set_clauses_list:
                        set_clauses = ", ".join(set_clauses_list)
                        sql = text(f"""
                            UPDATE {self.tabla}
                            SET {set_clauses}
                            WHERE id_migracion = :id_migracion
                        """)
                        db.execute(sql, params)
                        db.commit()
                        print(f"🌀 Registro actualizado para id_migracion={id_migracion} en {self.tabla}")
                    else:
                        print(f"ℹ️ No se actualizó nada para id_migracion={id_migracion}")

                else:
                    columnas_sql = ", ".join(self.MAPEO.values())
                    valores_sql = ", ".join([f":{col}" for col in self.MAPEO.values()])
                    sql = text(f"""
                        INSERT INTO {self.tabla} ({columnas_sql})
                        VALUES ({valores_sql})
                    """)
                    db.execute(sql, params)
                    db.commit()
                    print(f"✅ Registro insertado correctamente para id_migracion={id_migracion} en {self.tabla}")

        except Exception as e:
            print(f"❌ Error al registrar detalle migración en {self.tabla}: {e}")

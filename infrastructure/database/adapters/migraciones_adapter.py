from sqlalchemy import text
from infrastructure.database.database import SessionLocal
from config.config import EnvConfig


class MigracionesSQLAdapter:

    def __init__(self):
        # Ejemplo: Bajas_Moviles.dbo.migracion_detalle
        self.tabla = EnvConfig.BOT_TABLA_MIGRACION_DETALLE

    # === Mapeo entre nombres del contexto y columnas SQL ===
    MAPEO = {
        # --- Identificadores base ---
        "id_migracion": "id_migracion",

        # --- Tiempos principales ---
        "fecha_hora_inicio_migracionactions": "fecha_hora_inicio",
        "fecha_hora_fin_migracionactions": "fecha_hora_fin",

        # --- Planes y consumo ---
        "plan_actual_rpa": "plan_consumo_anterior_rpa",
        "plan_asignado_rpa": "plan_consumo_asignado_rpa",
        "codigo_plan_consumo_asignados_rpa": "codigo_plan_consumo_asignados_rpa",

        # --- Estado de cuenta ---
        "estado_cuenta_anterior_rpa": "estado_cuenta_anterior_rpa",
        "estado_cuenta_posterior_rpa": "estado_cuenta_posterior_rpa",

        # --- Forma de pago ---
        "forma_pago_anterior_rpa": "forma_pago_anterior_rpa",
        "forma_pago_posterior_rpa": "forma_pago_posterior_rpa",

        # --- Situación controlada ---
        "situacion_cuenta_anterior_rpa": "situacion_cuenta_anterior_rpa",
        "situacion_cuenta_posterior_rpa": "situacion_cuenta_posterior_rpa",

        # --- Servicios y validaciones ---
        "servicios_asignados_rpa": "servicios_asignados_rpa",
        "servicios_eliminados_rpa": "servicios_eliminados_rpa",

        # --- Facturación y deuda ---
        "facturas_pendientes_rpa": "facturas_pendientes_rpa",
        "deuda_pendiente": "deuda_pendiente",

        # --- Billetera / saldo prepago ---
        "billetera_prepago_rpa": "billetera_prepago_rpa",
        "antiguedad_meses_rpa": "antiguedad_meses_rpa",

        # --- Notificaciones ---
        "notificacion_baja_rpa": "notificacion_baja",
        "fecha_hora_fin_derivacionsmsaction": "fecha_hora_notificacion_baja_rpa",

        # --- Observaciones ---
        "fecha_hora_observacion_rpa": "fecha_hora_observacion_rpa",
        "mensaje_observacion_rpa": "mensaje_observacion_rpa",
    }

    # ======================================================
    # MÉTODO PRINCIPAL: REGISTRAR O ACTUALIZAR DETALLE
    # ======================================================
    def registrar_detalle(self, contexto: dict):
        try:
            with SessionLocal() as db:
                id_migracion = contexto.get("id_migracion")

                if not id_migracion:
                    print("⚠️ No se encontró 'id_migracion' en el contexto. No se puede registrar.")
                    return

                # --- Verificar existencia previa ---
                check_sql = text(f"SELECT COUNT(1) FROM {self.tabla} WHERE id_migracion = :id_migracion")
                existe = db.execute(check_sql, {"id_migracion": id_migracion}).scalar()

                # --- Construcción dinámica de parámetros ---
                params = {}
                for ctx_key, col_sql in self.MAPEO.items():
                    valor = contexto.get(ctx_key, None)

                    # 🧼 Normalización:
                    # - Si es string vacío o solo espacios → None (para insertar NULL)
                    # - Si contiene "ERROR_" → también None (para no llenar basura)
                    if isinstance(valor, str):
                        valor = valor.strip()
                        if valor == "" or valor.upper().startswith("ERROR_"):
                            valor = None

                    params[col_sql] = valor

                # asegurar que id_migracion siempre esté
                params["id_migracion"] = id_migracion

                # --- UPDATE si ya existe ---
                if existe:
                    set_clauses = ", ".join([
                        f"{col} = :{col}" for col in self.MAPEO.values()
                        if col != "id_migracion"
                    ])

                    sql = text(f"""
                        UPDATE {self.tabla}
                        SET {set_clauses}
                        WHERE id_migracion = :id_migracion
                    """)

                    db.execute(sql, params)
                    db.commit()
                    print(f"🌀 Registro actualizado para id_migracion={id_migracion} en {self.tabla}")

                # --- INSERT si no existe ---
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

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from config.config import EnvConfig
from infrastructure.database.database import Base


class MigracionDetalleModel(Base):
    __tablename__ = EnvConfig.BOT_TABLA_MIGRACION_DETALLE

    id = Column(Integer, primary_key=True, autoincrement=True)

    id_migracion = Column(Integer, nullable=False, index=True)

    fecha_hora_inicio = Column(DateTime, nullable=True)
    fecha_hora_fin = Column(DateTime, nullable=True)

    fecha_hora_notificacion_baja_rpa = Column(DateTime, nullable=True)
    fecha_hora_observacion_rpa = Column(DateTime, nullable=True)

    plan_consumo_anterior_rpa = Column(String(200), nullable=True)
    plan_consumo_asignado_rpa = Column(String(200), nullable=True)
    codigo_plan_consumo_asignados_rpa = Column(Integer, nullable=True)

    estado_cuenta_anterior_rpa = Column(String(10), nullable=True)
    estado_cuenta_posterior_rpa = Column(String(10), nullable=True)

    forma_pago_anterior_rpa = Column(String(30), nullable=True)
    forma_pago_posterior_rpa = Column(String(30), nullable=True)

    situacion_cuenta_anterior_rpa = Column(String(30), nullable=True)
    situacion_cuenta_posterior_rpa = Column(String(30), nullable=True)

    servicios_asignados_rpa = Column(String(50), nullable=True)
    servicios_eliminados_rpa = Column(String(50), nullable=True)

    facturas_pendientes_rpa = Column(Integer, nullable=True)
    deuda_pendiente = Column(String(50), nullable=True)

    billetera_prepago_rpa = Column(String(1000), nullable=True)
    antiguedad_meses_rpa = Column(Integer, nullable=True)

    notificacion_baja = Column(String(10), nullable=True)
    mensaje_observacion_rpa = Column(String(1000), nullable=True)

    creado = Column(DateTime, server_default=func.now(), nullable=False)
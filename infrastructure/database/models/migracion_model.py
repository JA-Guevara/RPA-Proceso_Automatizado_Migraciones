from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String
from sqlalchemy.sql import func

from config.config import EnvConfig
from infrastructure.database.database import Base


class MigracionModel(Base):
    __tablename__ = EnvConfig.BOT_TABLA_MIGRACION

    id = Column(Integer, primary_key=True, autoincrement=True)

    id_linea = Column(Integer, nullable=False)
    id_estado = Column(Integer, nullable=False)
    id_tipo_baja = Column(Integer, nullable=False)
    id_tipo_lista = Column(Integer, nullable=False)

    id_sharepoint = Column(Integer, nullable=False)

    monto_valor_r = Column(Float, nullable=True)
    lote = Column(String(100), nullable=False)

    hash_uni = Column(String(64), unique=True, nullable=False)
    estado_exportacion = Column(Boolean, default=False, nullable=False)

    creado = Column(DateTime, server_default=func.now(), nullable=False)
    modificado = Column(DateTime, onupdate=func.now())
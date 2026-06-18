from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from config.config import EnvConfig
from infrastructure.database.database import Base


class PlanModel(Base):
    __tablename__ = EnvConfig.BOT_TABLA_PLANES
    # __table_args__ = {"schema": "dbo"}

    id = Column(Integer, primary_key=True, autoincrement=True)

    id_tipo_lista = Column(Integer, ForeignKey("tipo_lista.id"), nullable=True)
    nombre_plan = Column(String(150), nullable=False)
    tipo = Column(String(20), nullable=False)

    creado = Column(DateTime, server_default=func.now(), nullable=False)
    modificado = Column(DateTime, onupdate=func.now())
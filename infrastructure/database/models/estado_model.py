from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from config.config import EnvConfig
from infrastructure.database.database import Base


class EstadoModel(Base):
    __tablename__ = EnvConfig.BOT_TABLA_ESTADOS
    # __table_args__ = {"schema": "dbo"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(String(255), nullable=True)

    creado = Column(DateTime, server_default=func.now(), nullable=False)
    modificado = Column(DateTime, onupdate=func.now())
from decimal import Decimal

from sqlalchemy import Column, Integer, Numeric, String

from config.config import EnvConfig
from infrastructure.database.database import Base


def resolver_schema_y_tabla(nombre: str) -> tuple[str | None, str]:
    partes = nombre.strip().split(".")

    if len(partes) == 2:
        return partes[0], partes[1]

    return "dbo", partes[0]


_SCHEMA, _TABLA = resolver_schema_y_tabla(EnvConfig.BOT_VISTA)


class VistaMigracionModel(Base):

    __tablename__ = _TABLA
    __table_args__ = {"schema": _SCHEMA}

    id_migracion = Column(Integer, primary_key=True)

    id_sharepoint = Column(Integer, nullable=True)
    id_tipo_lista = Column(Integer, nullable=True)
    nombre_lista = Column(String(255), nullable=True)

    id_tipo_baja = Column(Integer, nullable=True)
    nombre_tipo_baja = Column(String(255), nullable=True)

    id_estado = Column(Integer, nullable=True)
    nombre_estado = Column(String(255), nullable=True)

    nro_linea = Column(String(50), nullable=True)
    monto_valor_residual = Column(Numeric(18, 2), nullable=True)

    lote = Column(String(100), nullable=True)
from sqlalchemy import select

from infrastructure.database.models.estado_model import EstadoModel


class EstadoRepository:
    def obtener_id_por_nombre(self, db, nombre_estado: str) -> int | None:
        return db.execute(
            select(EstadoModel.id).where(EstadoModel.nombre == nombre_estado)
        ).scalar()

    def obtener_nombre_por_id(self, db, id_estado: int) -> str | None:
        return db.execute(
            select(EstadoModel.nombre).where(EstadoModel.id == id_estado)
        ).scalar()

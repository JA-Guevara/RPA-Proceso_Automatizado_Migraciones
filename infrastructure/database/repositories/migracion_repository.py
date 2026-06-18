from sqlalchemy import update

from infrastructure.database.models.migracion_model import MigracionModel


class MigracionRepository:
    def actualizar_estado(self, db, id_migracion: int, id_estado: int) -> bool:
        stmt = (
            update(MigracionModel)
            .where(MigracionModel.id == id_migracion)
            .values(id_estado=id_estado)
        )

        result = db.execute(stmt)

        return result.rowcount > 0
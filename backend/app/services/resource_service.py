from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, ValidationFailure
from app.models.resource import Resource


class ResourceService:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> list[Resource]:
        return list(self.db.scalars(select(Resource).order_by(Resource.id)))

    def get(self, resource_id: int) -> Resource:
        r = self.db.get(Resource, resource_id)
        if not r:
            raise NotFoundError("Recurso não encontrado")
        return r

    def create(self, name: str, quantity: int) -> Resource:
        if self.db.scalar(select(Resource).where(Resource.resource_name == name)):
            raise ConflictError(f"Já existe um recurso chamado '{name}'.")
        r = Resource(resource_name=name, quantity_available=quantity, quantity_in_use=0)
        self.db.add(r)
        self.db.commit()
        return r

    def update_quantity(self, resource_id: int, quantity_available: int) -> Resource:
        r = self.get(resource_id)
        if quantity_available < r.quantity_in_use:
            raise ValidationFailure(
                f"Há {r.quantity_in_use} unidade(s) em uso; a quantidade não pode ficar abaixo disso."
            )
        r.quantity_available = quantity_available
        self.db.commit()
        return r

    def free_map(self) -> dict[int, int]:
        return {r.id: max(r.quantity_available - r.quantity_in_use, 0) for r in self.list()}

    @staticmethod
    def to_out(r: Resource) -> dict:
        return {
            "id": r.id,
            "resource_name": r.resource_name,
            "quantity_available": r.quantity_available,
            "quantity_in_use": r.quantity_in_use,
            "quantity_free": max(r.quantity_available - r.quantity_in_use, 0),
            "updated_at": r.updated_at,
        }

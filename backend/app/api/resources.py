from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_clock, get_db
from app.core.clock import Clock
from app.schemas.resource import ResourceCreate, ResourceOut, ResourceUpdate
from app.services.priority_service import PriorityService
from app.services.resource_service import ResourceService

router = APIRouter(prefix="/resources", tags=["Recursos"])


@router.get("", response_model=list[ResourceOut])
def list_resources(db: Session = Depends(get_db)):
    svc = ResourceService(db)
    return [svc.to_out(r) for r in svc.list()]


@router.post("", response_model=ResourceOut, status_code=201)
def create_resource(body: ResourceCreate, db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    svc = ResourceService(db)
    r = svc.create(body.resource_name, body.quantity_available)
    PriorityService(db, clock).recalculate("resources_changed", reason=f"Recurso criado: {r.resource_name}")
    return svc.to_out(r)


@router.put("/{resource_id}", response_model=ResourceOut, summary="Alterar disponibilidade (reavalia a fila)")
def update_resource(resource_id: int, body: ResourceUpdate, db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    svc = ResourceService(db)
    r = svc.get(resource_id)
    if body.quantity_available is not None:
        r = svc.update_quantity(resource_id, body.quantity_available)
    PriorityService(db, clock).recalculate("resources_changed", reason=f"{r.resource_name}: {r.quantity_available} unidade(s)")
    return svc.to_out(r)

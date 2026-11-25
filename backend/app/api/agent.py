from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_clock, get_db
from app.core.clock import Clock
from app.schemas.agent import AgentStatusOut, ConfigOut, ConfigUpdate, EvaluateRequest, EvaluateResponse
from app.schemas.queue import QueueOut
from app.services.config_service import ConfigService
from app.services.priority_service import PriorityService

router = APIRouter(prefix="/agent", tags=["Agente"])


@router.post("/evaluate", response_model=EvaluateResponse, summary="Avaliar sem persistir (cenários 'e se')")
def evaluate(req: EvaluateRequest, db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    return PriorityService(db, clock).evaluate_adhoc(req)


@router.get("/status", response_model=AgentStatusOut)
def status(db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    return PriorityService(db, clock).status()


@router.get("/configuration", response_model=ConfigOut)
def get_configuration(db: Session = Depends(get_db)):
    return ConfigService.to_out(ConfigService(db).get_active())


@router.get("/configuration/history", response_model=list[ConfigOut])
def configuration_history(db: Session = Depends(get_db)):
    return [ConfigService.to_out(r) for r in ConfigService(db).history()]


@router.put("/configuration", response_model=ConfigOut, summary="Nova versão de pesos/parâmetros e recálculo da fila")
def update_configuration(body: ConfigUpdate, db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    cfg = ConfigService(db)
    row, warnings = cfg.update(
        body.weights.model_dump() if body.weights else None,
        body.params.model_dump(exclude_none=True) if body.params else None,
        body.note,
    )
    PriorityService(db, clock).recalculate("config_changed", force=True, reason=f"Configuração v{row.version}")
    out = ConfigService.to_out(row)
    out["warnings"] = warnings
    return out


@router.post("/recalculate", response_model=QueueOut, summary="Forçar um ciclo do agente")
def recalculate(db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    svc = PriorityService(db, clock)
    svc.recalculate("manual", force=True)
    return svc.get_queue()

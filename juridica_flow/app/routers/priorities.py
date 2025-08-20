from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date
from ..db import get_db
from .. import models, schemas
from ..core.config import PRIORITY_DEADLINE_WEIGHT, PRIORITY_COMPLEXITY_WEIGHT, PRIORITY_AGE_WEIGHT

router = APIRouter(prefix="/priorities", tags=["priorities"])

def compute_score(req: models.LegalRequest) -> float:
    # deadline factor: más alto si el plazo está cerca o vencido
    deadline_factor = 0.0
    today = date.today()
    if req.due_date:
        days_left = (req.due_date - today).days
        if days_left <= 0:
            deadline_factor = 1.0  # vencido: máximo
        else:
            deadline_factor = max(0.0, 1.0 - (days_left / 30.0))  # a 30 días o más, ~0

    # complexity factor: 1/3/5 normalizado a 0..1
    complexity_map = {1: 0.2, 2: 0.6, 3: 1.0}
    complexity_factor = complexity_map.get(req.complexity, 0.6)

    # age factor: más viejo = más prioridad (0..1 según 60 días)
    age_days = (today - req.created_at.date()).days if req.created_at else 0
    age_factor = min(1.0, age_days / 60.0)

    score = (
        PRIORITY_DEADLINE_WEIGHT * deadline_factor +
        PRIORITY_COMPLEXITY_WEIGHT * complexity_factor +
        PRIORITY_AGE_WEIGHT * age_factor
    )
    return round(float(score), 4)

@router.get("/", response_model=list[schemas.PrioritizedTask])
def prioritized_list(db: Session = Depends(get_db)):
    q = db.query(models.LegalRequest).filter(models.LegalRequest.status != "COMPLETADO")
    items = []
    for req in q.all():
        assignees = [a.assignee for a in req.assignments]
        score = compute_score(req)
        items.append({
            "request": req,
            "assignees": assignees,
            "score": score
        })
    # ordenar desc por score
    items.sort(key=lambda x: x["score"], reverse=True)
    return items

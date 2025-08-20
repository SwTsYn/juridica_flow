from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from .. import models, schemas

router = APIRouter(prefix="/requests", tags=["requests"])

@router.post("/", response_model=schemas.LegalRequestOut)
def create_request(payload: schemas.LegalRequestCreate, db: Session = Depends(get_db)):
    unit = db.query(models.Unit).get(payload.unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unidad no encontrada")
    req = models.LegalRequest(
        title=payload.title,
        description=payload.description,
        unit_id=payload.unit_id,
        complexity=payload.complexity,
        due_date=payload.due_date,
        status=payload.status,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req

@router.get("/", response_model=list[schemas.LegalRequestOut])
def list_requests(db: Session = Depends(get_db)):
    return db.query(models.LegalRequest).order_by(models.LegalRequest.created_at.desc()).all()

@router.post("/{request_id}/assign/{user_id}", response_model=schemas.AssignmentOut)
def assign_request(request_id: int, user_id: int, db: Session = Depends(get_db)):
    req = db.query(models.LegalRequest).get(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Requerimiento no encontrado")
    user = db.query(models.User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    existing = db.query(models.Assignment).filter_by(request_id=request_id, assignee_id=user_id).first()
    if existing:
        return existing

    asg = models.Assignment(request_id=request_id, assignee_id=user_id)
    db.add(asg)
    db.commit()
    db.refresh(asg)
    return asg

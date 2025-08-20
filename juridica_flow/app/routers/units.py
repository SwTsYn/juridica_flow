from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from .. import models, schemas

router = APIRouter(prefix="/units", tags=["units"])

@router.post("/", response_model=schemas.UnitOut)
def create_unit(payload: schemas.UnitCreate, db: Session = Depends(get_db)):
    if db.query(models.Unit).filter(models.Unit.name == payload.name).first():
        raise HTTPException(status_code=400, detail="La unidad ya existe")
    unit = models.Unit(name=payload.name)
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit

@router.get("/", response_model=list[schemas.UnitOut])
def list_units(db: Session = Depends(get_db)):
    return db.query(models.Unit).order_by(models.Unit.name).all()

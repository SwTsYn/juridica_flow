"""Semilla inicial con la dotación entregada y unidades típicas.
Ejecuta: `python scripts/seed.py` (con el server apagado) o `uvicorn app.main:app` ya creado DB y luego este script.
"""
from app.db import Base, engine, SessionLocal
from app import models

def ensure_seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Unidades base
        unit_names = [
            "Dirección de Tránsito",
            "SECPLA",
            "Dirección de Administración y Finanzas",
            "DIDECO",
            "Dirección de Obras Municipales"
        ]
        for name in unit_names:
            if not db.query(models.Unit).filter_by(name=name).first():
                db.add(models.Unit(name=name))
        db.commit()

        # Dotación
        users = [
            ("Luis Patricio Yáñez González", "Director Jurídico"),
            ("Luis Matías Trujillo Leiva", "Asesor Jurídico"),
            ("Salomón Ignacio Rivas Tapia", "Asesor Jurídico"),
            ("Romina Andrea Durán Durán", "Administrativa"),
        ]
        for full_name, role in users:
            if not db.query(models.User).filter_by(full_name=full_name).first():
                db.add(models.User(full_name=full_name, role=role))
        db.commit()
        print("Seed OK")
    finally:
        db.close()

if __name__ == "__main__":
    ensure_seed()

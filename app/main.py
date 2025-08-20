# app/main.py
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, Response

from .db import Base, engine
from .routers import users, units, requests, priorities
from . import web

# Crear tablas
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Jurídica Flow", version="0.1.0")

# Routers API
app.include_router(users.router)
app.include_router(units.router)
app.include_router(requests.router)
app.include_router(priorities.router)

# Router UI
app.include_router(web.router)

# Static (solo si existe app/static)
STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Redirección raíz y favicon
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/ui", status_code=307)

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)

@app.get("/health")
def health():
    return {"status": "ok"}


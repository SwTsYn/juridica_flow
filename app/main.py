from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .db import Base, engine
from .routers import users, units, requests, priorities
from . import web  # <-- NUEVO

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Jurídica Flow", version="0.1.0")

# APIs JSON
app.include_router(users.router)
app.include_router(units.router)
app.include_router(requests.router)
app.include_router(priorities.router)

# UI
app.include_router(web.router)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/health")
def health():
    return {"status": "ok"}

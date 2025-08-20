from collections import defaultdict
from datetime import date
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from pathlib import Path
from fastapi.templating import Jinja2Templates

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

from sqlalchemy.orm import Session

from .db import get_db
from . import models
from .core.config import (
    PRIORITY_DEADLINE_WEIGHT,
    PRIORITY_COMPLEXITY_WEIGHT,
    PRIORITY_AGE_WEIGHT,
)

router = APIRouter(tags=["ui"])
templates = Jinja2Templates(directory="templates")


# ------------------ SCORE ------------------
def compute_score(req: models.LegalRequest) -> float:
    """
    Score = combinación de 3 factores normalizados en [0..1]:
      - deadline_factor: más alto si está vencido o cerca del vencimiento
      - complexity_factor: 1 (alta), 0.6 (media), 0.2 (baja)
      - age_factor: sube con la antigüedad (cap en 60 días)
    Pesos vienen de core.config (PRIORITY_*_WEIGHT).
    """
    today = date.today()

    # deadline
    deadline_factor = 0.0
    if req.due_date:
        days_left = (req.due_date - today).days
        deadline_factor = 1.0 if days_left <= 0 else max(0.0, 1.0 - (days_left / 30.0))

    # complexity
    complexity_map = {1: 0.2, 2: 0.6, 3: 1.0}
    complexity = getattr(req, "complexity", 2)
    complexity_factor = complexity_map.get(int(complexity), 0.6)

    # age
    age_days = (today - req.created_at.date()).days if getattr(req, "created_at", None) else 0
    age_factor = min(1.0, age_days / 60.0)

    score = (
        PRIORITY_DEADLINE_WEIGHT * deadline_factor
        + PRIORITY_COMPLEXITY_WEIGHT * complexity_factor
        + PRIORITY_AGE_WEIGHT * age_factor
    )
    return round(float(score), 4)


# ------------------ REPORTERÍA ------------------

@router.get("/ui/reports", response_class=HTMLResponse)
def ui_reports(request: Request, db: Session = Depends(get_db)):
    # Trae todo una vez
    reqs = db.query(models.LegalRequest).all()
    users = {u.id: u for u in db.query(models.User).all()}
    units = {u.id: u for u in db.query(models.Unit).all()}
    today = date.today()

    # ---------- Métricas por usuario (carga) ----------
    per_user_counts = defaultdict(int)
    per_user_score = defaultdict(float)
    per_user_overdue = defaultdict(int)
    per_user_bins = defaultdict(lambda: {"0-0.33": 0, "0.34-0.66": 0, "0.67-1.0": 0})

    for r in reqs:
        if r.status == "COMPLETADO":
            continue
        score = compute_score(r)
        is_overdue = (r.due_date and r.due_date < today)
        assignees = [a.assignee_id for a in r.assignments]
        if not assignees:
            continue
        for uid in assignees:
            per_user_counts[uid] += 1
            per_user_score[uid] += score
            if is_overdue:
                per_user_overdue[uid] += 1
            if score <= 0.33:
                per_user_bins[uid]["0-0.33"] += 1
            elif score <= 0.66:
                per_user_bins[uid]["0.34-0.66"] += 1
            else:
                per_user_bins[uid]["0.67-1.0"] += 1

    user_ids = list(per_user_counts.keys())
    user_labels = [users[uid].full_name for uid in user_ids]
    user_open_counts = [per_user_counts[uid] for uid in user_ids]
    user_total_score = [round(per_user_score[uid], 3) for uid in user_ids]
    user_overdue_counts = [per_user_overdue.get(uid, 0) for uid in user_ids]
    user_bins_1 = [per_user_bins[uid]["0-0.33"] for uid in user_ids]
    user_bins_2 = [per_user_bins[uid]["0.34-0.66"] for uid in user_ids]
    user_bins_3 = [per_user_bins[uid]["0.67-1.0"] for uid in user_ids]

    # ---------- Métricas por unidad ----------
    unit_total = defaultdict(int)
    unit_open = defaultdict(int)
    unit_overdue = defaultdict(int)
    unit_avg_complexity_sum = defaultdict(int)
    unit_avg_complexity_n = defaultdict(int)

    for r in reqs:
        unit_name = units[r.unit_id].name if r.unit_id in units else "¿(Sin unidad)?"
        unit_total[unit_name] += 1
        if r.status != "COMPLETADO":
            unit_open[unit_name] += 1
        if r.due_date and r.due_date < today and r.status != "COMPLETADO":
            unit_overdue[unit_name] += 1
        if r.complexity:
            unit_avg_complexity_sum[unit_name] += int(r.complexity)
            unit_avg_complexity_n[unit_name] += 1

    unit_labels = list(unit_total.keys())
    unit_total_vals = [unit_total[n] for n in unit_labels]
    unit_open_vals = [unit_open[n] for n in unit_labels]
    unit_overdue_vals = [unit_overdue[n] for n in unit_labels]
    unit_avg_complexity = [
        round(unit_avg_complexity_sum[n] / unit_avg_complexity_n[n], 2) if unit_avg_complexity_n[n] else 0
        for n in unit_labels
    ]

    # ---------- Estado global y complejidad ----------
    status_counts = {"SIN_ASIGNAR": 0, "PENDIENTE": 0, "COMPLETADO": 0}
    complexity_counts = {1: 0, 2: 0, 3: 0}

    for r in reqs:
        assigned = len(r.assignments) > 0
        if not assigned:
            status_counts["SIN_ASIGNAR"] += 1
        else:
            if r.status == "COMPLETADO":
                status_counts["COMPLETADO"] += 1
            else:
                status_counts["PENDIENTE"] += 1
        if r.complexity in (1, 2, 3):
            complexity_counts[int(r.complexity)] += 1

    # ---------- Envejecimiento ----------
    aging_buckets = {"0-7": 0, "8-30": 0, "31-60": 0, ">60": 0}
    for r in reqs:
        age = (today - r.created_at.date()).days if r.created_at else 0
        if age <= 7:
            aging_buckets["0-7"] += 1
        elif age <= 30:
            aging_buckets["8-30"] += 1
        elif age <= 60:
            aging_buckets["31-60"] += 1
        else:
            aging_buckets[">60"] += 1

    # ---------- SLA simple ----------
    due_soon_unassigned = 0
    for r in reqs:
        if r.due_date and 0 <= (r.due_date - today).days <= 7 and len(r.assignments) == 0 and r.status != "COMPLETADO":
            due_soon_unassigned += 1

    return templates.TemplateResponse(
        "reports_page.html",
        {
            "request": request,
            "active": "reports",
            "user_labels": user_labels,
            "user_open_counts": user_open_counts,
            "user_total_score": user_total_score,
            "user_overdue_counts": user_overdue_counts,
            "user_bins_1": user_bins_1,
            "user_bins_2": user_bins_2,
            "user_bins_3": user_bins_3,
            "unit_labels": unit_labels,
            "unit_total_vals": unit_total_vals,
            "unit_open_vals": unit_open_vals,
            "unit_overdue_vals": unit_overdue_vals,
            "unit_avg_complexity": unit_avg_complexity,
            "status_labels": list(status_counts.keys()),
            "status_vals": list(status_counts.values()),
            "complexity_labels": ["Baja (1)", "Media (2)", "Alta (3)"],
            "complexity_vals": [complexity_counts[1], complexity_counts[2], complexity_counts[3]],
            "aging_labels": list(aging_buckets.keys()),
            "aging_vals": list(aging_buckets.values()),
            "due_soon_unassigned": due_soon_unassigned,
        },
    )


# ------------------ PÁGINAS (NAV) ------------------

@router.get("/ui", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    """Inicio: próximos vencimientos y asignados."""
    today = date.today()
    q = db.query(models.LegalRequest).filter(models.LegalRequest.status != "COMPLETADO")
    upcoming = []
    for r in q.all():
        if r.due_date:
            days = (r.due_date - today).days
            if -3 <= days <= 14:
                upcoming.append({
                    "request": r,
                    "assignees": [a.assignee for a in r.assignments],
                    "score": compute_score(r),
                })
    upcoming.sort(key=lambda x: (x["request"].due_date or today, -x["score"]))
    return templates.TemplateResponse("home.html", {"request": request, "upcoming": upcoming, "active": "home"})


@router.get("/ui/requests", response_class=HTMLResponse)
def ui_requests(request: Request, db: Session = Depends(get_db)):
    users = db.query(models.User).order_by(models.User.full_name).all()
    units = db.query(models.Unit).order_by(models.Unit.name).all()
    reqs = db.query(models.LegalRequest).order_by(models.LegalRequest.created_at.desc()).all()
    items = []
    for r in reqs:
        if r.status != "COMPLETADO":
            items.append((r, [a.assignee for a in r.assignments], compute_score(r)))
    items.sort(key=lambda t: t[2], reverse=True)
    return templates.TemplateResponse(
        "requests_page.html",
        {"request": request, "users": users, "units": units, "requests": reqs, "priorities": items, "active": "requests"},
    )


@router.get("/ui/users", response_class=HTMLResponse)
def ui_users(request: Request, db: Session = Depends(get_db)):
    users = db.query(models.User).order_by(models.User.full_name).all()
    return templates.TemplateResponse("users_page.html", {"request": request, "users": users, "active": "users"})


@router.get("/ui/units", response_class=HTMLResponse)
def ui_units(request: Request, db: Session = Depends(get_db)):
    units = db.query(models.Unit).order_by(models.Unit.name).all()
    return templates.TemplateResponse("units_page.html", {"request": request, "units": units, "active": "units"})


# ------------------ PARTIALS (HTMX) ------------------

@router.get("/ui/partials/users", response_class=HTMLResponse)
def partial_users(request: Request, db: Session = Depends(get_db)):
    users = db.query(models.User).order_by(models.User.full_name).all()
    return templates.TemplateResponse("partials/users.html", {"request": request, "users": users})


@router.get("/ui/partials/units", response_class=HTMLResponse)
def partial_units(request: Request, db: Session = Depends(get_db)):
    units = db.query(models.Unit).order_by(models.Unit.name).all()
    return templates.TemplateResponse("partials/units.html", {"request": request, "units": units})


@router.get("/ui/partials/requests", response_class=HTMLResponse)
def partial_requests(request: Request, db: Session = Depends(get_db)):
    reqs = db.query(models.LegalRequest).order_by(models.LegalRequest.created_at.desc()).all()
    return templates.TemplateResponse("partials/requests.html", {"request": request, "requests": reqs})


@router.get("/ui/partials/priorities", response_class=HTMLResponse)
def partial_priorities(request: Request, db: Session = Depends(get_db)):
    reqs = db.query(models.LegalRequest).filter(models.LegalRequest.status != "COMPLETADO").all()
    items = [(r, [a.assignee for a in r.assignments], compute_score(r)) for r in reqs]
    items.sort(key=lambda t: t[2], reverse=True)
    return templates.TemplateResponse("partials/priorities.html", {"request": request, "priorities": items})


@router.get("/ui/partials/assign_form", response_class=HTMLResponse)
def partial_assign_form(request: Request, db: Session = Depends(get_db)):
    users = db.query(models.User).order_by(models.User.full_name).all()
    reqs = db.query(models.LegalRequest).order_by(models.LegalRequest.created_at.desc()).all()
    return templates.TemplateResponse("partials/assign_form.html", {"request": request, "users": users, "requests": reqs})


# ------------------ ACCIONES (FORMULARIOS) ------------------

@router.post("/ui/create_user", response_class=HTMLResponse)
def create_user(
    request: Request,
    full_name: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db),
):
    user = models.User(full_name=full_name, role=role)
    db.add(user)
    db.commit()
    return partial_users(request, db)


@router.post("/ui/create_unit", response_class=HTMLResponse)
def create_unit(
    request: Request,
    name: str = Form(...),
    db: Session = Depends(get_db),
):
    if db.query(models.Unit).filter(models.Unit.name == name).first():
        raise HTTPException(status_code=400, detail="La unidad ya existe")
    unit = models.Unit(name=name)
    db.add(unit)
    db.commit()
    return partial_units(request, db)


@router.post("/ui/create_request", response_class=HTMLResponse)
def create_request(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    unit_id: int = Form(...),
    complexity: int = Form(2),
    due_date: str | None = Form(None),
    db: Session = Depends(get_db),
):
    due = date.fromisoformat(due_date) if due_date else None

    if not db.query(models.Unit).get(unit_id):
        raise HTTPException(status_code=404, detail="Unidad no encontrada")

    r = models.LegalRequest(
        title=title,
        description=description,
        unit_id=unit_id,
        complexity=complexity,
        due_date=due,
        status="PENDIENTE",
    )
    db.add(r)
    db.commit()

    if request.headers.get("HX-Request") == "true":
        return HTMLResponse(status_code=204, headers={"HX-Redirect": "/ui/requests"})
    return partial_requests(request, db)


@router.post("/ui/set_status", response_class=HTMLResponse)
def set_status(
    request: Request,
    request_id: int = Form(...),
    status: str = Form(...),
    db: Session = Depends(get_db),
):
    req = db.query(models.LegalRequest).get(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Requerimiento no encontrado")

    if status not in ("PENDIENTE", "COMPLETADO"):
        raise HTTPException(status_code=400, detail="Estado inválido")

    req.status = status
    db.commit()
    return partial_requests(request, db)


@router.post("/ui/assign", response_class=HTMLResponse)
def assign_request(
    request: Request,
    request_id: int = Form(...),
    user_id: int = Form(...),
    db: Session = Depends(get_db),
):
    req = db.query(models.LegalRequest).get(request_id)
    user = db.query(models.User).get(user_id)
    if not req or not user:
        raise HTTPException(status_code=404, detail="Requerimiento o usuario no existe")

    if not db.query(models.Assignment).filter_by(request_id=request_id, assignee_id=user_id).first():
        db.add(models.Assignment(request_id=request_id, assignee_id=user_id))

    if req.status != "COMPLETADO":
        req.status = "PENDIENTE"

    db.commit()
    return partial_priorities(request, db)


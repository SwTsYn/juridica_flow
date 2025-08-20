# Jurídica Flow

Sistema mínimo para priorizar y asignar requerimientos en una Dirección Jurídica municipal.
Stack: **FastAPI + SQLAlchemy + Uvicorn**. Base local por defecto en **SQLite**, configurable a Postgres (Neon/Render) vía `DATABASE_URL`.

## Estructura

```
juridica_flow/
  app/
    core/
      config.py
    routers/
      users.py
      units.py
      requests.py
      priorities.py
    __init__.py
    db.py
    models.py
    schemas.py
    main.py
  scripts/
    dev_run.sh
    seed.py
  tests/
    test_smoke.py
  .env.example
  requirements.txt
  README.md
```

## Ejecutar en local (Windows/Linux/Mac)

1. **Python 3.11+ recomendado**
2. Crear y activar un entorno virtual (opcional, pero recomendado)
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # Linux/Mac
   source .venv/bin/activate
   ```
3. Instalar dependencias
   ```bash
   pip install -r requirements.txt
   ```
4. Copiar `.env.example` a `.env` y ajustar si quieres usar Postgres. Si no, se usa SQLite por defecto.
5. Ejecutar el servidor
   ```bash
   bash scripts/dev_run.sh
   # o
   uvicorn app.main:app --reload
   ```
6. Abrir la documentación interactiva: `http://127.0.0.1:8000/docs`

## Configurar Postgres (Neon) más adelante

- Ajusta `DATABASE_URL` en `.env` usando el string de conexión de Neon, por ejemplo:
  ```env
  DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST/DB?sslmode=require
  ```
- Reinicia el servidor. Las tablas se crean automáticamente la primera vez.

## Ideas de siguiente paso
- Autenticación con usuarios reales (OAuth municipal o JWT simple).
- Alembic para migraciones.
- Integración con Google Calendar para fechas límite.
- Dashboard con frontend (React o FastAPI-templates).

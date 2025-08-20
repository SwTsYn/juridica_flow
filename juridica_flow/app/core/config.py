import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./juridica_flow.db")

# Pesos del cálculo de prioridad
PRIORITY_DEADLINE_WEIGHT = float(os.getenv("PRIORITY_DEADLINE_WEIGHT", 0.6))
PRIORITY_COMPLEXITY_WEIGHT = float(os.getenv("PRIORITY_COMPLEXITY_WEIGHT", 0.3))
PRIORITY_AGE_WEIGHT = float(os.getenv("PRIORITY_AGE_WEIGHT", 0.1))

from datetime import datetime
from sqlalchemy import Column, Integer, String, Date, Enum, ForeignKey, Text, DateTime, func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .db import Base
import enum

class Complexity(enum.IntEnum):
    BAJA = 1
    MEDIA = 2
    ALTA = 3

class Status(enum.Enum):
    PENDIENTE = "PENDIENTE"
    EN_CURSO = "EN_CURSO"
    COMPLETADO = "COMPLETADO"

class Unit(Base):
    __tablename__ = "units"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)

    requests = relationship("LegalRequest", back_populates="unit")

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    role: Mapped[str] = mapped_column(String(60), nullable=False)

    assignments = relationship("Assignment", back_populates="assignee")

class LegalRequest(Base):
    __tablename__ = "legal_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    unit_id: Mapped[int] = mapped_column(Integer, ForeignKey("units.id"), nullable=False)
    complexity: Mapped[int] = mapped_column(Integer, default=2)  # 1 baja, 2 media, 3 alta
    due_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDIENTE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    unit = relationship("Unit", back_populates="requests")
    assignments = relationship("Assignment", back_populates="request", cascade="all, delete-orphan")

class Assignment(Base):
    __tablename__ = "assignments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    request_id: Mapped[int] = mapped_column(Integer, ForeignKey("legal_requests.id"), nullable=False)
    assignee_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    request = relationship("LegalRequest", back_populates="assignments")
    assignee = relationship("User", back_populates="assignments")

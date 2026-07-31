import os
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import DATABASE_URL


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    active = Column(Boolean, default=True)


def get_engine(url: str | None = None):
    url = url or DATABASE_URL
    connect_args = {}
    if url.startswith("sqlite"):
        db_path = url.replace("sqlite:///", "", 1)
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        connect_args["check_same_thread"] = False
    try:
        return create_engine(url, connect_args=connect_args, echo=False, future=True)
    except Exception as exc:
        preview = (url or "")[:40]
        raise RuntimeError(
            f"Falha ao conectar no banco. Verifique DATABASE_URL no Render. "
            f"Início do valor: {preview!r}. Erro original: {exc}"
        ) from exc


def create_tables(engine=None):
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(engine)


def get_session_factory(engine=None):
    if engine is None:
        engine = get_engine()
    return sessionmaker(engine, class_=Session, expire_on_commit=False)

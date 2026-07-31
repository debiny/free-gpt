from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, Boolean, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


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


def get_engine(path: str = "sqlite:///./data/auth.db"):
    import os
    os.makedirs(os.path.dirname(path.replace("sqlite:///", "")), exist_ok=True)
    return create_engine(
        path,
        connect_args={"check_same_thread": False} if path.startswith("sqlite") else {},
        echo=False,
        future=True,
    )


def create_tables(engine=None):
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(engine)


def get_session_factory(engine=None):
    if engine is None:
        engine = get_engine()
    return sessionmaker(engine, class_=Session, expire_on_commit=False)
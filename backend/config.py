import os
from pathlib import Path


def load_local_env() -> None:
    """Carrega backend/.env se existir (dev local). No Render as vars já vêm do painel."""
    env_path = Path(__file__).parent / ".env"
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_local_env()


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Variável de ambiente {name} não definida. "
            f"Defina no .env (local) ou no painel do Render."
        )
    return value


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "sqlite:///./data/auth.db")
    # Render/Heroku às vezes entregam postgres:// — SQLAlchemy exige postgresql://
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    return url


OPENROUTER_API_KEY = require_env("OPENROUTER_API_KEY")
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-only-change-me-in-production")
DATABASE_URL = get_database_url()

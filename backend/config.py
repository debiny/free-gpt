import os
import re
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
    # Importante: "" no Render NÃO deve cair no default do .get()
    raw = (os.environ.get("DATABASE_URL") or "sqlite:///./data/auth.db").strip()
    url = raw.strip().strip('"').strip("'").strip("`")

    # Se colaram o comando psql inteiro, extrai só a URL
    match = re.search(r"(postgres(?:ql)?(?:\+\w+)?://\S+)", url, flags=re.IGNORECASE)
    if match:
        url = match.group(1).rstrip("';'")

    # Render/Heroku: postgres:// → postgresql://
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]

    # Driver explícito (psycopg2-binary)
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://") :]

    if not (
        url.startswith("sqlite:")
        or url.startswith("postgresql+psycopg2://")
        or url.startswith("postgresql://")
    ):
        preview = url[:32] if url else "(vazia)"
        raise RuntimeError(
            "DATABASE_URL inválida. Cole a Internal Database URL do Postgres no Render "
            f"(começa com postgresql://). Valor recebido (início): {preview!r}"
        )

    return url


OPENROUTER_API_KEY = require_env("OPENROUTER_API_KEY")
JWT_SECRET = os.environ.get("JWT_SECRET") or "dev-only-change-me-in-production"
DATABASE_URL = get_database_url()

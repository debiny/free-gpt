import os
import re
from pathlib import Path
from urllib.parse import quote_plus, urlparse


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


def _normalize_pg_url(url: str) -> str:
    url = url.strip().strip('"').strip("'").strip("`")
    match = re.search(r"(postgres(?:ql)?(?:\+\w+)?://\S+)", url, flags=re.IGNORECASE)
    if match:
        url = match.group(1).rstrip("';'")
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://") :]
    return url


def _url_has_password(url: str) -> bool:
    try:
        # postgresql+psycopg2:// não é bem entendido pelo urlparse em todos os casos
        parsed = urlparse(url.replace("postgresql+psycopg2://", "postgresql://", 1))
        return bool(parsed.password)
    except Exception:
        return False


def _url_from_pg_parts() -> str | None:
    """Monta a URL a partir das variáveis PG* que o Render costuma expor."""
    host = os.environ.get("PGHOST") or os.environ.get("DB_HOST")
    user = os.environ.get("PGUSER") or os.environ.get("DB_USER")
    password = os.environ.get("PGPASSWORD") or os.environ.get("DB_PASSWORD")
    dbname = os.environ.get("PGDATABASE") or os.environ.get("DB_NAME")
    port = os.environ.get("PGPORT") or os.environ.get("DB_PORT") or "5432"

    if not all([host, user, password, dbname]):
        return None

    return (
        f"postgresql+psycopg2://{quote_plus(user)}:{quote_plus(password)}"
        f"@{host}:{port}/{dbname}"
    )


def get_database_url() -> str:
    raw = (os.environ.get("DATABASE_URL") or "").strip()

    if raw:
        url = _normalize_pg_url(raw)
        if url.startswith("sqlite:"):
            return url
        if url.startswith("postgresql+psycopg2://") and _url_has_password(url):
            return url
        # URL sem senha (ex.: só hostname ou user@host) — tenta montar pelas PG*
        built = _url_from_pg_parts()
        if built:
            return built
        if url.startswith("postgresql+psycopg2://"):
            raise RuntimeError(
                "DATABASE_URL está sem senha. No Postgres do Render, copie a "
                "Internal Database URL completa (postgresql://user:SENHA@host/db), "
                "ou preencha PGUSER, PGPASSWORD, PGHOST e PGDATABASE."
            )

    built = _url_from_pg_parts()
    if built:
        return built

    # Dev local
    return "sqlite:///./data/auth.db"


OPENROUTER_API_KEY = require_env("OPENROUTER_API_KEY")
JWT_SECRET = os.environ.get("JWT_SECRET") or "dev-only-change-me-in-production"
DATABASE_URL = get_database_url()

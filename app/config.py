import os
from pathlib import Path


def load_local_env() -> None:
    """Carrega o arquivo .env do diretório do app ou da raiz do projeto."""
    for env_path in [Path(__file__).parent / ".env", Path(__file__).parent.parent / ".env"]:
        if env_path.is_file():
            for raw in env_path.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
            break


load_local_env()

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
MODEL = os.environ.get("OPENROUTER_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free")

# Origens permitidas no CORS: localhost para dev, a própria URL pública do
# serviço no Render (injetada automaticamente como RENDER_EXTERNAL_URL) e
# quaisquer extras definidas em ALLOWED_ORIGINS (separadas por vírgula).
_default_origins = ["http://localhost:8000", "http://127.0.0.1:8000"]
_render_url = os.environ.get("RENDER_EXTERNAL_URL")
if _render_url:
    _default_origins.append(_render_url)
_extra_origins = [
    origin.strip()
    for origin in os.environ.get("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
ALLOWED_ORIGINS = _default_origins + _extra_origins

# Configurações do Banco de Dados e Autenticação
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./data/app.db")
# Ajusta URLs antigas de provedores como Render/Heroku ("postgres://" -> "postgresql://")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

JWT_SECRET = os.environ.get("JWT_SECRET", "lumina-super-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24 * 7  # 7 dias de validade


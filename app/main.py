from pathlib import Path
from typing import Optional
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
import httpx
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth import (
    create_token,
    decode_token,
    hash_password,
    token_from_authorization,
    verify_password,
)
from config import MODEL, OPENROUTER_API_KEY
from models import User, create_tables, get_engine, get_session_factory

app = FastAPI(
    title="Free GPT API",
    description="API com autenticação em banco de dados e integração com IA",
    version="2.0.0",
)

# Habilita CORS para permitir requisições de qualquer cliente frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicialização do Banco de Dados (SQLite local ou PostgreSQL em produção)
engine = get_engine()
create_tables(engine)
SessionFactory = get_session_factory(engine)

security = HTTPBearer(auto_error=False)


def get_db():
    """Gera uma sessão de banco de dados do SQLAlchemy por requisição."""
    session = SessionFactory()
    try:
        yield session
    finally:
        session.close()


def get_current_user(
    session: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> User:
    """Dependency para proteger rotas exigindo um token JWT válido."""
    raw_header = credentials.credentials if credentials else None
    token = token_from_authorization(raw_header)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação necessária para acessar este recurso.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão inválida ou expirada. Faça login novamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = session.get(User, payload["sub"])
    if not user or not user.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado ou inativo.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# Schemas Pydantic
class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, description="Nome do usuário")
    email: str = Field(..., description="Email único")
    password: str = Field(..., min_length=6, description="Senha com no mínimo 6 caracteres")


class LoginRequest(BaseModel):
    email: str = Field(..., description="Email de cadastro")
    password: str = Field(..., description="Senha do usuário")


class UserResponse(BaseModel):
    id: str
    name: str
    email: str


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


class MessageRequest(BaseModel):
    message: str = Field(..., description="Mensagem do usuário para a IA")


class MessageResponse(BaseModel):
    reply: str = Field(..., description="Resposta gerada pela IA")


# Endpoints de Autenticação
@app.post("/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, session: Session = Depends(get_db)):
    clean_email = request.email.strip().lower()
    existing = session.execute(select(User).where(User.email == clean_email)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este email já está cadastrado.",
        )

    user = User(
        name=request.name.strip(),
        email=clean_email,
        password_hash=hash_password(request.password),
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    token = create_token(user.id, user.email)
    return AuthResponse(
        token=token,
        user=UserResponse(id=user.id, name=user.name, email=user.email),
    )


@app.post("/auth/login", response_model=AuthResponse)
def login(request: LoginRequest, session: Session = Depends(get_db)):
    clean_email = request.email.strip().lower()
    user = session.execute(select(User).where(User.email == clean_email)).scalar_one_or_none()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos.",
        )

    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sua conta está inativa.",
        )

    token = create_token(user.id, user.email)
    return AuthResponse(
        token=token,
        user=UserResponse(id=user.id, name=user.name, email=user.email),
    )


@app.get("/auth/me")
def get_profile(current_user: User = Depends(get_current_user)):
    return {
        "user": {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
        }
    }


# Endpoint de Envio de Mensagem (Protegido por Autenticação)
@app.post("/send_message", response_model=MessageResponse)
async def send_message(
    request: MessageRequest,
    current_user: User = Depends(get_current_user),
):
    if not OPENROUTER_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A variável OPENROUTER_API_KEY não está configurada.",
        )

    message_text = request.message.strip()
    if not message_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A mensagem não pode ser vazia.",
        )

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": message_text}
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            reply = data["choices"][0]["message"]["content"]
            return MessageResponse(reply=reply)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"Erro na API do OpenRouter: {exc.response.text}",
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Erro de comunicação com o OpenRouter: {str(exc)}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno no servidor: {str(exc)}",
        )


# Servir Frontend Unificado
STATIC_DIR = Path(__file__).parent / "static"


@app.get("/", response_class=FileResponse)
def serve_frontend():
    """Renderiza a aplicação frontend Lumina Chat 2.0."""
    index_file = STATIC_DIR / "index.html"
    if not index_file.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo frontend index.html não encontrado na pasta static.",
        )
    return FileResponse(index_file)


# Montar pastas de arquivos estáticos (CSS, JS, imagens, fontes)
if (STATIC_DIR / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

if (STATIC_DIR / "lumina-video").is_dir():
    app.mount("/lumina-video", StaticFiles(directory=STATIC_DIR / "lumina-video"), name="lumina-video")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

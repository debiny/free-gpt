import json
import urllib.request
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth import (
    create_token,
    decode_token,
    hash_password,
    token_from_authorization,
    verify_password,
)
from config import OPENROUTER_API_KEY
from models import User, create_tables, get_engine, get_session_factory

model = "nvidia/nemotron-3-ultra-550b-a55b:free"
STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)

engine = get_engine()
create_tables(engine)
SessionFactory = get_session_factory(engine)


class MessageRequest(BaseModel):
    message: str


class RegisterRequest(BaseModel):
    email: str
    name: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


def get_db():
    session = SessionFactory()
    try:
        yield session
    finally:
        session.close()


def get_current_user(
    session: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    token = token_from_authorization(credentials.credentials if credentials else None)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
        )
    user = session.get(User, payload["sub"])
    if not user or not user.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado",
        )
    return user


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/register")
def register(request: RegisterRequest, session: Session = Depends(get_db)):
    existing = session.execute(select(User).where(User.email == request.email)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email já cadastrado")
    user = User(
        email=request.email,
        name=request.name,
        password_hash=hash_password(request.password),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    token = create_token(user.id, user.email)
    return {"token": token, "user": {"id": user.id, "name": user.name, "email": user.email}}


@app.post("/auth/login")
def login(request: LoginRequest, session: Session = Depends(get_db)):
    user = session.execute(select(User).where(User.email == request.email)).scalar_one_or_none()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")
    token = create_token(user.id, user.email)
    return {"token": token, "user": {"id": user.id, "name": user.name, "email": user.email}}


@app.post("/send_message")
def send_message(request: MessageRequest, user: User = Depends(get_current_user)):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": request.message}],
    })
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=body.encode(),
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        reply = json.loads(resp.read().decode())["choices"][0]["message"]["content"]
    return {"reply": reply}


@app.get("/")
def serve_frontend():
    return FileResponse(STATIC_DIR / "index.html")


app.mount(
    "/lumina-video",
    StaticFiles(directory=STATIC_DIR / "lumina-video"),
    name="lumina-video",
)

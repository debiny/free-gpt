import json
import urllib.request
from pydotenv import Environment
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import User, create_tables, get_engine, get_session_factory
from auth import hash_password, verify_password, create_token, decode_token, token_from_authorization

env = Environment()
api_key = env["OPENROUTER_API_KEY"]
model = "nvidia/nemotron-3-ultra-550b-a55b:free"

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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido ou expirado")
    user = session.get(User, payload["sub"])
    if not user or not user.active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado")
    return user

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
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        reply = json.loads(resp.read().decode())["choices"][0]["message"]["content"]
    return {"reply": reply}
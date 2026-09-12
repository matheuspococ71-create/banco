
"""
Bagual Banco — Backend
API que implementa exatamente os endpoints esperados pelo front-end
(banco-app.html): registro, login, saldo, extrato, depositar, sacar, transferir.
"""

import os
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from sqlalchemy import (
    create_engine, Column, String, Numeric, DateTime, ForeignKey
)
from sqlalchemy.orm import sessionmaker, declarative_base, Session
import bcrypt
from jose import jwt, JWTError

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./bagual.db")
# Railway entrega DATABASE_URL como "postgres://...", SQLAlchemy quer "postgresql://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

SECRET_KEY = os.environ.get("SECRET_KEY", "troque-essa-chave-em-producao")
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 60 * 24  # 24h

CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")
origins = [o.strip() for o in CORS_ORIGINS.split(",")] if CORS_ORIGINS != "*" else ["*"]

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))

# ---------------------------------------------------------------------------
# Modelos de banco de dados
# ---------------------------------------------------------------------------

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    nome = Column(String, nullable=False)
    usuario = Column(String, unique=True, index=True, nullable=False)
    senha_hash = Column(String, nullable=False)
    saldo = Column(Numeric(14, 2), nullable=False, default=0)
    criado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Movimentacao(Base):
    __tablename__ = "movimentacoes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    usuario_id = Column(String, ForeignKey("usuarios.id"), nullable=False)
    tipo = Column(String, nullable=False)
    descricao = Column(String, nullable=False)
    valor = Column(Numeric(14, 2), nullable=False)
    criado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc))


Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# Schemas (validação de entrada)
# ---------------------------------------------------------------------------

class RegistroIn(BaseModel):
    nome: str
    usuario: str
    senha: str

    @field_validator("nome", "usuario", "senha")
    @classmethod
    def nao_vazio(cls, v):
        if not v or not v.strip():
            raise ValueError("campo obrigatório")
        return v.strip()


class LoginIn(BaseModel):
    usuario: str
    senha: str


class ValorIn(BaseModel):
    valor: float

    @field_validator("valor")
    @classmethod
    def valor_positivo(cls, v):
        if v is None or v <= 0:
            raise ValueError("valor deve ser positivo")
        return v


class TransferenciaIn(BaseModel):
    destinatario: str
    valor: float

    @field_validator("valor")
    @classmethod
    def valor_positivo(cls, v):
        if v is None or v <= 0:
            raise ValueError("valor deve ser positivo")
        return v


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="Bagual Banco API")


# --- MODO DEBUG TEMPORÁRIO ---
# Isso faz a API devolver o traceback completo no corpo da resposta 500,
# só para facilitar o diagnóstico. Remover depois que o app estiver estável.
import traceback
from fastapi.responses import JSONResponse
from fastapi.requests import Request


@app.exception_handler(Exception)
async def debug_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": traceback.format_exc()},
    )
# --- FIM DO MODO DEBUG ---


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def erro(status_code: int, mensagem: str):
    raise HTTPException(status_code=status_code, detail=mensagem)


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------

def criar_token(usuario_id: str) -> str:
    expira = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    payload = {"sub": usuario_id, "exp": expira}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


bearer_scheme = HTTPBearer()


def usuario_atual(
    credenciais: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    token = credenciais.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario_id = payload.get("sub")
        if not usuario_id:
            raise JWTError()
    except JWTError:
        erro(401, "Sessão inválida ou expirada.")

    user = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not user:
        erro(401, "Sessão inválida ou expirada.")
    return user


# ---------------------------------------------------------------------------
# Rotas: auth
# ---------------------------------------------------------------------------

@app.post("/auth/registrar", status_code=201)
def registrar(dados: RegistroIn, db: Session = Depends(get_db)):
    existente = (
        db.query(Usuario)
        .filter(Usuario.usuario.ilike(dados.usuario))
        .first()
    )
    if existente:
        erro(409, "Esse usuário já existe.")

    novo = Usuario(
        nome=dados.nome,
        usuario=dados.usuario,
        senha_hash=hash_senha(dados.senha),
        saldo=Decimal("0"),
    )
    db.add(novo)
    db.commit()
    return {"usuario": novo.usuario}


@app.post("/auth/login")
def login(dados: LoginIn, db: Session = Depends(get_db)):
    user = (
        db.query(Usuario)
        .filter(Usuario.usuario.ilike(dados.usuario))
        .first()
    )
    if not user or not verificar_senha(dados.senha, user.senha_hash):
        erro(401, "Usuário ou senha incorretos.")

    token = criar_token(user.id)
    return {"access_token": token}


# ---------------------------------------------------------------------------
# Rotas: conta
# ---------------------------------------------------------------------------

@app.get("/conta/saldo")
def saldo(user: Usuario = Depends(usuario_atual)):
    return {"saldo": float(user.saldo)}


@app.get("/conta/extrato")
def extrato(user: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    itens = (
        db.query(Movimentacao)
        .filter(Movimentacao.usuario_id == user.id)
        .order_by(Movimentacao.criado_em.asc())
        .all()
    )
    return [
        {"descricao": m.descricao, "valor": float(m.valor)}
        for m in itens
    ]


@app.post("/conta/depositar")
def depositar(
    dados: ValorIn,
    user: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
):
    valor = Decimal(str(dados.valor))
    user.saldo = user.saldo + valor
    db.add(Movimentacao(
        usuario_id=user.id,
        tipo="deposito",
        descricao="Depósito",
        valor=valor,
    ))
    db.commit()
    return {"saldo": float(user.saldo)}


@app.post("/conta/sacar")
def sacar(
    dados: ValorIn,
    user: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
):
    valor = Decimal(str(dados.valor))
    if valor > user.saldo:
        erro(400, "Saldo insuficiente.")

    user.saldo = user.saldo - valor
    db.add(Movimentacao(
        usuario_id=user.id,
        tipo="saque",
        descricao="Saque",
        valor=-valor,
    ))
    db.commit()
    return {"saldo": float(user.saldo)}


@app.post("/conta/transferir")
def transferir(
    dados: TransferenciaIn,
    user: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
):
    if dados.destinatario.strip().lower() == user.usuario.lower():
        erro(400, "Não é possível transferir para você mesmo.")

    destino = (
        db.query(Usuario)
        .filter(Usuario.usuario.ilike(dados.destinatario.strip()))
        .first()
    )
    if not destino:
        erro(404, "Usuário de destino não encontrado.")

    valor = Decimal(str(dados.valor))
    if valor > user.saldo:
        erro(400, "Saldo insuficiente.")

    user.saldo = user.saldo - valor
    destino.saldo = destino.saldo + valor

    db.add(Movimentacao(
        usuario_id=user.id,
        tipo="transferencia_enviada",
        descricao=f"Transferência para @{destino.usuario}",
        valor=-valor,
    ))
    db.add(Movimentacao(
        usuario_id=destino.id,
        tipo="transferencia_recebida",
        descricao=f"Transferência de @{user.usuario}",
        valor=valor,
    ))
    db.commit()
    return {"saldo": float(user.saldo)}


@app.get("/")
def raiz():
    return {"status": "Bagual Banco API no ar"}

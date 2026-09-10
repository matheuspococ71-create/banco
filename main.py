from typing import List

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

import auth
import models
import schemas
from database import Base, engine, get_db

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Banco Digital API")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def usuario_atual(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.Usuario:
    nome_usuario = auth.decodificar_token(token)
    if nome_usuario is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido ou expirado.")
    conta = db.query(models.Usuario).filter(models.Usuario.usuario == nome_usuario).first()
    if conta is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuário não encontrado.")
    return conta


@app.post("/auth/registrar", status_code=201)
def registrar(dados: schemas.UsuarioCriar, db: Session = Depends(get_db)):
    if db.query(models.Usuario).filter(models.Usuario.usuario == dados.usuario).first():
        raise HTTPException(400, "Já existe uma conta com esse usuário.")
    conta = models.Usuario(
        usuario=dados.usuario,
        senha_hash=auth.gerar_hash_senha(dados.senha),
        nome=dados.nome,
        saldo=0.0,
    )
    db.add(conta)
    db.commit()
    return {"mensagem": "Conta criada com sucesso."}


@app.post("/auth/login", response_model=schemas.Token)
def login(dados: schemas.UsuarioLogin, db: Session = Depends(get_db)):
    conta = db.query(models.Usuario).filter(models.Usuario.usuario == dados.usuario).first()
    if not conta or not auth.verificar_senha(dados.senha, conta.senha_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuário ou senha inválidos.")
    token = auth.criar_token(conta.usuario)
    return schemas.Token(access_token=token)


@app.get("/conta/saldo", response_model=schemas.SaldoResposta)
def saldo(conta: models.Usuario = Depends(usuario_atual)):
    return schemas.SaldoResposta(saldo=conta.saldo)


@app.post("/conta/depositar", response_model=schemas.SaldoResposta)
def depositar(
    dados: schemas.ValorOperacao,
    conta: models.Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
):
    conta.saldo += dados.valor
    db.add(models.Movimentacao(usuario_id=conta.id, tipo="Depósito", valor=dados.valor))
    db.commit()
    db.refresh(conta)
    return schemas.SaldoResposta(saldo=conta.saldo)


@app.post("/conta/sacar", response_model=schemas.SaldoResposta)
def sacar(
    dados: schemas.ValorOperacao,
    conta: models.Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
):
    if conta.saldo < dados.valor:
        raise HTTPException(400, "Saldo insuficiente.")
    conta.saldo -= dados.valor
    db.add(models.Movimentacao(usuario_id=conta.id, tipo="Saque", valor=-dados.valor))
    db.commit()
    db.refresh(conta)
    return schemas.SaldoResposta(saldo=conta.saldo)


@app.post("/conta/transferir", response_model=schemas.SaldoResposta)
def transferir(
    dados: schemas.TransferenciaOperacao,
    conta: models.Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
):
    if dados.destino == conta.usuario:
        raise HTTPException(400, "Não é possível transferir para a própria conta.")
    destino = db.query(models.Usuario).filter(models.Usuario.usuario == dados.destino).first()
    if not destino:
        raise HTTPException(404, "Conta de destino não encontrada.")
    if conta.saldo < dados.valor:
        raise HTTPException(400, "Saldo insuficiente.")
    conta.saldo -= dados.valor
    destino.saldo += dados.valor
    db.add(models.Movimentacao(
        usuario_id=conta.id, tipo="Transferência enviada", valor=-dados.valor, detalhe=f"para {destino.usuario}",
    ))
    db.add(models.Movimentacao(
        usuario_id=destino.id, tipo="Transferência recebida", valor=dados.valor, detalhe=f"de {conta.usuario}",
    ))
    db.commit()
    db.refresh(conta)
    return schemas.SaldoResposta(saldo=conta.saldo)


@app.get("/conta/extrato", response_model=List[schemas.MovimentacaoResposta])
def extrato(
    conta: models.Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.Movimentacao)
        .filter(models.Movimentacao.usuario_id == conta.id)
        .order_by(models.Movimentacao.data.desc())
        .all()
    )

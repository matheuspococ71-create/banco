from datetime import datetime

from pydantic import BaseModel, Field


class UsuarioCriar(BaseModel):
    usuario: str = Field(min_length=3, max_length=50)
    senha: str = Field(min_length=6)
    nome: str = Field(min_length=1)


class UsuarioLogin(BaseModel):
    usuario: str
    senha: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SaldoResposta(BaseModel):
    saldo: float


class ValorOperacao(BaseModel):
    valor: float = Field(gt=0)


class TransferenciaOperacao(BaseModel):
    destino: str
    valor: float = Field(gt=0)


class MovimentacaoResposta(BaseModel):
    tipo: str
    valor: float
    detalhe: str
    data: datetime

    class Config:
        from_attributes = True

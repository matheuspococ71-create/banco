from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    usuario = Column(String, unique=True, index=True, nullable=False)
    senha_hash = Column(String, nullable=False)
    nome = Column(String, nullable=False)
    saldo = Column(Float, default=0.0, nullable=False)

    movimentacoes = relationship(
        "Movimentacao", back_populates="conta", foreign_keys="Movimentacao.usuario_id"
    )


class Movimentacao(Base):
    __tablename__ = "movimentacoes"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    tipo = Column(String, nullable=False)
    valor = Column(Float, nullable=False)
    detalhe = Column(String, default="")
    data = Column(DateTime(timezone=True), server_default=func.now())

    conta = relationship("Usuario", back_populates="movimentacoes", foreign_keys=[usuario_id])

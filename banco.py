import json
import os
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "contas.json")


class ContaExistente(Exception):
    pass


class ContaNaoEncontrada(Exception):
    pass


class SaldoInsuficiente(Exception):
    pass


class Banco:
    """Camada de dados e regras de negócio do sistema bancário."""

    def __init__(self, arquivo=DB_FILE):
        self.arquivo = arquivo
        self.contas = self._carregar()

    def _carregar(self):
        if os.path.exists(self.arquivo):
            with open(self.arquivo, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _salvar(self):
        with open(self.arquivo, "w", encoding="utf-8") as f:
            json.dump(self.contas, f, indent=2, ensure_ascii=False)

    def criar_conta(self, usuario, senha, nome_titular):
        if usuario in self.contas:
            raise ContaExistente("Já existe uma conta com esse usuário.")
        self.contas[usuario] = {
            "senha": senha,
            "titular": nome_titular,
            "saldo": 0.0,
            "extrato": [],
        }
        self._salvar()

    def autenticar(self, usuario, senha):
        conta = self.contas.get(usuario)
        return bool(conta and conta["senha"] == senha)

    def _registrar(self, usuario, tipo, valor, detalhe=""):
        registro = {
            "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "tipo": tipo,
            "valor": valor,
            "detalhe": detalhe,
        }
        self.contas[usuario]["extrato"].insert(0, registro)

    def depositar(self, usuario, valor):
        if valor <= 0:
            raise ValueError("O valor deve ser positivo.")
        self.contas[usuario]["saldo"] += valor
        self._registrar(usuario, "Depósito", valor)
        self._salvar()

    def sacar(self, usuario, valor):
        if valor <= 0:
            raise ValueError("O valor deve ser positivo.")
        if self.contas[usuario]["saldo"] < valor:
            raise SaldoInsuficiente("Saldo insuficiente.")
        self.contas[usuario]["saldo"] -= valor
        self._registrar(usuario, "Saque", -valor)
        self._salvar()

    def transferir(self, usuario_origem, usuario_destino, valor):
        if usuario_destino not in self.contas:
            raise ContaNaoEncontrada("Conta de destino não encontrada.")
        if usuario_destino == usuario_origem:
            raise ValueError("Não é possível transferir para a própria conta.")
        if valor <= 0:
            raise ValueError("O valor deve ser positivo.")
        if self.contas[usuario_origem]["saldo"] < valor:
            raise SaldoInsuficiente("Saldo insuficiente.")
        self.contas[usuario_origem]["saldo"] -= valor
        self.contas[usuario_destino]["saldo"] += valor
        self._registrar(usuario_origem, "Transferência enviada", -valor, f"para {usuario_destino}")
        self._registrar(usuario_destino, "Transferência recebida", valor, f"de {usuario_origem}")
        self._salvar()

    def saldo(self, usuario):
        return self.contas[usuario]["saldo"]

    def extrato(self, usuario):
        return self.contas[usuario]["extrato"]

    def titular(self, usuario):
        return self.contas[usuario]["titular"]

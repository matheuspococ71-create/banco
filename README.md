# Banco Digital — App de Sistema Bancário (CustomTkinter)

## Como rodar

```bash
pip install customtkinter
python main.py
```

## O que o app faz

- **Login e cadastro** de contas (usuário/senha).
- **Depósito**, **saque** e **transferência** entre contas.
- **Extrato** com histórico de todas as movimentações.
- Dados salvos automaticamente em `contas.json` (criado na primeira execução), então tudo persiste entre uma execução e outra.

## Estrutura

- `banco.py` — regras de negócio (classe `Banco`): criação de conta, autenticação, depósito, saque, transferência, extrato. Não depende de interface gráfica, então dá pra testar ou reaproveitar separado.
- `main.py` — interface gráfica em CustomTkinter, com três telas: Login, Cadastro e Dashboard.

## Próximos passos possíveis

- Trocar o JSON por SQLite se o volume de contas crescer.
- Hash de senha (ex: `hashlib` ou `bcrypt`) em vez de texto puro — hoje as senhas ficam em texto simples no `contas.json`.
- Validação de força de senha e confirmação de senha no cadastro.
- Exportar extrato em PDF/CSV.

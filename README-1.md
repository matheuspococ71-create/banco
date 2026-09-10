# Banco Digital API

Backend do sistema bancário, feito pra servir tanto um app mobile (Flutter/React Native) quanto qualquer outro cliente.

## Como rodar

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

A API sobe em `http://127.0.0.1:8000`. Documentação interativa (dá pra testar tudo direto no navegador) em `http://127.0.0.1:8000/docs`.

## Diferenças em relação à versão desktop

- Banco de dados real (SQLite, arquivo `banco.db`) em vez de JSON.
- Senha guardada com hash (bcrypt), nunca em texto puro.
- Autenticação por token (JWT): você faz login uma vez e usa o token nas próximas requisições.

## Endpoints

| Método | Rota | O que faz | Precisa de token? |
|---|---|---|---|
| POST | `/auth/registrar` | Cria conta (`usuario`, `senha`, `nome`) | Não |
| POST | `/auth/login` | Retorna o token de acesso | Não |
| GET | `/conta/saldo` | Saldo da conta logada | Sim |
| POST | `/conta/depositar` | Deposita (`valor`) | Sim |
| POST | `/conta/sacar` | Saca (`valor`) | Sim |
| POST | `/conta/transferir` | Transfere (`destino`, `valor`) | Sim |
| GET | `/conta/extrato` | Histórico de movimentações | Sim |

Nas rotas que precisam de token, envie o header:
```
Authorization: Bearer SEU_TOKEN_AQUI
```

## Testando rapidinho pelo terminal

```bash
# Criar conta
curl -X POST http://127.0.0.1:8000/auth/registrar -H "Content-Type: application/json" -d "{\"usuario\":\"joao\",\"senha\":\"123456\",\"nome\":\"João Silva\"}"

# Login (retorna o token)
curl -X POST http://127.0.0.1:8000/auth/login -H "Content-Type: application/json" -d "{\"usuario\":\"joao\",\"senha\":\"123456\"}"

# Ver saldo (troque SEU_TOKEN pelo token recebido no login)
curl http://127.0.0.1:8000/conta/saldo -H "Authorization: Bearer SEU_TOKEN"
```

## Próximo passo: o app mobile

Com essa API rodando, o app em Flutter ou React Native só precisa fazer requisições HTTP pra esses endpoints — a mesma lógica de negócio (saldo, saque, depósito, transferência) já está pronta e testada aqui, não precisa ser reescrita no app.

Antes de colocar em produção de verdade: trocar a `SECRET_KEY` fixa por uma variável de ambiente segura, e rodar atrás de HTTPS.

# Lumina Chat / Free GPT

API em FastAPI com autenticação (JWT + banco de dados) e integração com IA via OpenRouter. O frontend (Lumina Chat) é servido pela própria API a partir de `app/static/`.

## Estrutura

```
app/
  main.py          # API FastAPI (auth, chat, arquivos estáticos)
  config.py        # Carrega .env e variáveis de ambiente
  models.py        # Modelos SQLAlchemy (User) e criação de engine/tabelas
  auth.py          # Hash de senha e geração/validação de JWT
  static/          # Frontend (index.html, assets, lumina-video)
  .env             # Variáveis de ambiente (NÃO versionado)
  .env.example     # Modelo de variáveis de ambiente
```

## Pré-requisitos

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (gerenciador de pacotes usado no projeto)

## Configuração do `.env`

O arquivo `app/.env` **não é versionado** (está no `.gitignore`) — se você "esquecer" as configurações, é aqui que elas moram. Copie `app/.env.example` para `app/.env` e preencha:

```
OPENROUTER_API_KEY=sk-or-v1-...       # chave da API do OpenRouter (openrouter.ai)
JWT_SECRET=uma-string-longa-aleatoria # segredo usado para assinar os tokens JWT
DATABASE_URL=postgresql://...          # ver seção "Banco de dados" abaixo
```

Se `DATABASE_URL` não for definida, a aplicação usa SQLite local em `app/data/app.db` automaticamente (bom para testes rápidos, mas os dados não persistem em serviços como o Render).

## Banco de dados

O banco em uso é **PostgreSQL hospedado no Neon** (https://neon.tech).

- **Projeto:** `neondb`
- **Host:** `ep-red-wildflower-aeq7a0fv-pooler.c-2.us-east-2.aws.neon.tech` (endpoint *pooler*, região `us-east-2`)
- **Usuário:** `neondb_owner`
- **Onde ver/gerenciar:** painel do Neon → console.neon.tech → login com a conta usada para criar o projeto → aba **Connection Details** para pegar a connection string completa (com senha) a qualquer momento, ou o **SQL Editor** para consultar dados direto pelo navegador.
- A connection string completa (com senha) fica **somente** em `app/.env`, na variável `DATABASE_URL`. Não é possível recuperá-la aqui por segurança — caso perca o `.env`, gere uma nova senha/connection string no painel do Neon (Connection Details → Reset password) e atualize o `.env`.
- A URL do Neon já vem com `sslmode=require&channel_binding=require` — mantenha esses parâmetros.
- A tabela usada é `users` (id, email, name, password_hash, created_at, active), criada automaticamente pela aplicação ao iniciar (`create_tables` em `models.py`), sem precisar rodar migração manual.

## Como subir a aplicação localmente

```bash
cd app
uv sync                      # instala as dependências (primeira vez)
uv run uvicorn main:app --reload
```

A aplicação sobe em **http://127.0.0.1:8000**:

- `/` — frontend Lumina Chat
- `/docs` — documentação interativa (Swagger) dos endpoints
- `/auth/register`, `/auth/login`, `/auth/me` — autenticação
- `/send_message` — envia mensagem para a IA (rota protegida, exige JWT)

Alternativa sem `uv` (usando o `.venv` já criado):

```powershell
.venv\Scripts\python.exe -m uvicorn main:app --reload
```

## Deploy (Render)

O projeto tem um Blueprint (`render.yaml`, na raiz do repositório) que descreve o serviço inteiro como código — build, start command, health check e variáveis de ambiente. Isso significa que o deploy é reprodutível e não depende de configuração manual clicada no painel.

1. No [dashboard do Render](https://dashboard.render.com), **New > Blueprint** e conecte o repositório `debiny/free-gpt`.
2. O Render lê o `render.yaml` automaticamente e propõe o serviço `lumina-chat` (Web Service Python, `rootDir: app`, build `pip install -r requirements.txt`, start `uvicorn main:app --host 0.0.0.0 --port $PORT`).
3. Antes de confirmar, preencher as variáveis marcadas como secretas (o Render pede na tela de criação do Blueprint):
   - `OPENROUTER_API_KEY`
   - `DATABASE_URL` (a mesma connection string do Neon usada localmente)
   - `JWT_SECRET` é gerado automaticamente pelo Render (`generateValue: true`) — não precisa definir.
4. Clicar em **Apply**. A partir daí, todo `git push` na branch conectada dispara um novo deploy automaticamente (`autoDeploy: true`).

Como o banco já é o Neon (externo), o mesmo banco é compartilhado entre ambiente local e produção — não é necessário um banco separado para deploy.

### Manutenção

- **Atualizar o app:** só dar push na branch principal; o Render builda e sobe sozinho.
- **Ver logs:** aba *Logs* do serviço no painel do Render (útil para depurar erros do `/send_message` ou de conexão com o banco).
- **Girar segredos:** trocar `OPENROUTER_API_KEY`/`DATABASE_URL` na aba *Environment* do serviço — não requer novo deploy manual, o Render reinicia sozinho.
- **Plano free:** o serviço "dorme" após períodos de inatividade e a primeira requisição fica mais lenta ao acordar. Se isso for um problema, migrar para um plano pago no mesmo `render.yaml` (campo `plan`).

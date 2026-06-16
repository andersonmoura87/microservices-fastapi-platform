# microservices-fastapi-platform

[![CI](https://github.com/andersonmoura87/microservices-fastapi-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/andersonmoura87/microservices-fastapi-platform/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Prometheus](https://img.shields.io/badge/Prometheus-metrics-E6522C?logo=prometheus&logoColor=white)](https://prometheus.io/)

Uma plataforma de microsserviços pronta para produção, construída com FastAPI, Docker, PostgreSQL, Redis e GitHub Actions CI/CD.

## Arquitetura

```
Cliente
  │
  ▼
┌─────────────────────────────┐
│     API Gateway  :8000      │  ← Ponto único de entrada, roteamento + agregação de health
└──────────┬──────────────────┘
           │
    ┌──────┴──────┐
    ▼             ▼
┌────────────┐  ┌────────────┐
│User Service│  │Data Service│
│   :8001    │  │   :8002    │
└─────┬──────┘  └─────┬──────┘
      │               │
      ▼               ▼
┌──────────┐   ┌────────────────┐
│PostgreSQL│   │PostgreSQL Redis│
└──────────┘   └────────────────┘
```

Cada serviço é totalmente isolado — schema de banco de dados independente, container independente e endpoint de health independente.

## Stack

| Camada | Tecnologia |
|---|---|
| API | FastAPI 0.111 + Python 3.11 |
| ORM | SQLAlchemy 2.0 + Alembic |
| Banco de dados | PostgreSQL 15 |
| Cache | Redis 7 |
| Containers | Docker + Docker Compose |
| Métricas | Prometheus (`/metrics` em cada serviço) |
| CI/CD | GitHub Actions |

## Início Rápido

```bash
git clone https://github.com/andersonmoura87/microservices-fastapi-platform
cd microservices-fastapi-platform

cp .env.example .env
docker compose up --build
```

Os serviços ficarão disponíveis em:

- API Gateway → http://localhost:8000
- Swagger UI  → http://localhost:8000/docs
- Prometheus  → http://localhost:9090
- Grafana     → http://localhost:3000 (admin / admin)

## Endpoints da API

### Usuários
```
POST   /users           Criar usuário
GET    /users/{id}      Buscar usuário por ID
PUT    /users/{id}      Atualizar usuário
DELETE /users/{id}      Remover usuário
```

### Autenticação
```
POST   /auth/token      Emite um JWT para um usuário existente (por e-mail)
```

### Dados
```
POST   /data/ingest     Ingerir um registro
GET    /data/records    Listar registros (cacheado via Redis)
GET    /data/{id}       Buscar registro por ID
```

### Plataforma
```
GET    /health          Healthcheck agregado (gateway + todos os serviços)
GET    /metrics         Métricas do Prometheus
```

## Estrutura do Projeto

```
microservices-fastapi-platform/
├── services/
│   ├── api-gateway/
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   └── logging_config.py
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   ├── .dockerignore
│   │   └── requirements.txt
│   ├── user-service/
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   ├── logging_config.py
│   │   │   ├── auth.py
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── crud.py
│   │   │   └── database.py
│   │   ├── alembic/
│   │   │   ├── env.py
│   │   │   └── versions/
│   │   ├── tests/
│   │   ├── alembic.ini
│   │   ├── entrypoint.sh
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── data-service/
│       ├── app/
│       │   ├── main.py
│       │   ├── config.py
│       │   ├── logging_config.py
│       │   ├── models.py
│       │   ├── schemas.py
│       │   ├── crud.py
│       │   ├── cache.py
│       │   └── database.py
│       ├── alembic/
│       ├── tests/
│       ├── alembic.ini
│       ├── entrypoint.sh
│       ├── Dockerfile
│       └── requirements.txt
├── infra/
│   ├── postgres/
│   │   └── init.sql
│   ├── prometheus/
│   │   └── prometheus.yml
│   └── grafana/
│       ├── datasources/
│       └── dashboards/
├── .github/
│   ├── workflows/
│   │   └── ci.yml
│   └── dependabot.yml
├── docker-compose.yml
├── Makefile
├── ruff.toml
├── .env.example
└── README.md
```

## Pipeline de CI/CD

```
push para main / PR
       │
       ▼
  ┌─────────┐   ┌─────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
  │  Lint   │ → │  Teste  │ → │ Build Images │ → │ Scan (Trivy) │ → │  Push para  │
  │(ruff)   │   │(pytest) │   │  (3 serviços)│   │ HIGH/CRITICAL│   │  GHCR       │
  └─────────┘   └─────────┘   └──────────────┘   └──────────────┘   └──────────────┘
```

O pipeline roda a cada push para a `main` e em todos os pull requests. O job de testes
roda em **matrix** pelos três serviços, sobe Postgres + Redis como serviços do GitHub Actions
e aplica as migrations (`alembic upgrade head`) antes do `pytest`. O `build` só publica a imagem
no GHCR se o scan de vulnerabilidades do Trivy passar (falha em HIGH/CRITICAL com fix disponível).
O `dependabot` mantém as dependências pip, as imagens Docker e as GitHub Actions atualizadas.

## Observabilidade

Cada serviço expõe `/metrics` no formato do Prometheus. A configuração em `infra/prometheus` coleta (scrape) os três serviços a cada 15 segundos. O Grafana já vem pré-configurado com um dashboard mostrando:

- Taxa de requisições por serviço
- Latência de resposta P95 por serviço
- Razão de cache hit/miss (data-service)
- Taxa de respostas 5xx por serviço

O datasource do Prometheus e o dashboard são provisionados automaticamente
(`infra/grafana/datasources` e `infra/grafana/dashboards`) — nada de configuração manual.

## Variáveis de Ambiente

Copie `.env.example` para `.env` e ajuste conforme necessário:

```env
POSTGRES_USER=platform
POSTGRES_PASSWORD=changeme
POSTGRES_DB=platform
REDIS_URL=redis://redis:6379/0
CACHE_TTL=300
JWT_SECRET=change-this-in-production
LOG_LEVEL=INFO
```

## Migrations

O schema é gerenciado com **Alembic** — `create_all` não é usado em runtime. Cada serviço com
banco tem o seu próprio histórico de migrations em `alembic/versions/` e roda
`alembic upgrade head` no `entrypoint.sh` antes de subir o Uvicorn, garantindo que o container
nunca atende tráfego com o schema desatualizado.

```bash
# Gerar uma nova migration a partir das mudanças nos models
cd services/user-service
alembic revision --autogenerate -m "add phone column"

# Aplicar nos containers em execução
make migrate
```

## Executando os Testes

```bash
# Todos os serviços de uma vez
make test

# Ou um serviço específico (requer postgres + redis em execução)
cd services/user-service
pip install -r requirements.txt
pytest tests/ -v
```

## Comandos (Makefile)

```bash
make up        # build + sobe a stack (detached)
make down      # derruba a stack
make logs      # tail dos logs
make lint      # ruff em todos os serviços
make test      # roda os testes de todos os serviços
make migrate   # aplica as migrations nos containers
make clean     # derruba a stack e remove os volumes
```

## Segurança

- Containers rodam como usuário **não-root** (`appuser`), com build **multi-stage** para imagem enxuta
- Imagens são escaneadas com **Trivy** no CI; HIGH/CRITICAL com fix disponível **quebram o build**
- Segredos só via variáveis de ambiente / `pydantic-settings` — nunca hardcoded
- **Dependabot** abre PRs semanais para pip, Docker e GitHub Actions
- Logs **estruturados em JSON** com `structlog`, prontos para ingestão por um stack de logs

## Decisões de Design

**Por que uma única instância PostgreSQL com schemas separados em vez de bancos separados?**
É mais fácil de operar em um setup de nó único, mantendo ainda o isolamento lógico. Em um ambiente de produção real, cada serviço teria sua própria instância de banco de dados.

**Por que Redis para cache no data-service?**
O padrão de consultas do data-service é predominantemente de leitura (read-heavy). O cache baseado em TTL do Redis evita acessos redundantes ao banco para registros consultados com frequência, reduzindo significativamente a latência p95.

**Por que httpx para chamadas entre serviços no gateway?**
O httpx suporta async nativamente, o que mantém o gateway não bloqueante mesmo ao distribuir chamadas (fan-out) para múltiplos serviços downstream no endpoint de agregação `/health`.

## Contribuindo

1. Faça um fork do repositório
2. Crie uma branch de feature (`git checkout -b feat/sua-feature`)
3. Faça commits das suas alterações seguindo o padrão [Conventional Commits](https://www.conventionalcommits.org/)
4. Faça push e abra um Pull Request

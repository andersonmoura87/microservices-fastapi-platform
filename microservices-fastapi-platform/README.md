# microservices-fastapi-platform

[![CI](https://github.com/andersonmoura87/microservices-fastapi-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/andersonmoura87/microservices-fastapi-platform/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-Kustomize-326CE5?logo=kubernetes&logoColor=white)](https://kubernetes.io/)
[![Prometheus](https://img.shields.io/badge/Prometheus-metrics-E6522C?logo=prometheus&logoColor=white)](https://prometheus.io/)
[![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-tracing-425CC7?logo=opentelemetry&logoColor=white)](https://opentelemetry.io/)
[![Grafana](https://img.shields.io/badge/Grafana-LGTM-F46800?logo=grafana&logoColor=white)](https://grafana.com/)

Uma plataforma de microsserviços pronta para produção, construída com FastAPI, Docker, PostgreSQL, Redis e GitHub Actions CI/CD.

## Arquitetura

Diagrama de contêineres (estilo C4 — nível 2). O cliente só fala com o API Gateway;
os serviços são isolados por schema próprio no Postgres e nunca se chamam diretamente.

```mermaid
flowchart TB
    client(["Cliente / SPA"])

    subgraph edge["Borda"]
        gw["API Gateway :8000<br/>roteamento · agregação de /health · /metrics"]
    end

    subgraph services["Serviços de aplicação"]
        us["User Service :8001<br/>CRUD de usuários · emissão de JWT"]
        ds["Data Service :8002<br/>ingestão · listagem com cache"]
    end

    subgraph state["Estado (isolado por schema)"]
        pg[("PostgreSQL 15<br/>schemas: users · data")]
        rd[("Redis 7<br/>cache versionado (TTL)")]
    end

    subgraph obs["Observabilidade"]
        prom["Prometheus"]
        tempo["Tempo (traces)"]
        loki["Loki (logs)"]
        graf["Grafana"]
    end

    client -->|HTTP| gw
    gw -->|/users, /auth| us
    gw -->|/data| ds
    us --> pg
    ds --> pg
    ds --> rd

    prom -. scrape /metrics .-> gw
    prom -. scrape /metrics .-> us
    prom -. scrape /metrics .-> ds
    gw & us & ds -. OTLP traces .-> tempo
    gw & us & ds -. stdout JSON .-> loki
    graf --> prom
    graf --> tempo
    graf --> loki
```

Cada serviço é totalmente isolado — schema de banco de dados independente, container independente e endpoint de health independente.

### Fluxo de uma requisição (ingestão + cache)

Sequência do `POST /data/ingest` seguido de `GET /data/records`, mostrando a invalidação
de cache na escrita e o caminho de leitura (miss → popula cache, hit → serve do Redis).

```mermaid
sequenceDiagram
    autonumber
    participant C as Cliente
    participant G as API Gateway
    participant D as Data Service
    participant R as Redis
    participant P as PostgreSQL

    C->>G: POST /data/ingest
    G->>D: encaminha (trace context propagado)
    D->>P: INSERT record
    D->>R: DEL v1:data:records  (invalida cache)
    D-->>C: 201 Created

    C->>G: GET /data/records
    G->>D: encaminha
    D->>R: GET v1:data:records
    alt cache miss
        R-->>D: (vazio)
        D->>P: SELECT records
        D->>R: SET v1:data:records (TTL)
        D-->>C: 200 + lista
    else cache hit
        R-->>D: lista cacheada
        D-->>C: 200 + lista
    end
```

## Stack

| Camada | Tecnologia |
|---|---|
| API | FastAPI 0.111 + Python 3.11 |
| ORM | SQLAlchemy 2.0 + Alembic |
| Banco de dados | PostgreSQL 15 |
| Cache | Redis 7 |
| Containers | Docker + Docker Compose |
| Orquestração | Kubernetes (Kustomize: base + overlays dev/prod) |
| Métricas | Prometheus (`/metrics` em cada serviço) |
| Alertas | Prometheus rules + Alertmanager (SLOs) |
| Tracing | OpenTelemetry → Tempo |
| Logs | structlog (JSON) → Loki via Promtail |
| Dashboards | Grafana (datasources provisionados) |
| GitOps | ArgoCD (overlays dev/prod) |
| CI/CD | GitHub Actions + Trivy + cosign + SBOM + Dependabot |
| Carga | k6 (thresholds de SLO) |

## Início Rápido

```bash
git clone https://github.com/andersonmoura87/microservices-fastapi-platform
cd microservices-fastapi-platform

cp .env.example .env
docker compose up --build
```

Os serviços ficarão disponíveis em:

- API Gateway   → http://localhost:8000
- Swagger UI    → http://localhost:8000/docs
- Prometheus    → http://localhost:9090
- Alertmanager  → http://localhost:9093
- Grafana       → http://localhost:3000 (admin / admin)

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
│   │   │   ├── logging_config.py
│   │   │   ├── tracing.py
│   │   │   └── ratelimit.py
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   ├── .dockerignore
│   │   └── requirements.txt
│   ├── user-service/
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   ├── logging_config.py
│   │   │   ├── tracing.py
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
│       │   ├── tracing.py
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
│   │   ├── prometheus.yml
│   │   └── rules/slo.yml
│   ├── alertmanager/
│   │   └── alertmanager.yml
│   ├── tempo/
│   │   └── tempo.yaml
│   ├── loki/
│   │   └── loki-config.yaml
│   ├── promtail/
│   │   └── promtail-config.yaml
│   └── grafana/
│       ├── datasources/
│       └── dashboards/
├── deploy/
│   ├── k8s/
│   │   ├── base/
│   │   └── overlays/
│   │       ├── dev/
│   │       └── prod/
│   └── argocd/
│       ├── project.yaml
│       ├── application-dev.yaml
│       └── application-prod.yaml
├── load/
│   └── k6-smoke.js
├── .github/
│   ├── workflows/
│   │   └── ci.yml
│   └── dependabot.yml
├── docker-compose.yml
├── Makefile
├── ruff.toml
├── .pre-commit-config.yaml
├── .secrets.baseline
├── .env.example
└── README.md
```

## Pipeline de CI/CD

```mermaid
flowchart LR
    push(["push na main / PR"]) --> lint["Lint<br/>ruff + hadolint"]
    lint --> test["Test (matrix 3 serviços)<br/>Postgres + Redis · alembic · pytest"]
    test --> build["Build Images<br/>(3 serviços)"]
    build --> scan["Scan Trivy<br/>HIGH/CRITICAL → falha"]
    scan --> pushimg["Push GHCR<br/>(só na main)"]
    pushimg --> sign["Cosign sign<br/>(keyless / OIDC)"]
    sign --> sbom["SBOM (syft)<br/>+ attest"]
```

O pipeline roda a cada push para a `main` e em todos os pull requests. `ruff` e `hadolint`
(lint de Dockerfile) rodam em paralelo; o job de testes roda em **matrix** pelos três serviços,
sobe Postgres + Redis como serviços do GitHub Actions e aplica as migrations
(`alembic upgrade head`) antes do `pytest`. O `build` só publica no GHCR se o scan do Trivy
passar (falha em HIGH/CRITICAL com fix disponível). Após o push, cada imagem é **assinada com
cosign** (keyless via OIDC) e tem seu **SBOM gerado (syft) e anexado como attestation**.
O `dependabot` mantém pip, imagens Docker e GitHub Actions atualizados.

## Observabilidade

Os três pilares (métricas, traces e logs) ficam no mesmo Grafana, com datasources
provisionados automaticamente — nada de configuração manual.

**Métricas (Prometheus).** Cada serviço expõe `/metrics`; o Prometheus coleta os três a cada
15s. O dashboard provisionado mostra:

- Taxa de requisições por serviço
- Latência de resposta P95 por serviço
- Razão de cache hit/miss (data-service)
- Taxa de respostas 5xx por serviço

**Tracing (OpenTelemetry → Tempo).** FastAPI e o cliente httpx do gateway são instrumentados
com OpenTelemetry; o trace context é propagado gateway → serviços, então um `POST /data/ingest`
aparece como um único trace ponta-a-ponta. O exporter usa OTLP/HTTP e só liga se
`OTEL_EXPORTER_OTLP_ENDPOINT` estiver definido (zero overhead quando ausente, ex.: em testes).

**Logs (structlog → Loki).** Os logs saem em **JSON estruturado** no stdout; o Promtail coleta
os logs dos containers e envia ao Loki. Cada log carrega `trace_id`/`span_id`, e o Grafana está
configurado para **pivotar de um log direto para o trace correspondente** no Tempo (e vice-versa).

**Alertas e SLOs (Prometheus + Alertmanager).** As regras em `infra/prometheus/rules/slo.yml`
definem os SLIs como *recording rules* e disparam alertas para o Alertmanager:

| Alerta | Condição | Severidade |
|---|---|---|
| `ServiceDown` | `up == 0` por 2m | critical |
| `HighErrorRate` | 5xx > 5% por 5m | critical |
| `ErrorBudgetBurn` | 5xx > 1% por 15m | warning |
| `HighLatencyP95` | p95 > 300ms por 10m | warning |

O Alertmanager agrupa, faz inhibition (um `critical` silencia o `warning` equivalente) e
encaminha para o receiver configurado (Slack/PagerDuty/webhook — deixei um webhook placeholder
para subir sem credenciais).

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
OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4318
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
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
make load      # roda o teste de carga k6 contra o gateway
make hooks     # instala os pre-commit hooks
make clean     # derruba a stack e remove os volumes
```

## Rate limiting & graceful shutdown

O gateway aplica **rate limiting por IP** com um contador de janela fixa no **Redis** — o estado
fica no Redis (não na memória do processo) justamente para o limite ser consistente entre os
múltiplos workers/réplicas. O limiter **falha aberto**: se o Redis cair, as requisições passam,
para não transformar uma indisponibilidade de cache em indisponibilidade da API. Ao exceder,
responde `429` com `Retry-After`. Configurável via `RATE_LIMIT_REQUESTS` / `RATE_LIMIT_WINDOW`.

No **shutdown**, o `lifespan` fecha o cliente httpx (pool) e a conexão Redis de forma limpa.
No Kubernetes, o gateway tem `terminationGracePeriodSeconds: 30` e um hook `preStop` para
**drenar conexões em andamento** antes do `SIGTERM`.

## Teste de carga (k6)

`load/k6-smoke.js` exercita o caminho de escrita (`/data/ingest`) e leitura (`/data/records`)
através do gateway. Os **thresholds codificam os SLOs** (p95 < 300ms, erro < 1%), então o k6 sai
com código de erro se forem violados — pronto para virar gate em CI.

```bash
make up                          # com a stack no ar
make load                        # k6 run load/k6-smoke.js
k6 run -e BASE_URL=http://host load/k6-smoke.js   # apontando para outro alvo
```

## GitOps (ArgoCD)

`deploy/argocd/` traz um `AppProject` e duas `Application` apontando para os overlays do Git
(a fonte da verdade). O ambiente **dev** sincroniza automaticamente (`prune` + `selfHeal`);
**prod** é sync manual (promoção feita por uma pessoa).

```bash
kubectl apply -f deploy/argocd/project.yaml
kubectl apply -f deploy/argocd/application-dev.yaml
```

## Kubernetes

Os manifests vivem em `deploy/k8s/` usando **Kustomize** (base + overlays por ambiente),
sem precisar de Helm. A base traz, para cada serviço de aplicação:

- `Deployment` com **RollingUpdate** `maxUnavailable: 0` (zero-downtime)
- `readinessProbe` + `livenessProbe` em `/health`
- `resources.requests` e `resources.limits`
- `securityContext` endurecido: non-root, `readOnlyRootFilesystem`, `drop: [ALL]`, seccomp `RuntimeDefault`
- `HorizontalPodAutoscaler` (CPU 70%) e `PodDisruptionBudget`
- `Service` interno + `Ingress` (nginx) expondo só o gateway

Os overlays ajustam réplicas/recursos por ambiente; `prod` ainda fixa as imagens em uma tag
imutável (`v1.0.0`) em vez de `:latest`.

```bash
# Renderizar e revisar o que seria aplicado
kubectl kustomize deploy/k8s/overlays/dev

# Aplicar em um cluster (ex.: kind / minikube)
kubectl apply -k deploy/k8s/overlays/dev
kubectl apply -k deploy/k8s/overlays/prod
```

> Segredos aqui são apenas valores de demonstração. Em um cluster real eles viriam de um
> gerenciador externo (External Secrets Operator / Vault / SOPS), nunca versionados em texto puro.
> As migrations rodam pelo `entrypoint` da imagem; em produção, o ideal é promovê-las a um
> `Job`/hook de pré-deploy para evitar corrida entre réplicas.

## Segurança

- Containers rodam como usuário **não-root** (`appuser`), com build **multi-stage** para imagem enxuta
- No Kubernetes: `readOnlyRootFilesystem`, `allowPrivilegeEscalation: false`, `drop: [ALL]` e seccomp `RuntimeDefault`
- Imagens são escaneadas com **Trivy** no CI; HIGH/CRITICAL com fix disponível **quebram o build**
- **Supply chain:** imagens **assinadas com cosign** (keyless/OIDC) + **SBOM (syft)** anexado como attestation
- **`hadolint`** lint dos Dockerfiles no CI; **`pre-commit`** com ruff, `detect-secrets`, hadolint e checagens de YAML
- Segredos só via variáveis de ambiente / `pydantic-settings` — nunca hardcoded
- **Dependabot** abre PRs semanais para pip, Docker e GitHub Actions
- Logs **estruturados em JSON** com `structlog`, correlacionados a traces via `trace_id`

## Decisões de Design

**Por que uma única instância PostgreSQL com schemas separados em vez de bancos separados?**
É mais fácil de operar em um setup de nó único, mantendo ainda o isolamento lógico. Em um ambiente de produção real, cada serviço teria sua própria instância de banco de dados.

**Por que Redis para cache no data-service?**
O padrão de consultas do data-service é predominantemente de leitura (read-heavy). O cache baseado em TTL do Redis evita acessos redundantes ao banco para registros consultados com frequência, reduzindo significativamente a latência p95.

**Por que httpx para chamadas entre serviços no gateway?**
O httpx suporta async nativamente, o que mantém o gateway não bloqueante mesmo ao distribuir chamadas (fan-out) para múltiplos serviços downstream no endpoint de agregação `/health`.

**Por que OpenTelemetry + Tempo/Loki em vez de só métricas?**
Métricas dizem *que* algo está lento, mas não *onde*. Com tracing distribuído dá pra seguir uma
requisição pelo gateway até o banco em um único trace, e o `trace_id` nos logs fecha o ciclo:
de um alerta no Prometheus → trace no Tempo → logs daquela request no Loki, tudo no mesmo Grafana.

**Por que Kustomize em vez de Helm?**
Para esta plataforma, overlays declarativos (sem templating/`values.yaml`) deixam o diff por
ambiente explícito e legível, e casam bem com fluxo GitOps. Helm faria mais sentido se a intenção
fosse empacotar e distribuir o chart para terceiros.

## Contribuindo

1. Faça um fork do repositório
2. Crie uma branch de feature (`git checkout -b feat/sua-feature`)
3. Faça commits das suas alterações seguindo o padrão [Conventional Commits](https://www.conventionalcommits.org/)
4. Faça push e abra um Pull Request

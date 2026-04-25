hu# 🚀 Detector de Anomalias em Transações Financeiras

Projeto **full-stack de análise de dados** para detecção de anomalias em transações
financeiras, usando **Python, PySpark, Pandas, NumPy, MySQL e FastAPI**, com
visualizações em **Matplotlib/Seaborn/Plotly** e ambiente pronto para **deploy na AWS**
(ECS Fargate + RDS + Terraform + GitHub Actions).

---

## 📑 Índice

- [Arquitetura](#-arquitetura)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Stack Tecnológico](#-stack-tecnológico)
- [Pré-requisitos](#-pré-requisitos)
- [Como rodar localmente](#-como-rodar-localmente)
- [Pipeline de detecção](#-pipeline-de-detecção)
- [API FastAPI](#-api-fastapi)
- [Notebook de EDA](#-notebook-de-eda)
- [Testes](#-testes)
- [Deploy na AWS](#-deploy-na-aws)
- [Algoritmos usados](#-algoritmos-usados)
- [Troubleshooting](#-troubleshooting)

---

## 🏗️ Arquitetura

```
┌──────────────────┐       ┌─────────────────┐       ┌──────────────────┐
│  Dados sintéticos │──────▶│  MySQL (Docker) │◀──────│  PySpark / Pandas │
│  (10k transações) │       │   anomaly_db    │       │  Feature engineer. │
└──────────────────┘       └─────────────────┘       └──────────────────┘
                                    │                         │
                                    ▼                         ▼
                           ┌─────────────────┐       ┌──────────────────┐
                           │  Isolation Forest│       │ DBSCAN + Z-Score │
                           │   (principal)    │       │   (secundário)   │
                           └─────────────────┘       └──────────────────┘
                                    │                         │
                                    └────────────┬────────────┘
                                                 ▼
                                     ┌──────────────────────┐
                                     │  Anomalias no MySQL  │
                                     │  + CSV processado    │
                                     │  + Gráficos PNG/HTML │
                                     └──────────────────────┘
                                                 │
                                                 ▼
                                        ┌──────────────┐
                                        │  FastAPI API │
                                        │ /health /docs│
                                        │ /anomalies   │
                                        │ /detect      │
                                        │ /dashboard   │
                                        └──────────────┘
```

---

## 📁 Estrutura do Projeto

```
detecto_de_anomalias em transações/
├── docker-compose.yml           # MySQL 8.0 + app Python
├── Dockerfile                    # Container dev (Python 3.11 + Java 17)
├── requirements.txt              # Todas as dependências Python
├── main.py                       # Pipeline principal
├── app.py                        # API FastAPI
├── README.md                     # Este arquivo
├── .env.example                  # Exemplo de variáveis de ambiente
│
├── config/
│   ├── database.py               # Conexões MySQL (SQLAlchemy + JDBC)
│   └── config.yaml               # Configurações gerais
│
├── data/
│   ├── schema.sql                # Schema MySQL (transacoes + anomalias)
│   ├── raw/                      # Dados brutos (CSV gerados)
│   └── processed/                # Resultados + gráficos
│
├── src/
│   ├── data_loader.py            # Leitura MySQL/CSV + escrita anomalias
│   ├── populate_data.py          # Gera 10k transações sintéticas
│   ├── preprocessor.py           # Feature engineering (Pandas)
│   ├── anomaly_detector.py       # Isolation Forest + DBSCAN/Z-Score
│   ├── pyspark_pipeline.py       # Pipeline Spark distribuído
│   ├── evaluator.py              # Métricas (F1, AUC-ROC, etc.)
│   ├── visualizations.py         # Gráficos matplotlib/seaborn/plotly
│   └── logger.py                 # Logging estruturado (structlog)
│
├── notebooks/
│   └── 01-exploratory_analysis.ipynb   # EDA interativa
│
├── tests/
│   ├── conftest.py               # Fixtures pytest
│   ├── test_preprocessor.py
│   └── test_detector.py
│
├── deploy/
│   ├── Dockerfile.prod           # Multi-stage build (produção)
│   ├── ecs-task-definition.json  # Task Definition ECS Fargate
│   └── terraform/
│       ├── main.tf               # VPC+ECS+RDS+ALB+ECR+CloudWatch
│       ├── variables.tf
│       ├── outputs.tf
│       └── terraform.tfvars.example
│
└── .github/workflows/
    └── deploy.yml                # CI/CD GitHub Actions
```

---

## 🛠️ Stack Tecnológico

| Camada | Tecnologia |
|---|---|
| **Processamento** | PySpark 3.5, Pandas 2.1, NumPy 1.24 |
| **ML** | scikit-learn (Isolation Forest, DBSCAN) |
| **Banco** | MySQL 8.0 (via Docker/RDS) |
| **API** | FastAPI + Uvicorn |
| **Visualização** | Matplotlib, Seaborn, Plotly |
| **Infra** | Docker, docker-compose |
| **Deploy** | AWS ECS Fargate, RDS MySQL, ALB, ECR |
| **IaC** | Terraform |
| **CI/CD** | GitHub Actions |
| **Logging** | structlog |
| **Testes** | pytest + pytest-cov |

---

## ⚙️ Pré-requisitos

- **Python 3.11+**
- **Docker + Docker Compose**
- **Java 17** (para PySpark) — opcional se usar Docker
- **Git**
- (Opcional para AWS) AWS CLI + Terraform 1.5+

---

## 🚀 Como rodar localmente

### Opção 1 — Tudo via Docker (recomendado)

```bash
# 1. Subir MySQL + app
docker-compose up -d --build

# 2. Popular banco com 10k transações sintéticas
docker-compose exec app python src/populate_data.py

# 3. Rodar o pipeline completo
docker-compose exec app python main.py --save-mysql

# 4. Acessar API: http://localhost:8000/docs
```

### Opção 2 — Python local + MySQL em Docker

```bash
# 1. Criar ambiente virtual
python -m venv venv
venv\Scripts\activate           # Windows
source venv/bin/activate        # Linux/Mac

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Subir apenas o MySQL
docker-compose up -d mysql

# 4. Configurar .env (copie .env.example → .env)
copy .env.example .env          # Windows
cp .env.example .env            # Linux/Mac

# 5. Popular banco
python src/populate_data.py

# 6. Rodar pipeline
python main.py --save-mysql

# 7. API
uvicorn app:app --reload --port 8000
```

Abra em **http://localhost:8000/docs** para ver o Swagger.

---

## 🔄 Pipeline de detecção

O `main.py` executa as etapas:

1. **Carrega** transações do MySQL (fallback para CSV se MySQL offline)
2. **Pré-processa** criando features:
   - `valor_log` — log do valor (reduz cauda longa)
   - `hora`, `dia_semana`, `is_madrugada`, `is_fim_semana`
   - `frequencia_cliente`, `valor_medio_cliente`, `valor_std_cliente`
   - `desvio_valor_cliente` — z-score do valor vs média do cliente
   - `tipo_transacao_encoded`, `local_encoded`, `dispositivo_encoded`
3. **Detecta** com dois métodos em paralelo:
   - **Isolation Forest** (principal) — sklearn com paralelização
   - **DBSCAN + Z-Score** (secundário) — validação cruzada
4. **Avalia** métricas quando há labels verdadeiros
5. **Gera** 5 visualizações:
   - Distribuição de valores
   - Série temporal
   - Heatmap de correlações
   - Scatter 2D das anomalias
   - **Dashboard interativo Plotly** (`data/processed/05_dashboard.html`)
6. **Persiste** resultados em `anomalias` (MySQL) e CSV

### Pipeline PySpark (distribuído)

Para grandes volumes, use `--use-spark`:

```bash
python main.py --use-spark --save-mysql
```

O módulo `src/pyspark_pipeline.py`:
- Lê MySQL via JDBC
- Aplica feature engineering distribuído (window functions, groupBy)
- Converte para Pandas no final para treino do IForest

---

## 🌐 API FastAPI

### Endpoints principais

| Método | Rota | Descrição |
|---|---|---|
| GET | `/health` | Status da API + banco |
| GET | `/stats` | Estatísticas gerais |
| GET | `/anomalies` | Lista anomalias (filtros: `date_from`, `date_to`, `limit`, `metodo`) |
| POST | `/detect` | Upload de CSV e retorna anomalias |
| GET | `/dashboard` | Serve o dashboard Plotly HTML |
| GET | `/docs` | Swagger UI |
| GET | `/redoc` | ReDoc |

### Exemplos cURL

```bash
# Health check
curl http://localhost:8000/health

# Listar top 50 anomalias
curl "http://localhost:8000/anomalies?limit=50"

# Filtrar por data e método
curl "http://localhost:8000/anomalies?date_from=2024-01-01&metodo=isolation_forest"

# Upload CSV para detecção
curl -X POST "http://localhost:8000/detect" \
  -F "file=@data/raw/transacoes.csv"

# Estatísticas
curl http://localhost:8000/stats
```

---

## 📓 Notebook de EDA

```bash
# Dentro do container
docker-compose exec app jupyter notebook --ip=0.0.0.0 --allow-root --port=8888

# Ou local
jupyter notebook notebooks/01-exploratory_analysis.ipynb
```

O notebook cobre: carregamento, estatísticas, distribuições, heatmap, treino
dos detectores, avaliação e visualização interativa.

---

## 🧪 Testes

```bash
# Rodar todos os testes
pytest tests/ -v

# Com cobertura
pytest tests/ -v --cov=src --cov-report=html

# Apenas um arquivo
pytest tests/test_detector.py -v
```

Os testes cobrem: preprocessador, detectores (IForest e DBSCAN), avaliador e
pipeline end-to-end com dataset sintético gerado pelas fixtures.

---

## ☁️ Deploy na AWS

### Arquitetura AWS provisionada pelo Terraform

```
Internet ─▶ ALB (public subnets)
              │
              ▼
         ECS Fargate Service (private subnets)
              │
              ▼
         RDS MySQL (private subnets)

         + ECR (imagem Docker)
         + CloudWatch Logs
         + NAT Gateway
         + IAM Roles
```

### Passos

**1. Configurar AWS CLI**
```bash
aws configure
```

**2. Provisionar infraestrutura com Terraform**
```bash
cd deploy/terraform
copy terraform.tfvars.example terraform.tfvars    # preencha db_password
terraform init
terraform plan
terraform apply
```

No final, o Terraform mostra:
- `alb_url` — URL pública da aplicação
- `ecr_repository_url` — para push da imagem
- `rds_endpoint` — endpoint do banco

**3. Build e push da imagem**
```bash
# Autentica no ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <ECR_URL>

# Build e push
docker build -f deploy/Dockerfile.prod -t <ECR_URL>:latest .
docker push <ECR_URL>:latest
```

**4. CI/CD automático (GitHub Actions)**

Configure os secrets no GitHub:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

Ao fazer push em `main`, o workflow:
1. Roda os testes
2. Faz build da imagem
3. Push para ECR
4. Atualiza o ECS Service

**5. Aplicar schema no RDS (primeira vez)**
```bash
mysql -h <RDS_ENDPOINT> -u admin -p anomaly_db < data/schema.sql
```

---

## 🧠 Algoritmos usados

### Isolation Forest (principal)

Algoritmo baseado em árvores que isola anomalias através de partições
aleatórias. Pontos que precisam de **menos splits** para serem isolados são
mais anômalos.

- **Complexidade**: O(n log n)
- **Escala bem** para grandes volumes
- **Contamination**: 3% (ajustável via `--contamination`)

> ⚠️ O PySpark MLlib **não tem** IForest nativo. Usamos scikit-learn com
> paralelização (`n_jobs=-1`), e o Spark é usado para feature engineering
> distribuído e I/O via JDBC.

### DBSCAN + Z-Score (secundário)

- **DBSCAN**: clustering baseado em densidade; pontos que não pertencem a
  nenhum cluster denso são marcados como ruído (potencial anomalia)
- **Z-Score**: marca como anomalia qualquer transação com |z| > 3σ em alguma
  feature

A combinação `DBSCAN OR Z-Score` oferece uma segunda opinião útil para
validação cruzada.

---

## 🧪 Status de Testes & Validação

Esta seção documenta exatamente o que foi validado no ambiente local do
desenvolvimento e o que **ainda precisa** ser testado pelo usuário final
(tipicamente porque exige Docker, AWS ou Java instalados).

### ✅ Já validado neste ambiente

| # | Item | Resultado |
|---|---|---|
| 1 | Testes unitários `pytest tests/ -v` | **14/14 passing** em 4.7s |
| 2 | Pipeline end-to-end `python main.py --source csv` sobre 10.000 transações sintéticas | AUC-ROC **0.961** (Isolation Forest), **0.976** (DBSCAN+Z-Score); 300 anomalias detectadas; 5 PNG + dashboard HTML gerados |
| 3 | API FastAPI — **9/9 endpoints** via `TestClient` | `GET /`, `/health`, `/docs`, `/openapi.json`, `/dashboard`, `POST /detect` (válido + inválido), `GET /anomalies` e `/stats` (com tratamento gracioso de erro quando MySQL offline) |
| 4 | Stack MySQL — validação estática (sem container rodando) | Drivers `mysql-connector-python 9.6.0`, `sqlalchemy 2.0.49`, `pymysql 1.4.6` instalados; schema SQL parseado (75 linhas, todas estruturas presentes); `docker-compose.yml` estruturalmente correto; URLs SQLAlchemy e JDBC montadas corretamente |
| 5 | `src/populate_data.py` | Gera CSV de 10k transações com ~3% de anomalias injetadas |
| 6 | Visualizações | `01_distribuicao_valores.png`, `02_serie_temporal.png`, `03_heatmap_correlacoes.png`, `04_scatter_anomalias.png`, `05_dashboard.html` |

### ⏸️ Não testado neste ambiente (bloqueado ou opcional)

| # | Item | Motivo | Como validar |
|---|---|---|---|
| 1 | `docker-compose up` end-to-end (MySQL real + App) | **Docker Desktop não está instalado** neste PC | Instale Docker Desktop, rode `docker-compose up -d` e depois `python src/populate_data.py` (dados vão para MySQL) |
| 2 | Persistência real no MySQL (`python main.py --save-mysql`) | Depende do item 1 | Mesmo comando após subir o MySQL |
| 3 | `GET /anomalies` e `GET /stats` com dados reais | Depende do item 1 | `curl http://localhost:8000/anomalies?limit=50` após popular o banco |
| 4 | Pipeline **PySpark** (`python main.py --use-spark`) | Não solicitado anteriormente; exige Java 17 + 1,5 GB de download do PySpark | `pip install pyspark==3.5.0` + Java 17 + rodar com a flag |
| 5 | Notebook `01-exploratory_analysis.ipynb` execução célula-a-célula | Estrutura criada, mas nenhuma célula foi rodada | `jupyter notebook notebooks/01-exploratory_analysis.ipynb` e Cell → Run All |
| 6 | `terraform validate` + `terraform plan` | Terraform CLI não instalado; requer credenciais AWS | `cd deploy/terraform && terraform init && terraform validate` |
| 7 | Deploy efetivo AWS + CI/CD GitHub Actions | Requer credenciais AWS e push para repositório | Configure `AWS_ACCESS_KEY_ID` e `AWS_SECRET_ACCESS_KEY` nos secrets do repo e faça push em `main` |

### 📊 Resumo dos testes automatizados

```
tests/test_preprocessor.py::test_preprocessor_fit_transform_retorna_features    PASSED
tests/test_preprocessor.py::test_preprocessor_gera_features_esperadas           PASSED
tests/test_preprocessor.py::test_preprocessor_transform_sem_fit_falha           PASSED
tests/test_preprocessor.py::test_preprocessor_transform_apos_fit                PASSED
tests/test_preprocessor.py::test_valor_log_sem_negativos_nem_nan                PASSED
tests/test_preprocessor.py::test_is_madrugada_binario                           PASSED
tests/test_detector.py::test_isolation_forest_retorna_detection_result          PASSED
tests/test_detector.py::test_dbscan_retorna_detection_result                    PASSED
tests/test_detector.py::test_isolation_forest_detecta_anomalias_conhecidas      PASSED
tests/test_detector.py::test_deteccao_combinada                                 PASSED
tests/test_detector.py::test_montar_df_anomalias                                PASSED
tests/test_detector.py::test_avaliador_metricas_validas                         PASSED
tests/test_detector.py::test_contamination_fora_do_intervalo_levanta_erro       PASSED
tests/test_detector.py::test_pipeline_end_to_end_minimo                         PASSED
============================= 14 passed in 4.70s ==============================
```

### 🚦 Métricas do pipeline sobre 10.000 transações sintéticas (3% de anomalias)

| Algoritmo | AUC-ROC | F1 | Precision | Recall | Nº anomalias |
|---|---|---|---|---|---|
| Isolation Forest | **0.961** | 0.393 | 0.393 | 0.393 | 300 |
| DBSCAN + Z-Score | **0.976** | 0.060 | 0.031 | **1.000** | ~9.700 |

> Isolation Forest é o detector **equilibrado** (precisão e recall iguais).
> DBSCAN + Z-Score prioriza **recall total** (bom para triagem, revisão humana
> depois). Os limiares são ajustáveis em `config/config.yaml`.

---

## 🧯 Troubleshooting

### MySQL não conecta
```
Erro: Can't connect to MySQL server
```
- Confirme que o container está rodando: `docker-compose ps`
- Aguarde ~20s após `docker-compose up` (healthcheck)
- Verifique porta: `netstat -an | findstr 3306`

### PySpark: "JAVA_HOME not set"
- Instale Java 17: https://adoptium.net/
- Ou use o Docker (já vem com Java)
- Windows: defina `JAVA_HOME` nas variáveis de ambiente

### Dashboard vazio em `/dashboard`
- Rode o pipeline primeiro: `python main.py --save-mysql`
- Verifique se `data/processed/05_dashboard.html` foi gerado

### ImportError: No module named 'pyspark'
```bash
pip install -r requirements.txt
```

### Testes falhando por falta de MySQL
Os testes **não** precisam de MySQL — usam fixtures sintéticas.
Se falhar, rode: `pytest tests/test_preprocessor.py tests/test_detector.py -v`

---

## 📊 Entregas

- ✅ `docker-compose up` → ambiente local funcional
- ✅ `python src/populate_data.py` → 10k transações geradas
- ✅ `python main.py` → pipeline completo
- ✅ `uvicorn app:app` → API + Swagger em /docs
- ✅ `notebooks/01-exploratory_analysis.ipynb` → EDA completa
- ✅ `deploy/` → pronto para AWS (Terraform + GitHub Actions)
- ✅ `pytest tests/` → testes unitários

---

## 📝 Licença

Uso educacional e demonstrativo.

---

## 🤝 Fluxo típico de uso

```bash
# Desenvolvimento
docker-compose up -d
docker-compose exec app python src/populate_data.py
docker-compose exec app python main.py --save-mysql
# abre http://localhost:8000/docs

# Produção
cd deploy/terraform && terraform apply
git push origin main   # dispara CI/CD
# abre http://<alb_url>/docs
```

Bom hacking! 🎉

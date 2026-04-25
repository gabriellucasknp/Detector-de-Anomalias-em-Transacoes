# Detector-de-Anomalias-em-Dados-de-Transações
### Estrutura Base
- [x] .gitignore
- [x] .env.example
- [x] requirements.txt
- [x] README.md

### Docker & Ambiente
- [x] docker-compose.yml (MySQL + app)
- [x] Dockerfile (Python 3.11 + Java 17 para PySpark)

### Configuração
- [x] config/__init__.py
- [x] config/database.py (lazy imports, funciona sem drivers MySQL)
- [x] config/config.yaml

### Dados
- [x] data/schema.sql (tabelas transacoes, anomalias, view)
- [x] data/raw/
- [x] data/processed/

### Código Fonte (src/)
- [x] src/__init__.py
- [x] src/logger.py (structlog)
- [x] src/data_loader.py (MySQL + CSV)
- [x] src/preprocessor.py (12 features engineered)
- [x] src/anomaly_detector.py (Isolation Forest + DBSCAN + Z-Score)
- [x] src/pyspark_pipeline.py (Pipeline Spark)
- [x] src/evaluator.py (métricas precision/recall/F1/AUC)
- [x] src/populate_data.py (10k transações sintéticas + 3% anomalias)
- [x] src/visualizations.py (5 gráficos + dashboard Plotly)

### Principal
- [x] main.py (CLI com argparse)
- [x] app.py (FastAPI: /health, /anomalies, /detect, /dashboard)

### Notebooks
- [x] notebooks/01-exploratory_analysis.ipynb

### Testes
- [x] tests/__init__.py
- [x] tests/conftest.py
- [x] tests/test_preprocessor.py (6 testes)
- [x] tests/test_detector.py (8 testes)


### CI/CD
- [x] .github/workflows/deploy.yml

## 🧪 VALIDAÇÃO

### Testes Unitários
- ✅ **14/14 testes passando** em 7.12s
  - test_preprocessor.py: 6/6
  - test_detector.py: 8/8

### Smoke Test End-to-End
- ✅ `python src/populate_data.py` → gera 10k registros CSV
- ✅ `python main.py --source csv` → pipeline completo:
  - Carrega 10.000 transações
  - Preprocessa (12 features)
  - Isolation Forest: **AUC=0.961**, F1=0.393
  - DBSCAN+Z-Score: **AUC=0.976**, recall=1.00
  - Gera 5 gráficos PNG + dashboard HTML interativo
  - Exporta CSVs de anomalias

### Artefatos Gerados
- ✅ data/raw/transacoes.csv (10k linhas)
- ✅ data/processed/01_distribuicao_valores.png
- ✅ data/processed/02_timeseries.png
- ✅ data/processed/03_heatmap_correlacoes.png
- ✅ data/processed/04_scatter_anomalias.png
- ✅ data/processed/05_dashboard.html (Plotly interativo)
- ✅ data/processed/anomalias_isolation_forest.csv
- ✅ data/processed/anomalias_dbscan.csv

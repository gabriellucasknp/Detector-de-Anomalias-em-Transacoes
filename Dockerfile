# Dockerfile de desenvolvimento
# Inclui Python 3.11 + Java 17 (necessário para PySpark)
FROM python:3.11-slim

# Metadados
LABEL maintainer="Detector de Anomalias"
LABEL description="Ambiente de desenvolvimento - Python + PySpark + MySQL"

# Variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
    PATH="/usr/lib/jvm/java-17-openjdk-amd64/bin:${PATH}"

# Instala dependências do sistema: Java (PySpark), build tools e MySQL client
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-17-jdk-headless \
    build-essential \
    curl \
    default-libmysqlclient-dev \
    pkg-config \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Diretório de trabalho
WORKDIR /app

# Copia requirements e instala dependências Python primeiro (cache do Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia o código da aplicação
COPY . .

# Expõe portas da API FastAPI e Jupyter
EXPOSE 8000 8888

# Comando padrão: sobe a API
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

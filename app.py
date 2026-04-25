"""
API FastAPI do Detector de Anomalias.

Endpoints:
- GET  /health              → status da aplicação e banco
- GET  /anomalies           → lista anomalias (filtros por data e limite)
- POST /detect              → upload CSV e retorna anomalias detectadas
- GET  /dashboard           → métricas agregadas + links para gráficos
- GET  /stats               → estatísticas gerais das transações
"""
from __future__ import annotations

import io
from datetime import datetime
from typing import List, Optional

import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from config.database import get_engine, test_connection
from src.anomaly_detector import detectar_anomalias_combinado, montar_df_anomalias
from src.data_loader import carregar_transacoes_mysql
from src.logger import logger
from src.preprocessor import TransactionPreprocessor

# ---------------------------------------------------------------------
# App
# ---------------------------------------------------------------------
app = FastAPI(
    title="Detector de Anomalias API",
    description="API REST para detecção de anomalias em transações financeiras",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------
# Schemas Pydantic
# ---------------------------------------------------------------------
class HealthResponse(BaseModel):
    status: str
    database: str
    timestamp: str


class AnomalyResponse(BaseModel):
    anomalia_id: int
    transacao_id: int
    cliente_id: int
    valor: float
    data_transacao: str
    tipo_transacao: str
    local: Optional[str]
    dispositivo: Optional[str]
    score_anomalia: float
    metodo_deteccao: str


class DetectionSummary(BaseModel):
    total_transacoes: int
    anomalias_isolation_forest: int
    anomalias_dbscan: int
    taxa_anomalia_iforest: float
    taxa_anomalia_dbscan: float
    preview: List[dict]


class StatsResponse(BaseModel):
    total_transacoes: int
    total_anomalias: int
    valor_total: float
    valor_medio: float
    clientes_unicos: int


# ---------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------
@app.get("/", tags=["Root"])
def root() -> dict:
    """Endpoint raiz — redireciona para /docs."""
    return {
        "app": "Detector de Anomalias API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse, tags=["Sistema"])
def health() -> HealthResponse:
    """Verifica o status da API e do banco de dados."""
    db_ok = test_connection()
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        database="connected" if db_ok else "disconnected",
        timestamp=datetime.utcnow().isoformat(),
    )


@app.get("/anomalies", tags=["Anomalias"])
def listar_anomalias(
    date_from: Optional[str] = Query(None, description="Data inicial YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="Data final YYYY-MM-DD"),
    limit: int = Query(100, ge=1, le=10000),
    metodo: Optional[str] = Query(None, description="isolation_forest ou dbscan_zscore"),
) -> JSONResponse:
    """Lista anomalias detectadas com filtros opcionais."""
    try:
        engine = get_engine()
        query = """
            SELECT
                a.id AS anomalia_id,
                a.transacao_id,
                a.cliente_id,
                a.score_anomalia,
                a.metodo_deteccao,
                a.detected_at,
                t.valor,
                t.data_transacao,
                t.tipo_transacao,
                t.local,
                t.dispositivo
            FROM anomalias a
            INNER JOIN transacoes t ON a.transacao_id = t.id
            WHERE a.is_anomaly = TRUE
        """
        params: dict = {}
        if date_from:
            query += " AND t.data_transacao >= :date_from"
            params["date_from"] = date_from
        if date_to:
            query += " AND t.data_transacao <= :date_to"
            params["date_to"] = date_to
        if metodo:
            query += " AND a.metodo_deteccao = :metodo"
            params["metodo"] = metodo

        query += f" ORDER BY a.score_anomalia DESC LIMIT {int(limit)}"

        df = pd.read_sql(query, engine, params=params)
        # Converte timestamps para string ISO
        for col in ["data_transacao", "detected_at"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col]).astype(str)

        return JSONResponse({
            "total": len(df),
            "filtros": {"date_from": date_from, "date_to": date_to, "metodo": metodo},
            "anomalias": df.to_dict(orient="records"),
        })
    except Exception as e:
        logger.error("erro_listar_anomalias", erro=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/detect", response_model=DetectionSummary, tags=["Detecção"])
async def detectar_upload(file: UploadFile = File(...)) -> DetectionSummary:
    """
    Upload de um CSV de transações e retorna anomalias detectadas.

    Formato esperado do CSV:
        cliente_id, valor, data_transacao, tipo_transacao, local, dispositivo, ip_address
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Arquivo precisa ser CSV.")

    try:
        conteudo = await file.read()
        df = pd.read_csv(io.BytesIO(conteudo), parse_dates=["data_transacao"])
    except Exception as e:
        raise HTTPException(400, f"Erro ao ler CSV: {e}")

    obrigatorias = {"cliente_id", "valor", "data_transacao", "tipo_transacao"}
    if not obrigatorias.issubset(df.columns):
        raise HTTPException(
            400,
            f"CSV precisa ter colunas: {obrigatorias}. "
            f"Encontradas: {list(df.columns)}"
        )

    # Garante colunas opcionais
    for col in ["local", "dispositivo", "ip_address"]:
        if col not in df.columns:
            df[col] = "desconhecido"

    try:
        pre = TransactionPreprocessor()
        df_feat, X = pre.fit_transform(df)
        r_if, r_db = detectar_anomalias_combinado(X)

        df_feat["score_iforest"] = r_if.scores
        df_feat["is_anomaly_iforest"] = r_if.labels
        df_feat["is_anomaly_dbscan"] = r_db.labels

        preview = (
            df_feat[df_feat["is_anomaly_iforest"] == 1]
            .sort_values("score_iforest", ascending=False)
            .head(20)
            [["cliente_id", "valor", "data_transacao", "tipo_transacao",
              "local", "score_iforest"]]
            .assign(data_transacao=lambda d: d["data_transacao"].astype(str))
            .to_dict(orient="records")
        )

        n = len(df_feat)
        return DetectionSummary(
            total_transacoes=n,
            anomalias_isolation_forest=int(r_if.labels.sum()),
            anomalias_dbscan=int(r_db.labels.sum()),
            taxa_anomalia_iforest=round(float(r_if.labels.mean()), 4),
            taxa_anomalia_dbscan=round(float(r_db.labels.mean()), 4),
            preview=preview,
        )
    except Exception as e:
        logger.error("erro_deteccao_upload", erro=str(e))
        raise HTTPException(500, f"Erro no processamento: {e}")


@app.get("/stats", response_model=StatsResponse, tags=["Dashboard"])
def stats() -> StatsResponse:
    """Estatísticas gerais do banco de transações."""
    try:
        engine = get_engine()
        df = pd.read_sql(
            """
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(valor), 0) AS valor_total,
                COALESCE(AVG(valor), 0) AS valor_medio,
                COUNT(DISTINCT cliente_id) AS clientes
            FROM transacoes
            """,
            engine,
        )
        df_anom = pd.read_sql(
            "SELECT COUNT(*) AS total FROM anomalias WHERE is_anomaly = TRUE",
            engine,
        )
        return StatsResponse(
            total_transacoes=int(df.iloc[0]["total"]),
            total_anomalias=int(df_anom.iloc[0]["total"]),
            valor_total=float(df.iloc[0]["valor_total"]),
            valor_medio=float(df.iloc[0]["valor_medio"]),
            clientes_unicos=int(df.iloc[0]["clientes"]),
        )
    except Exception as e:
        logger.error("erro_stats", erro=str(e))
        raise HTTPException(500, str(e))


@app.get("/dashboard", tags=["Dashboard"])
def dashboard() -> FileResponse:
    """Retorna o dashboard HTML gerado pelo Plotly."""
    from pathlib import Path
    path = Path("data/processed/05_dashboard.html")
    if not path.exists():
        raise HTTPException(
            404,
            "Dashboard ainda não foi gerado. Execute 'python main.py' primeiro.",
        )
    return FileResponse(path, media_type="text/html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)

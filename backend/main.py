"""
NewsKG バックエンドAPI

FastAPIアプリケーションのエントリポイント
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import API_PREFIX, CORS_ORIGINS
from backend.routers import graph, stats, entities
from backend.scheduler import init_scheduler, start_scheduler, stop_scheduler, get_scheduler_status


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("NewsKG API Server starting...")
    scheduler = init_scheduler()
    start_scheduler()
    yield
    stop_scheduler()
    print("NewsKG API Server shutting down...")


app = FastAPI(
    title="NewsKG API",
    description="NHKニュースから抽出した知識グラフを可視化するためのAPI",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーターを登録
app.include_router(graph.router, prefix=API_PREFIX)
app.include_router(stats.router, prefix=API_PREFIX)
app.include_router(entities.router, prefix=API_PREFIX)


@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "name": "NewsKG API",
        "version": "0.1.0",
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health")
async def health_check():
    from backend.services.sparql_client import sparql_client

    fuseki_ok = await sparql_client.check_connection()
    scheduler_status = get_scheduler_status()

    return {
        "status": "ok" if fuseki_ok else "degraded",
        "fuseki": "connected" if fuseki_ok else "disconnected",
        "scheduler": scheduler_status,
    }


@app.get("/api/scheduler/status")
async def scheduler_status():
    return get_scheduler_status()


@app.post("/api/pipeline/run")
async def run_pipeline_manual():
    from backend.scheduler import run_daily_pipeline
    result = await run_daily_pipeline()
    return result

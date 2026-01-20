"""
バックエンド設定モジュール

環境変数やデフォルト設定を管理します。
"""

import os
from pathlib import Path

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent

# Fuseki設定（既存config.pyから継承）
FUSEKI_ENDPOINT = os.getenv("FUSEKI_ENDPOINT", "http://172.28.64.1:3030")
FUSEKI_DATASET = os.getenv("FUSEKI_DATASET", "NewsKG")

# SPARQLエンドポイント
SPARQL_QUERY_ENDPOINT = f"{FUSEKI_ENDPOINT}/{FUSEKI_DATASET}/query"
SPARQL_UPDATE_ENDPOINT = f"{FUSEKI_ENDPOINT}/{FUSEKI_DATASET}/update"

# 名前空間
NEWSKG_NAMESPACE = "http://example.org/newskg#"

# API設定
API_PREFIX = "/api"
DEFAULT_GRAPH_LIMIT = 500
MAX_GRAPH_LIMIT = 2000

# CORS設定
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
]

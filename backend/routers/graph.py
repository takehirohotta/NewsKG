"""
グラフAPIルーター

/api/graph エンドポイントを提供します。
トリプルベースRDF対応版（v2）
"""

from typing import Optional, List
from datetime import date, timedelta
from fastapi import APIRouter, Query, HTTPException

from backend.models.schemas import GraphResponse, PeriodType
from backend.services.sparql_client_v2 import sparql_client_v2
from backend.services.graph_builder import graph_builder
from backend.config import DEFAULT_GRAPH_LIMIT, MAX_GRAPH_LIMIT


router = APIRouter(prefix="/graph", tags=["graph"])


def calculate_date_range(
    period: PeriodType,
    from_date: Optional[date],
    to_date: Optional[date],
) -> tuple[date, date]:
    """期間タイプから日付範囲を計算"""
    today = date.today()

    if period == PeriodType.CUSTOM:
        if from_date is None or to_date is None:
            raise HTTPException(
                status_code=400,
                detail="Custom period requires 'from' and 'to' parameters",
            )
        return from_date, to_date

    if period == PeriodType.DAY:
        return today, today
    elif period == PeriodType.WEEK:
        return today - timedelta(days=7), today
    elif period == PeriodType.MONTH:
        return today - timedelta(days=30), today

    # デフォルトは1週間
    return today - timedelta(days=7), today


@router.get("", response_model=GraphResponse)
async def get_graph(
    period: PeriodType = Query(
        default=PeriodType.WEEK,
        description="期間タイプ (day, week, month, custom)",
    ),
    from_date: Optional[date] = Query(
        default=None,
        alias="from",
        description="開始日 (YYYY-MM-DD) - customの場合必須",
    ),
    to_date: Optional[date] = Query(
        default=None,
        alias="to",
        description="終了日 (YYYY-MM-DD) - customの場合必須",
    ),
    types: Optional[str] = Query(
        default=None,
        description="ノードタイプフィルタ (カンマ区切り)",
    ),
    limit: int = Query(
        default=DEFAULT_GRAPH_LIMIT,
        ge=1,
        le=MAX_GRAPH_LIMIT,
        description=f"最大ノード数 (1-{MAX_GRAPH_LIMIT})",
    ),
):
    """
    グラフデータを取得（トリプルベースRDF対応）

    期間を指定してニュース記事とエンティティのグラフを取得します。
    """
    # 日付範囲を計算
    start_date, end_date = calculate_date_range(period, from_date, to_date)

    # タイプフィルタをパース
    type_filter: Optional[List[str]] = None
    if types:
        type_filter = [t.strip() for t in types.split(",")]

    try:
        # SPARQLでデータ取得（v2クライアント使用）
        raw_data = await sparql_client_v2.get_graph_data(
            from_date=start_date,
            to_date=end_date,
            types=type_filter,
            limit=limit,
        )

        # 接続数を取得
        connection_counts = await sparql_client_v2.get_connection_counts()

        # Cytoscape.js形式に変換
        graph = graph_builder.build_graph(
            nodes_raw=raw_data["nodes_raw"],
            edges_raw=raw_data["edges_raw"],
            connection_counts=connection_counts,
            from_date=start_date,
            to_date=end_date,
        )

        return graph

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch graph data: {str(e)}",
        )

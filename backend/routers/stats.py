"""
統計APIルーター

/api/stats エンドポイントを提供します。
トリプルベースRDF対応版
"""

from fastapi import APIRouter, HTTPException

from backend.models.schemas import StatsResponse, DateRange
from backend.services.sparql_client_v2 import sparql_client_v2


router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=StatsResponse)
async def get_stats():
    """
    統計情報を取得（トリプルベースRDF対応）

    記事数、トリプル数、エンティティ数などの統計を返します。
    """
    try:
        stats = await sparql_client_v2.get_stats()

        # DateRangeを適切に構築
        date_range = DateRange(
            earliest=stats["dateRange"].get("earliest"),
            latest=stats["dateRange"].get("latest"),
        )

        return StatsResponse(
            totalArticles=stats["totalArticles"],
            totalStatements=stats.get("totalTriples", 0),  # トリプル数をStatements欄に表示
            totalEntities=stats["totalEntities"],
            entityBreakdown=stats["entityBreakdown"],
            statementBreakdown={},  # トリプルベースでは不要
            dateRange=date_range,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch statistics: {str(e)}",
        )

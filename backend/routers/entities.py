"""
エンティティAPIルーター

/api/entities エンドポイントを提供します。
トリプルベースRDF対応版
"""

from fastapi import APIRouter, HTTPException, Path

from backend.models.schemas import EntityDetailResponse
from backend.services.sparql_client_v2 import sparql_client_v2


router = APIRouter(prefix="/entities", tags=["entities"])


@router.get("/{entity_id}", response_model=EntityDetailResponse)
async def get_entity_detail(
    entity_id: str = Path(
        description="エンティティID (例: person_kishida_fumio)",
    ),
):
    """
    エンティティ詳細を取得（トリプルベースRDF対応）

    指定されたIDのエンティティの詳細情報と関連記事を返します。
    """
    try:
        detail = await sparql_client_v2.get_entity_detail(entity_id)

        if not detail.get("label") or detail["label"] == entity_id:
            # エンティティが見つからない可能性
            pass

        return EntityDetailResponse(**detail)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch entity detail: {str(e)}",
        )

"""
Pydanticスキーマ定義

APIのリクエスト/レスポンスモデルを定義します。
"""

from typing import Optional, Dict, Any, List
from datetime import date
from enum import Enum
from pydantic import BaseModel, Field


class PeriodType(str, Enum):
    """期間タイプ"""
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    CUSTOM = "custom"


class NodeData(BaseModel):
    """ノードデータ"""
    id: str
    label: str
    type: str
    size: int = 10
    properties: Dict[str, Any] = Field(default_factory=dict)


class Node(BaseModel):
    """Cytoscape.js形式のノード"""
    data: NodeData


class EdgeData(BaseModel):
    """エッジデータ"""
    id: str
    source: str
    target: str
    label: str
    type: str


class Edge(BaseModel):
    """Cytoscape.js形式のエッジ"""
    data: EdgeData


class PeriodMeta(BaseModel):
    """期間メタ情報"""
    from_date: date = Field(alias="from")
    to_date: date = Field(alias="to")

    class Config:
        populate_by_name = True


class NodeTypeCounts(BaseModel):
    """ノードタイプ別カウント"""
    Person: int = 0
    Organization: int = 0
    Place: int = 0
    NewsArticle: int = 0
    Statement: int = 0


class GraphMeta(BaseModel):
    """グラフメタ情報"""
    period: PeriodMeta
    totalNodes: int
    totalEdges: int
    nodeTypes: Dict[str, int] = Field(default_factory=dict)


class GraphResponse(BaseModel):
    """グラフデータレスポンス"""
    nodes: List[Node]
    edges: List[Edge]
    meta: GraphMeta


class EntityBreakdown(BaseModel):
    """エンティティ種別内訳"""
    Person: int = 0
    Organization: int = 0
    Place: int = 0


class StatementBreakdown(BaseModel):
    """Statement種別内訳"""
    PolicyAnnouncement: int = 0
    WeatherDisaster: int = 0
    EarthquakeEvent: int = 0
    ElectionResult: int = 0
    DissolutionAnnouncement: int = 0
    CandidateAnnouncement: int = 0
    BudgetDecision: int = 0
    LegislationEvent: int = 0
    EvacuationOrder: int = 0
    DamageReport: int = 0


class DateRange(BaseModel):
    """日付範囲"""
    earliest: Optional[date] = None
    latest: Optional[date] = None


class StatsResponse(BaseModel):
    """統計情報レスポンス"""
    totalArticles: int = 0
    totalStatements: int = 0
    totalEntities: int = 0
    entityBreakdown: Dict[str, int] = Field(default_factory=dict)
    statementBreakdown: Dict[str, int] = Field(default_factory=dict)
    dateRange: DateRange = Field(default_factory=DateRange)


class RelatedArticle(BaseModel):
    """関連記事"""
    id: str
    title: str
    url: str
    pubDate: Optional[str] = None


class RelatedStatement(BaseModel):
    """関連Statement"""
    id: str
    type: str
    label: str


class EntityDetailResponse(BaseModel):
    """エンティティ詳細レスポンス"""
    id: str
    label: str
    type: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    relatedArticles: List[RelatedArticle] = Field(default_factory=list)
    relatedStatements: List[RelatedStatement] = Field(default_factory=list)
    connectionCount: int = 0


class PipelineRunResponse(BaseModel):
    """パイプライン実行レスポンス"""
    success: bool
    message: str
    stats: Optional[Dict[str, Any]] = None

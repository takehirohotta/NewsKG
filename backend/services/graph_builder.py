"""
グラフビルダー

SPARQLの結果をCytoscape.js形式に変換します。
トリプルベースRDF対応版
"""

from typing import Dict, Any, List, Optional
from datetime import date

from backend.config import NEWSKG_NAMESPACE
from backend.models.schemas import (
    Node,
    NodeData,
    Edge,
    EdgeData,
    GraphResponse,
    GraphMeta,
    PeriodMeta,
)


class GraphBuilder:
    """SPARQLの結果をCytoscape.js形式に変換するクラス"""

    def __init__(self, namespace: str = NEWSKG_NAMESPACE):
        self.ns = namespace

    def build_graph(
        self,
        nodes_raw: List[Dict[str, Any]],
        edges_raw: List[Dict[str, Any]],
        connection_counts: Dict[str, int],
        from_date: date,
        to_date: date,
    ) -> GraphResponse:
        """
        生のSPARQL結果からCytoscape.js形式のグラフを構築
        """
        nodes = self._build_nodes(nodes_raw, connection_counts)
        edges = self._build_edges(edges_raw, nodes)

        # ノードタイプ別カウント
        node_types: Dict[str, int] = {}
        for node in nodes:
            node_type = node.data.type
            node_types[node_type] = node_types.get(node_type, 0) + 1

        meta = GraphMeta(
            period=PeriodMeta(**{"from": from_date, "to": to_date}),
            totalNodes=len(nodes),
            totalEdges=len(edges),
            nodeTypes=node_types,
        )

        return GraphResponse(nodes=nodes, edges=edges, meta=meta)

    def _build_nodes(
        self,
        nodes_raw: List[Dict[str, Any]],
        connection_counts: Dict[str, int],
    ) -> List[Node]:
        """ノードリストを構築"""
        nodes: Dict[str, Node] = {}

        for binding in nodes_raw:
            node_uri = binding["node"]["value"]
            node_id = self._uri_to_id(node_uri)

            if node_id in nodes:
                continue

            node_type_uri = binding["nodeType"]["value"]
            node_type = node_type_uri.split("#")[-1]

            # ラベルを取得（hasLabelまたはhasTitleから）
            label = binding.get("label", {}).get("value", node_id)

            # 接続数からサイズを計算
            connection_count = connection_counts.get(node_uri, 0)
            size = self._calculate_size(node_type, connection_count)

            # プロパティ
            properties: Dict[str, Any] = {}
            if "url" in binding:
                properties["url"] = binding["url"]["value"]
            if "pubDate" in binding:
                properties["pubDate"] = binding["pubDate"]["value"]

            node_data = NodeData(
                id=node_id,
                label=label,
                type=node_type,
                size=size,
                properties=properties,
            )
            nodes[node_id] = Node(data=node_data)

        return list(nodes.values())

    def _build_edges(
        self,
        edges_raw: List[Dict[str, Any]],
        nodes: List[Node],
    ) -> List[Edge]:
        """エッジリストを構築"""
        # 有効なノードIDセット
        valid_node_ids = {node.data.id for node in nodes}

        edges: Dict[str, Edge] = {}
        edge_counter = 0

        for binding in edges_raw:
            source_uri = binding["source"]["value"]
            target_uri = binding["target"]["value"]
            predicate_uri = binding["predicate"]["value"]

            source_id = self._uri_to_id(source_uri)
            target_id = self._uri_to_id(target_uri)

            # 両端がノードリストに存在する場合のみ追加
            if source_id not in valid_node_ids or target_id not in valid_node_ids:
                continue

            edge_key = f"{source_id}-{predicate_uri}-{target_id}"
            if edge_key in edges:
                continue

            # 述語のラベルを取得（日本語ラベルがあれば使用）
            predicate_label = binding.get("predicateLabel", {}).get("value")
            if not predicate_label:
                # URIから抽出
                predicate = predicate_uri.split("#")[-1]
                # rel_xxx形式の場合、rel_を除去
                if predicate.startswith("rel_"):
                    predicate_label = predicate[4:]
                else:
                    predicate_label = predicate
            
            predicate_type = predicate_uri.split("#")[-1]

            edge_id = f"edge_{edge_counter}"
            edge_counter += 1

            edge_data = EdgeData(
                id=edge_id,
                source=source_id,
                target=target_id,
                label=predicate_label,
                type=predicate_type,
            )
            edges[edge_key] = Edge(data=edge_data)

        return list(edges.values())

    def _uri_to_id(self, uri: str) -> str:
        """URIからIDを抽出"""
        if "#" in uri:
            return uri.split("#")[-1]
        return uri.split("/")[-1]

    def _calculate_size(self, node_type: str, connection_count: int) -> int:
        """ノードタイプと接続数からサイズを計算"""
        # タイプ別の基本サイズ
        base_sizes = {
            "Person": 20,
            "Organization": 22,
            "Place": 18,
            "Event": 16,
            "Entity": 14,
            "NewsArticle": 12,
        }
        
        base_size = base_sizes.get(node_type, 15)
        
        # 接続数に応じてサイズを増加
        size_per_connection = 2
        max_size = 50

        size = base_size + connection_count * size_per_connection
        return min(size, max_size)


# シングルトンインスタンス
graph_builder = GraphBuilder()

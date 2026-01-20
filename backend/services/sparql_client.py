"""
SPARQLクライアント

Fusekiサーバーへのクエリ実行を担当します。
"""

import httpx
from typing import Dict, Any, List, Optional
from datetime import date
import logging

from backend.config import (
    SPARQL_QUERY_ENDPOINT,
    SPARQL_UPDATE_ENDPOINT,
    NEWSKG_NAMESPACE,
)


logger = logging.getLogger(__name__)


class SPARQLClient:
    """SPARQLクエリを実行するクライアント"""

    def __init__(
        self,
        query_endpoint: str = SPARQL_QUERY_ENDPOINT,
        update_endpoint: str = SPARQL_UPDATE_ENDPOINT,
        timeout: float = 30.0,
    ):
        self.query_endpoint = query_endpoint
        self.update_endpoint = update_endpoint
        self.timeout = timeout
        self.ns = NEWSKG_NAMESPACE

    async def execute_query(self, sparql: str) -> Dict[str, Any]:
        """
        SPARQLクエリを実行

        Args:
            sparql: SPARQLクエリ文字列

        Returns:
            SPARQL JSON結果
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    self.query_endpoint,
                    params={"query": sparql},
                    headers={"Accept": "application/sparql-results+json"},
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"SPARQL query failed: {e.response.status_code}")
                raise
            except httpx.RequestError as e:
                logger.error(f"SPARQL request error: {e}")
                raise

    async def check_connection(self) -> bool:
        """Fusekiへの接続を確認"""
        try:
            simple_query = "SELECT * WHERE { ?s ?p ?o } LIMIT 1"
            await self.execute_query(simple_query)
            return True
        except Exception:
            return False

    async def get_graph_data(
        self,
        from_date: date,
        to_date: date,
        types: Optional[List[str]] = None,
        limit: int = 500,
    ) -> Dict[str, Any]:
        """
        グラフ表示用データを取得

        Args:
            from_date: 開始日
            to_date: 終了日
            types: フィルタするノードタイプ
            limit: 最大ノード数

        Returns:
            ノードとエッジのデータ
        """
        from_dt = f"{from_date}T00:00:00"
        to_dt = f"{to_date}T23:59:59"

        # ノード取得クエリ
        nodes_query = f"""
        PREFIX newskg: <{self.ns}>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

        SELECT DISTINCT ?node ?nodeType ?label ?url ?pubDate
        WHERE {{
            # 期間内の記事
            ?article a newskg:NewsArticle ;
                     newskg:hasPubDate ?pubDate .
            
            FILTER(?pubDate >= "{from_dt}"^^xsd:dateTime)
            FILTER(?pubDate <= "{to_dt}"^^xsd:dateTime)
            
            {{
                # 記事自体
                BIND(?article AS ?node)
                BIND(newskg:NewsArticle AS ?nodeType)
                ?article newskg:hasTitle ?label .
                OPTIONAL {{ ?article newskg:hasUrl ?url }}
            }}
            UNION
            {{
                # 記事から抽出されたStatement
                ?stmt newskg:extractedFrom ?article ;
                      a ?nodeType .
                BIND(?stmt AS ?node)
                OPTIONAL {{ ?stmt newskg:hasLabel ?label }}
                FILTER(?nodeType != newskg:Statement)
            }}
            UNION
            {{
                # Statementに関連するエンティティ
                ?stmt newskg:extractedFrom ?article .
                {{
                    ?stmt newskg:hasActor ?node .
                    ?node a ?nodeType .
                }}
                UNION
                {{
                    ?stmt newskg:hasLocation ?node .
                    ?node a ?nodeType .
                }}
                ?node newskg:hasLabel ?label .
            }}
        }}
        LIMIT {limit * 3}
        """

        # エッジ取得クエリ
        edges_query = f"""
        PREFIX newskg: <{self.ns}>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

        SELECT DISTINCT ?source ?predicate ?target
        WHERE {{
            ?article a newskg:NewsArticle ;
                     newskg:hasPubDate ?pubDate .
            
            FILTER(?pubDate >= "{from_dt}"^^xsd:dateTime)
            FILTER(?pubDate <= "{to_dt}"^^xsd:dateTime)
            
            {{
                # Statement -> Article
                ?source newskg:extractedFrom ?article .
                BIND(newskg:extractedFrom AS ?predicate)
                BIND(?article AS ?target)
            }}
            UNION
            {{
                # Statement -> Entity (hasActor, hasLocation)
                ?stmt newskg:extractedFrom ?article .
                ?stmt ?predicate ?target .
                BIND(?stmt AS ?source)
                FILTER(?predicate IN (newskg:hasActor, newskg:hasLocation))
            }}
        }}
        LIMIT {limit * 5}
        """

        # クエリ実行
        nodes_result = await self.execute_query(nodes_query)
        edges_result = await self.execute_query(edges_query)

        return {
            "nodes_raw": nodes_result.get("results", {}).get("bindings", []),
            "edges_raw": edges_result.get("results", {}).get("bindings", []),
        }

    async def get_connection_counts(self) -> Dict[str, int]:
        """各ノードの接続数を取得"""
        query = f"""
        PREFIX newskg: <{self.ns}>

        SELECT ?entity (COUNT(*) as ?count)
        WHERE {{
            {{
                ?entity ?p ?o .
                FILTER(?p IN (
                    newskg:hasActor,
                    newskg:hasLocation,
                    newskg:extractedFrom
                ))
            }}
            UNION
            {{
                ?s ?p ?entity .
                FILTER(?p IN (
                    newskg:hasActor,
                    newskg:hasLocation,
                    newskg:extractedFrom
                ))
            }}
        }}
        GROUP BY ?entity
        """
        result = await self.execute_query(query)
        bindings = result.get("results", {}).get("bindings", [])

        counts = {}
        for binding in bindings:
            entity = binding["entity"]["value"]
            count = int(binding["count"]["value"])
            counts[entity] = count

        return counts

    async def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得"""
        # 記事数
        articles_query = f"""
        PREFIX newskg: <{self.ns}>
        SELECT (COUNT(DISTINCT ?article) AS ?count)
        WHERE {{ ?article a newskg:NewsArticle }}
        """

        # Statement数（種別ごと）
        statements_query = f"""
        PREFIX newskg: <{self.ns}>
        SELECT ?type (COUNT(?stmt) AS ?count)
        WHERE {{
            ?stmt a ?type .
            FILTER(STRSTARTS(STR(?type), "{self.ns}"))
            FILTER(?type NOT IN (
                newskg:NewsArticle,
                newskg:Person,
                newskg:Organization,
                newskg:Place,
                newskg:Entity
            ))
        }}
        GROUP BY ?type
        """

        # エンティティ数（種別ごと）
        entities_query = f"""
        PREFIX newskg: <{self.ns}>
        SELECT ?type (COUNT(?entity) AS ?count)
        WHERE {{
            ?entity a ?type .
            FILTER(?type IN (
                newskg:Person,
                newskg:Organization,
                newskg:Place
            ))
        }}
        GROUP BY ?type
        """

        # 日付範囲
        date_range_query = f"""
        PREFIX newskg: <{self.ns}>
        SELECT (MIN(?date) AS ?earliest) (MAX(?date) AS ?latest)
        WHERE {{
            ?article a newskg:NewsArticle ;
                     newskg:hasPubDate ?date .
        }}
        """

        articles_result = await self.execute_query(articles_query)
        statements_result = await self.execute_query(statements_query)
        entities_result = await self.execute_query(entities_query)
        date_range_result = await self.execute_query(date_range_query)

        # 結果をパース
        total_articles = 0
        if articles_result.get("results", {}).get("bindings"):
            total_articles = int(
                articles_result["results"]["bindings"][0]["count"]["value"]
            )

        entity_breakdown = {}
        total_entities = 0
        for binding in entities_result.get("results", {}).get("bindings", []):
            type_uri = binding["type"]["value"]
            type_name = type_uri.split("#")[-1]
            count = int(binding["count"]["value"])
            entity_breakdown[type_name] = count
            total_entities += count

        statement_breakdown = {}
        total_statements = 0
        for binding in statements_result.get("results", {}).get("bindings", []):
            type_uri = binding["type"]["value"]
            type_name = type_uri.split("#")[-1]
            count = int(binding["count"]["value"])
            statement_breakdown[type_name] = count
            total_statements += count

        date_range = {"earliest": None, "latest": None}
        if date_range_result.get("results", {}).get("bindings"):
            binding = date_range_result["results"]["bindings"][0]
            if "earliest" in binding:
                earliest = binding["earliest"]["value"]
                date_range["earliest"] = earliest.split("T")[0]
            if "latest" in binding:
                latest = binding["latest"]["value"]
                date_range["latest"] = latest.split("T")[0]

        return {
            "totalArticles": total_articles,
            "totalStatements": total_statements,
            "totalEntities": total_entities,
            "entityBreakdown": entity_breakdown,
            "statementBreakdown": statement_breakdown,
            "dateRange": date_range,
        }

    async def get_entity_detail(self, entity_id: str) -> Dict[str, Any]:
        """エンティティの詳細情報を取得"""
        entity_uri = f"{self.ns}{entity_id}"

        # 基本情報
        basic_query = f"""
        PREFIX newskg: <{self.ns}>

        SELECT ?type ?label ?role
        WHERE {{
            <{entity_uri}> a ?type ;
                           newskg:hasLabel ?label .
            OPTIONAL {{ <{entity_uri}> newskg:hasRole ?role }}
        }}
        LIMIT 1
        """

        # 関連記事（hasActorまたはhasLocationで関連）
        articles_query = f"""
        PREFIX newskg: <{self.ns}>

        SELECT DISTINCT ?articleId ?title ?url ?pubDate
        WHERE {{
            {{
                ?stmt newskg:hasActor <{entity_uri}> .
            }}
            UNION
            {{
                ?stmt newskg:hasLocation <{entity_uri}> .
            }}
            ?stmt newskg:extractedFrom ?article .
            ?article newskg:hasTitle ?title ;
                     newskg:hasUrl ?url ;
                     newskg:hasPubDate ?pubDate .
            BIND(REPLACE(STR(?article), "{self.ns}", "") AS ?articleId)
        }}
        ORDER BY DESC(?pubDate)
        LIMIT 10
        """

        # 関連Statement（hasActorまたはhasLocationで関連）
        statements_query = f"""
        PREFIX newskg: <{self.ns}>

        SELECT ?stmtId ?type
        WHERE {{
            {{
                ?stmt newskg:hasActor <{entity_uri}> .
            }}
            UNION
            {{
                ?stmt newskg:hasLocation <{entity_uri}> .
            }}
            ?stmt a ?type .
            FILTER(?type != newskg:Statement)
            BIND(REPLACE(STR(?stmt), "{self.ns}", "") AS ?stmtId)
        }}
        LIMIT 10
        """

        # 接続数
        connection_query = f"""
        PREFIX newskg: <{self.ns}>

        SELECT (COUNT(*) AS ?count)
        WHERE {{
            {{
                ?s ?p <{entity_uri}> .
            }}
            UNION
            {{
                <{entity_uri}> ?p ?o .
            }}
        }}
        """

        basic_result = await self.execute_query(basic_query)
        articles_result = await self.execute_query(articles_query)
        statements_result = await self.execute_query(statements_query)
        connection_result = await self.execute_query(connection_query)

        # 基本情報をパース
        entity_type = "Entity"
        label = entity_id
        properties = {}

        if basic_result.get("results", {}).get("bindings"):
            binding = basic_result["results"]["bindings"][0]
            entity_type = binding["type"]["value"].split("#")[-1]
            label = binding["label"]["value"]
            if "role" in binding:
                properties["role"] = binding["role"]["value"]

        # 関連記事をパース
        related_articles = []
        for binding in articles_result.get("results", {}).get("bindings", []):
            related_articles.append({
                "id": binding["articleId"]["value"],
                "title": binding["title"]["value"],
                "url": binding["url"]["value"],
                "pubDate": binding.get("pubDate", {}).get("value"),
            })

        # 関連Statementをパース
        related_statements = []
        for binding in statements_result.get("results", {}).get("bindings", []):
            stmt_type = binding["type"]["value"].split("#")[-1]
            related_statements.append({
                "id": binding["stmtId"]["value"],
                "type": stmt_type,
                "label": stmt_type,
            })

        # 接続数をパース
        connection_count = 0
        if connection_result.get("results", {}).get("bindings"):
            connection_count = int(
                connection_result["results"]["bindings"][0]["count"]["value"]
            )

        return {
            "id": entity_id,
            "label": label,
            "type": entity_type,
            "properties": properties,
            "relatedArticles": related_articles,
            "relatedStatements": related_statements,
            "connectionCount": connection_count,
        }


# シングルトンインスタンス
sparql_client = SPARQLClient()

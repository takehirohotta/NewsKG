"""
SPARQLクライアント v2 (トリプルベース対応)

新しいトリプルベースRDF形式に対応したFusekiクエリを実行します。
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


class SPARQLClientV2:
    """トリプルベースRDF用SPARQLクライアント"""

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
        """SPARQLクエリを実行"""
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
        トリプルベースRDFからグラフ表示用データを取得
        """
        from_dt = f"{from_date}T00:00:00"
        to_dt = f"{to_date}T23:59:59"

        # ノード取得クエリ（記事とエンティティ）
        nodes_query = f"""
        PREFIX newskg: <{self.ns}>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

        SELECT DISTINCT ?node ?nodeType ?label ?url ?pubDate
        WHERE {{
            {{
                # 記事ノード
                ?node a newskg:NewsArticle ;
                      newskg:hasPubDate ?pubDate ;
                      newskg:hasTitle ?label .
                BIND(newskg:NewsArticle AS ?nodeType)
                OPTIONAL {{ ?node newskg:hasUrl ?url }}
                FILTER(?pubDate >= "{from_dt}"^^xsd:dateTime && ?pubDate <= "{to_dt}"^^xsd:dateTime)
            }}
            UNION
            {{
                # トリプルの主語エンティティ
                ?triple a newskg:NewsTriple ;
                        newskg:extractedFrom ?article ;
                        rdf:subject ?node .
                ?article newskg:hasPubDate ?articlePubDate .
                BIND(?articlePubDate AS ?pubDate)
                FILTER(?pubDate >= "{from_dt}"^^xsd:dateTime && ?pubDate <= "{to_dt}"^^xsd:dateTime)
                
                ?node a ?nodeType .
                FILTER(?nodeType != newskg:NewsTriple)
                OPTIONAL {{ ?node newskg:hasLabel ?label }}
            }}
            UNION
            {{
                # トリプルの目的語エンティティ
                ?triple a newskg:NewsTriple ;
                        newskg:extractedFrom ?article ;
                        rdf:object ?node .
                ?article newskg:hasPubDate ?articlePubDate .
                BIND(?articlePubDate AS ?pubDate)
                FILTER(?pubDate >= "{from_dt}"^^xsd:dateTime && ?pubDate <= "{to_dt}"^^xsd:dateTime)
                
                ?node a ?nodeType .
                FILTER(?nodeType != newskg:NewsTriple)
                OPTIONAL {{ ?node newskg:hasLabel ?label }}
            }}
        }}
        LIMIT {limit * 3}
        """

        # エッジ取得クエリ
        edges_query = f"""
        PREFIX newskg: <{self.ns}>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

        SELECT DISTINCT ?source ?predicate ?target ?predicateLabel
        WHERE {{
            {{
                # エンティティ間の直接関係（トリプルから）
                ?triple a newskg:NewsTriple ;
                        newskg:extractedFrom ?article ;
                        rdf:subject ?source ;
                        rdf:predicate ?predicate ;
                        rdf:object ?target .
                
                ?article newskg:hasPubDate ?pubDate .
                FILTER(?pubDate >= "{from_dt}"^^xsd:dateTime && ?pubDate <= "{to_dt}"^^xsd:dateTime)
                
                OPTIONAL {{ ?predicate rdfs:label ?predicateLabel }}
            }}
            UNION
            {{
                # 記事→エンティティ（主語）の関係
                ?triple a newskg:NewsTriple ;
                        newskg:extractedFrom ?source ;
                        rdf:subject ?target .
                
                ?source a newskg:NewsArticle ;
                        newskg:hasPubDate ?pubDate .
                ?target a ?targetType .
                FILTER(?targetType != newskg:NewsTriple)
                FILTER(?pubDate >= "{from_dt}"^^xsd:dateTime && ?pubDate <= "{to_dt}"^^xsd:dateTime)
                
                BIND(newskg:mentions AS ?predicate)
                BIND("言及" AS ?predicateLabel)
            }}
            UNION
            {{
                # 記事→エンティティ（目的語）の関係
                ?triple a newskg:NewsTriple ;
                        newskg:extractedFrom ?source ;
                        rdf:object ?target .
                
                ?source a newskg:NewsArticle ;
                        newskg:hasPubDate ?pubDate .
                ?target a ?targetType .
                FILTER(?targetType != newskg:NewsTriple)
                FILTER(?pubDate >= "{from_dt}"^^xsd:dateTime && ?pubDate <= "{to_dt}"^^xsd:dateTime)
                
                BIND(newskg:mentions AS ?predicate)
                BIND("言及" AS ?predicateLabel)
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
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT ?entity (COUNT(*) as ?count)
        WHERE {{
            {{
                ?triple rdf:subject ?entity .
            }}
            UNION
            {{
                ?triple rdf:object ?entity .
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
        articles_query = f"""
        PREFIX newskg: <{self.ns}>
        SELECT (COUNT(DISTINCT ?article) AS ?count)
        WHERE {{ ?article a newskg:NewsArticle }}
        """

        triples_query = f"""
        PREFIX newskg: <{self.ns}>
        SELECT (COUNT(?triple) AS ?count)
        WHERE {{ ?triple a newskg:NewsTriple }}
        """

        entities_query = f"""
        PREFIX newskg: <{self.ns}>
        SELECT ?type (COUNT(DISTINCT ?entity) AS ?count)
        WHERE {{
            ?entity a ?type .
            FILTER(?type IN (
                newskg:Person,
                newskg:Organization,
                newskg:Place,
                newskg:Event,
                newskg:Entity
            ))
        }}
        GROUP BY ?type
        """

        date_range_query = f"""
        PREFIX newskg: <{self.ns}>
        SELECT (MIN(?date) AS ?earliest) (MAX(?date) AS ?latest)
        WHERE {{
            ?article a newskg:NewsArticle ;
                     newskg:hasPubDate ?date .
        }}
        """

        articles_result = await self.execute_query(articles_query)
        triples_result = await self.execute_query(triples_query)
        entities_result = await self.execute_query(entities_query)
        date_range_result = await self.execute_query(date_range_query)

        total_articles = 0
        if articles_result.get("results", {}).get("bindings"):
            total_articles = int(
                articles_result["results"]["bindings"][0]["count"]["value"]
            )

        total_triples = 0
        if triples_result.get("results", {}).get("bindings"):
            total_triples = int(
                triples_result["results"]["bindings"][0]["count"]["value"]
            )

        entity_breakdown = {}
        total_entities = 0
        for binding in entities_result.get("results", {}).get("bindings", []):
            type_uri = binding["type"]["value"]
            type_name = type_uri.split("#")[-1]
            count = int(binding["count"]["value"])
            entity_breakdown[type_name] = count
            total_entities += count

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
            "totalTriples": total_triples,
            "totalEntities": total_entities,
            "entityBreakdown": entity_breakdown,
            "dateRange": date_range,
        }

    async def get_entity_detail(self, entity_id: str) -> Dict[str, Any]:
        """エンティティの詳細情報を取得"""
        entity_uri = f"{self.ns}{entity_id}"

        basic_query = f"""
        PREFIX newskg: <{self.ns}>

        SELECT ?type ?label ?alias
        WHERE {{
            <{entity_uri}> a ?type .
            OPTIONAL {{ <{entity_uri}> newskg:hasLabel ?label }}
            OPTIONAL {{ <{entity_uri}> newskg:hasAlias ?alias }}
        }}
        LIMIT 1
        """

        articles_query = f"""
        PREFIX newskg: <{self.ns}>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT DISTINCT ?articleId ?title ?url ?pubDate
        WHERE {{
            ?triple a newskg:NewsTriple ;
                    newskg:extractedFrom ?article .
            {{
                ?triple rdf:subject <{entity_uri}> .
            }}
            UNION
            {{
                ?triple rdf:object <{entity_uri}> .
            }}
            ?article newskg:hasTitle ?title ;
                     newskg:hasUrl ?url ;
                     newskg:hasPubDate ?pubDate .
            BIND(REPLACE(STR(?article), "{self.ns}", "") AS ?articleId)
        }}
        ORDER BY DESC(?pubDate)
        LIMIT 10
        """

        related_triples_query = f"""
        PREFIX newskg: <{self.ns}>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?subjectLabel ?predicateLabel ?objectLabel
        WHERE {{
            ?triple a newskg:NewsTriple ;
                    rdf:subject ?subject ;
                    rdf:predicate ?predicate ;
                    rdf:object ?object .
            {{
                FILTER(?subject = <{entity_uri}> || ?object = <{entity_uri}>)
            }}
            OPTIONAL {{ ?subject newskg:hasLabel ?subjectLabel }}
            OPTIONAL {{ ?predicate rdfs:label ?predicateLabel }}
            OPTIONAL {{ ?object newskg:hasLabel ?objectLabel }}
        }}
        LIMIT 10
        """

        connection_query = f"""
        PREFIX newskg: <{self.ns}>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT (COUNT(*) AS ?count)
        WHERE {{
            {{
                ?triple rdf:subject <{entity_uri}> .
            }}
            UNION
            {{
                ?triple rdf:object <{entity_uri}> .
            }}
        }}
        """

        basic_result = await self.execute_query(basic_query)
        articles_result = await self.execute_query(articles_query)
        related_result = await self.execute_query(related_triples_query)
        connection_result = await self.execute_query(connection_query)

        entity_type = "Entity"
        label = entity_id
        properties = {}

        if basic_result.get("results", {}).get("bindings"):
            binding = basic_result["results"]["bindings"][0]
            entity_type = binding["type"]["value"].split("#")[-1]
            if "label" in binding:
                label = binding["label"]["value"]
            if "alias" in binding:
                properties["alias"] = binding["alias"]["value"]

        related_articles = []
        for binding in articles_result.get("results", {}).get("bindings", []):
            related_articles.append({
                "id": binding["articleId"]["value"],
                "title": binding["title"]["value"],
                "url": binding["url"]["value"],
                "pubDate": binding.get("pubDate", {}).get("value"),
            })

        related_triples = []
        for binding in related_result.get("results", {}).get("bindings", []):
            related_triples.append({
                "subject": binding.get("subjectLabel", {}).get("value", "?"),
                "predicate": binding.get("predicateLabel", {}).get("value", "?"),
                "object": binding.get("objectLabel", {}).get("value", "?"),
            })

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
            "relatedTriples": related_triples,
            "connectionCount": connection_count,
        }


# シングルトンインスタンス
sparql_client_v2 = SPARQLClientV2()

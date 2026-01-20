"""
Fusekiアップローダーモジュール

生成されたRDFデータをApache Jena Fusekiサーバーにアップロードします。
"""

import requests
from typing import Optional, Dict, Any
from pathlib import Path
import logging


class FusekiUploader:
    """Fusekiサーバーへのアップロードを行うクラス"""

    def __init__(
        self,
        endpoint: str = "http://localhost:3030",
        dataset: str = "NewsKG"
    ):
        """
        Args:
            endpoint: Fusekiサーバーのベースエンドポイント
            dataset: データセット名
        """
        self.endpoint = endpoint.rstrip("/")
        self.dataset = dataset
        self.logger = logging.getLogger(__name__)

        # エンドポイントURL
        self.data_endpoint = f"{self.endpoint}/{dataset}/data"
        self.query_endpoint = f"{self.endpoint}/{dataset}/query"
        self.update_endpoint = f"{self.endpoint}/{dataset}/update"

    def check_connection(self) -> bool:
        """
        Fusekiサーバーへの接続を確認

        Returns:
            接続成功ならTrue
        """
        try:
            response = requests.get(f"{self.endpoint}/$/ping", timeout=5)
            return response.status_code == 200
        except requests.RequestException as e:
            self.logger.error(f"Fuseki接続エラー: {e}")
            return False

    def upload_file(
        self,
        file_path: str,
        graph_uri: Optional[str] = None,
        replace: bool = False
    ) -> Dict[str, Any]:
        """
        RDFファイルをFusekiにアップロード

        Args:
            file_path: アップロードするRDFファイルのパス
            graph_uri: 名前付きグラフのURI（Noneの場合はデフォルトグラフ）
            replace: Trueの場合、既存データを置換

        Returns:
            アップロード結果の辞書
        """
        file_path = Path(file_path)
        if not file_path.exists():
            return {
                "success": False,
                "error": f"ファイルが見つかりません: {file_path}"
            }

        # Content-Typeを拡張子から判定
        content_type_map = {
            ".ttl": "text/turtle",
            ".rdf": "application/rdf+xml",
            ".xml": "application/rdf+xml",
            ".nt": "application/n-triples",
            ".nq": "application/n-quads",
            ".jsonld": "application/ld+json",
        }
        content_type = content_type_map.get(
            file_path.suffix.lower(), "text/turtle"
        )

        # アップロードURL構築
        url = self.data_endpoint
        if graph_uri:
            url = f"{url}?graph={graph_uri}"

        # HTTPメソッド選択
        method = "PUT" if replace else "POST"

        try:
            with open(file_path, "rb") as f:
                headers = {"Content-Type": content_type}
                if method == "PUT":
                    response = requests.put(url, data=f, headers=headers, timeout=60)
                else:
                    response = requests.post(url, data=f, headers=headers, timeout=60)

            if response.status_code in (200, 201, 204):
                self.logger.info(f"アップロード成功: {file_path}")
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "message": f"アップロード成功: {file_path.name}",
                    "endpoint": url,
                }
            else:
                self.logger.error(
                    f"アップロード失敗: {response.status_code} - {response.text}"
                )
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error": response.text,
                }

        except requests.RequestException as e:
            self.logger.error(f"アップロードエラー: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def upload_data(
        self,
        data: str,
        content_type: str = "text/turtle",
        graph_uri: Optional[str] = None,
        replace: bool = False
    ) -> Dict[str, Any]:
        """
        RDFデータ文字列をFusekiにアップロード

        Args:
            data: RDFデータ文字列
            content_type: データのContent-Type
            graph_uri: 名前付きグラフのURI
            replace: Trueの場合、既存データを置換

        Returns:
            アップロード結果の辞書
        """
        url = self.data_endpoint
        if graph_uri:
            url = f"{url}?graph={graph_uri}"

        method = "PUT" if replace else "POST"

        try:
            headers = {"Content-Type": content_type}
            if method == "PUT":
                response = requests.put(
                    url, data=data.encode("utf-8"), headers=headers, timeout=60
                )
            else:
                response = requests.post(
                    url, data=data.encode("utf-8"), headers=headers, timeout=60
                )

            if response.status_code in (200, 201, 204):
                self.logger.info("データアップロード成功")
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "message": "アップロード成功",
                }
            else:
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error": response.text,
                }

        except requests.RequestException as e:
            return {
                "success": False,
                "error": str(e),
            }

    def clear_graph(self, graph_uri: Optional[str] = None) -> Dict[str, Any]:
        """
        グラフのデータをクリア

        Args:
            graph_uri: クリアするグラフのURI（Noneの場合はデフォルトグラフ）

        Returns:
            結果の辞書
        """
        if graph_uri:
            sparql = f"CLEAR GRAPH <{graph_uri}>"
        else:
            sparql = "CLEAR DEFAULT"

        try:
            response = requests.post(
                self.update_endpoint,
                data={"update": sparql},
                timeout=30
            )

            if response.status_code in (200, 204):
                self.logger.info(f"グラフクリア成功")
                return {"success": True, "message": "グラフをクリアしました"}
            else:
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error": response.text,
                }

        except requests.RequestException as e:
            return {"success": False, "error": str(e)}

    def get_triple_count(self, graph_uri: Optional[str] = None) -> int:
        """
        グラフ内のトリプル数を取得

        Args:
            graph_uri: 対象グラフのURI

        Returns:
            トリプル数（エラー時は-1）
        """
        if graph_uri:
            sparql = f"SELECT (COUNT(*) AS ?count) WHERE {{ GRAPH <{graph_uri}> {{ ?s ?p ?o }} }}"
        else:
            sparql = "SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o }"

        try:
            response = requests.get(
                self.query_endpoint,
                params={"query": sparql},
                headers={"Accept": "application/sparql-results+json"},
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                count = int(result["results"]["bindings"][0]["count"]["value"])
                return count
            else:
                return -1

        except (requests.RequestException, KeyError, ValueError):
            return -1

    def get_statistics(self) -> Dict[str, Any]:
        """
        データセットの統計情報を取得

        Returns:
            統計情報の辞書
        """
        triple_count = self.get_triple_count()

        # クラス別のインスタンス数を取得
        class_count_sparql = """
        SELECT ?class (COUNT(?s) AS ?count)
        WHERE {
            ?s a ?class .
        }
        GROUP BY ?class
        ORDER BY DESC(?count)
        """

        class_counts = {}
        try:
            response = requests.get(
                self.query_endpoint,
                params={"query": class_count_sparql},
                headers={"Accept": "application/sparql-results+json"},
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                for binding in result["results"]["bindings"]:
                    class_uri = binding["class"]["value"]
                    count = int(binding["count"]["value"])
                    # URIからローカル名を抽出
                    local_name = class_uri.split("#")[-1].split("/")[-1]
                    class_counts[local_name] = count

        except (requests.RequestException, KeyError, ValueError):
            pass

        return {
            "total_triples": triple_count,
            "class_counts": class_counts,
            "endpoint": self.endpoint,
            "dataset": self.dataset,
        }

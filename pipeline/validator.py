"""
SHACL検証モジュール

生成されたRDFデータをSHACL制約で検証します。
"""

from typing import Tuple, Optional
from pathlib import Path
from rdflib import Graph
from rdflib.namespace import RDF, SH
from pyshacl import validate

from ontology import SHAPES_TTL


class SHACLValidator:
    """SHACL検証を行うクラス"""

    def __init__(self, shapes_path: Optional[str] = None):
        """
        Args:
            shapes_path: SHACLシェイプファイルのパス
        """
        self.shapes_path = Path(shapes_path) if shapes_path else SHAPES_TTL
        self.shapes_graph = None
        self._load_shapes()

    def _load_shapes(self):
        """SHACLシェイプをロード"""
        if self.shapes_path.exists():
            self.shapes_graph = Graph()
            self.shapes_graph.parse(str(self.shapes_path), format="turtle")

    def validate(
        self, data_path_or_graph, inference: str = "none"
    ) -> Tuple[bool, str, Graph]:
        """
        RDFデータをSHACL検証

        Args:
            data_path_or_graph: RDFデータのパスまたはGraphオブジェクト
            inference: 推論モード ("none", "rdfs", "owlrl")

        Returns:
            (適合性, 検証レポートテキスト, 検証結果グラフ)
        """
        # データグラフをロード
        if isinstance(data_path_or_graph, Graph):
            data_graph = data_path_or_graph
        else:
            data_graph = Graph()
            data_graph.parse(str(data_path_or_graph), format="turtle")

        if self.shapes_graph is None:
            return True, "シェイプファイルが見つかりません（検証スキップ）", Graph()

        # SHACL検証を実行
        conforms, results_graph, results_text = validate(
            data_graph,
            shacl_graph=self.shapes_graph,
            inference=inference,
            abort_on_first=False,
            meta_shacl=False,
            debug=False,
        )

        return conforms, results_text, results_graph

    def validate_file(self, data_path: str) -> Tuple[bool, str]:
        """
        ファイルからRDFデータを読み込んで検証

        Args:
            data_path: RDFデータファイルのパス

        Returns:
            (適合性, 検証レポートテキスト)
        """
        conforms, results_text, _ = self.validate(data_path)
        return conforms, results_text

    def get_validation_summary(
        self, data_path_or_graph
    ) -> dict:
        """
        検証結果のサマリーを取得

        Args:
            data_path_or_graph: RDFデータのパスまたはGraphオブジェクト

        Returns:
            検証結果のサマリー辞書
        """
        conforms, results_text, results_graph = self.validate(data_path_or_graph)

        # 違反の数をカウント（SHACL語彙に基づく）
        violation_count = 0
        if not conforms:
            # sh:ValidationResult を数える
            violation_count = sum(
                1
                for _ in results_graph.triples((None, RDF.type, SH.ValidationResult))
            )

        return {
            "conforms": conforms,
            "violation_count": violation_count,
            "report": results_text if not conforms else "データは全ての制約に適合しています",
        }

"""
述語正規化モジュール

抽出された述語を正規化し、類似述語を統合します。
バッチ処理でLLMを使った正規化も行います。
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import Counter

from .llm_client import OpenRouterClient, get_client


@dataclass
class PredicateEntry:
    """述語マスターのエントリ"""
    id: str
    label: str
    aliases: List[str]
    category: str


class PredicateNormalizer:
    """述語の正規化を行うクラス"""
    
    def __init__(self, master_path: Optional[Path] = None):
        """
        Args:
            master_path: 述語マスターJSONのパス
        """
        if master_path is None:
            master_path = Path(__file__).parent.parent / "dictionaries" / "predicates" / "predicate_master.json"
        
        self.master_path = master_path
        self.predicates: Dict[str, PredicateEntry] = {}
        self.alias_to_id: Dict[str, str] = {}
        self.unknown_predicates: Counter = Counter()  # 未知の述語をカウント
        self.logger = logging.getLogger(__name__)
        
        self._load_master()
    
    def _load_master(self):
        """述語マスターを読み込み"""
        if not self.master_path.exists():
            self.logger.warning(f"述語マスターが見つかりません: {self.master_path}")
            return
        
        with open(self.master_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for p in data.get("predicates", []):
            entry = PredicateEntry(
                id=p["id"],
                label=p["label"],
                aliases=p.get("aliases", []),
                category=p.get("category", "other")
            )
            self.predicates[entry.id] = entry
            
            # ラベルとエイリアスをマッピング
            self.alias_to_id[entry.label] = entry.id
            for alias in entry.aliases:
                self.alias_to_id[alias] = entry.id
    
    def normalize(self, predicate: str) -> Tuple[str, str]:
        """
        述語を正規化
        
        Args:
            predicate: 正規化する述語
        
        Returns:
            (正規化された述語ID, ラベル) のタプル
            マスターにない場合は (元の述語, 元の述語) を返す
        """
        # 完全一致
        if predicate in self.alias_to_id:
            pid = self.alias_to_id[predicate]
            return pid, self.predicates[pid].label
        
        # 部分一致を試みる
        for alias, pid in self.alias_to_id.items():
            if alias in predicate or predicate in alias:
                return pid, self.predicates[pid].label
        
        # マスターにない場合
        self.unknown_predicates[predicate] += 1
        return predicate, predicate
    
    def normalize_triple(self, triple: Dict) -> Dict:
        """
        トリプルの述語を正規化
        
        Args:
            triple: トリプル辞書
        
        Returns:
            正規化されたトリプル辞書
        """
        predicate = triple.get("predicate", "")
        pred_id, pred_label = self.normalize(predicate)
        
        return {
            **triple,
            "predicate_id": pred_id,
            "predicate_label": pred_label,
            "predicate_original": predicate
        }
    
    def get_unknown_predicates(self) -> List[Tuple[str, int]]:
        """未知の述語とその出現回数を取得"""
        return self.unknown_predicates.most_common()
    
    def add_predicate(self, id: str, label: str, aliases: List[str] = None, category: str = "other"):
        """
        新しい述語をマスターに追加
        
        Args:
            id: 述語ID
            label: 述語ラベル
            aliases: エイリアスリスト
            category: カテゴリ
        """
        aliases = aliases or []
        entry = PredicateEntry(id=id, label=label, aliases=aliases, category=category)
        self.predicates[id] = entry
        
        self.alias_to_id[label] = id
        for alias in aliases:
            self.alias_to_id[alias] = id
    
    def save_master(self):
        """述語マスターを保存"""
        data = {
            "predicates": [
                {
                    "id": p.id,
                    "label": p.label,
                    "aliases": p.aliases,
                    "category": p.category
                }
                for p in self.predicates.values()
            ]
        }
        
        self.master_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.master_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


class PredicateBatchNormalizer:
    """バッチ処理で述語を正規化するクラス（LLM使用）"""
    
    SYSTEM_PROMPT = """あなたは日本語の述語（動詞・動作を表す語句）を正規化する専門家です。

## タスク
与えられた述語リストを分析し、類似した述語をグループ化して正規化してください。

## 出力形式
JSON形式で以下の構造で出力してください：
{
  "groups": [
    {
      "canonical": "正規化された述語（代表形）",
      "members": ["元の述語1", "元の述語2", ...],
      "category": "カテゴリ（position/action/event/diplomacy/crime/business/other）"
    }
  ]
}

## ルール
1. 同じ意味の述語は1つのグループにまとめる
2. 代表形は最も一般的で簡潔な表現を選ぶ
3. 「する」は省略する（例: 「発表する」→「発表」）
4. 出現回数が多いものを優先的に代表形にする"""

    def __init__(self, client: Optional[OpenRouterClient] = None, normalizer: Optional[PredicateNormalizer] = None):
        self.client = client or get_client()
        self.normalizer = normalizer or PredicateNormalizer()
        self.logger = logging.getLogger(__name__)
    
    def normalize_batch(self, predicates: List[str]) -> Dict[str, str]:
        """
        述語リストをバッチで正規化
        
        Args:
            predicates: 正規化する述語のリスト
        
        Returns:
            {元の述語: 正規化された述語} のマッピング
        """
        if not predicates:
            return {}
        
        # 重複を除去してカウント
        pred_counts = Counter(predicates)
        unique_preds = list(pred_counts.keys())
        
        # まず既存マスターで正規化を試みる
        mapping = {}
        unknown = []
        
        for pred in unique_preds:
            pred_id, pred_label = self.normalizer.normalize(pred)
            if pred_id != pred:  # マスターにあった
                mapping[pred] = pred_label
            else:
                unknown.append(pred)
        
        # 未知の述語が少なければLLMは使わない
        if len(unknown) < 5:
            for pred in unknown:
                mapping[pred] = pred
            return mapping
        
        # LLMで正規化
        try:
            result = self._llm_normalize(unknown, pred_counts)
            mapping.update(result)
        except Exception as e:
            self.logger.error(f"LLM正規化エラー: {e}")
            # フォールバック: そのまま使用
            for pred in unknown:
                mapping[pred] = pred
        
        return mapping
    
    def _llm_normalize(self, predicates: List[str], counts: Counter) -> Dict[str, str]:
        """LLMを使って述語を正規化"""
        # 出現回数付きのリストを作成
        pred_list = [f"- {p} ({counts[p]}回)" for p in predicates]
        
        user_prompt = f"""以下の述語リストを正規化してください。括弧内は出現回数です。

{chr(10).join(pred_list)}

JSON形式で出力してください。"""

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        response = self.client.chat_json(messages, temperature=0.1)
        
        # 結果をマッピングに変換
        mapping = {}
        for group in response.get("groups", []):
            canonical = group.get("canonical", "")
            members = group.get("members", [])
            category = group.get("category", "other")
            
            for member in members:
                mapping[member] = canonical
            
            # マスターに追加
            if canonical and members:
                pred_id = canonical.replace(" ", "_").lower()
                self.normalizer.add_predicate(
                    id=pred_id,
                    label=canonical,
                    aliases=[m for m in members if m != canonical],
                    category=category
                )
        
        # マスターを保存
        self.normalizer.save_master()
        
        return mapping


# シングルトンインスタンス
_normalizer: Optional[PredicateNormalizer] = None


def get_normalizer() -> PredicateNormalizer:
    """シングルトンの正規化器を取得"""
    global _normalizer
    if _normalizer is None:
        _normalizer = PredicateNormalizer()
    return _normalizer

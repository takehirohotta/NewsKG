"""
辞書ローダーモジュール

JSONファイルからエンティティ辞書を読み込み、検索可能な形式で提供します。
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class DictionaryEntry:
    """辞書エントリを表すデータクラス"""
    id: str
    label: str
    aliases: List[str]
    entity_type: str  # organization, person, place
    extra: Dict  # その他の属性


class DictionaryLoader:
    """エンティティ辞書の読み込みと検索を行うクラス"""

    def __init__(self, dictionaries_dir: Optional[Path] = None):
        """
        Args:
            dictionaries_dir: 辞書ファイルが格納されているディレクトリ
        """
        if dictionaries_dir is None:
            dictionaries_dir = Path(__file__).parent
        self.dictionaries_dir = dictionaries_dir

        # エンティティを格納
        self.organizations: Dict[str, DictionaryEntry] = {}
        self.persons: Dict[str, DictionaryEntry] = {}
        self.places: Dict[str, DictionaryEntry] = {}

        # テキストからエンティティへのマッピング（検索用）
        self._text_to_entity: Dict[str, DictionaryEntry] = {}

        # 辞書をロード
        self._load_all()

    def _load_all(self):
        """全ての辞書ファイルをロード"""
        self._load_organizations()
        self._load_persons()
        self._load_places()

    def _load_organizations(self):
        """組織辞書をロード"""
        path = self.dictionaries_dir / "organizations.json"
        if not path.exists():
            return

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for org in data.get("organizations", []):
            entry = DictionaryEntry(
                id=org["id"],
                label=org["label"],
                aliases=org.get("aliases", []),
                entity_type="organization",
                extra={"org_type": org.get("type")}
            )
            self.organizations[entry.id] = entry
            self._register_text_mapping(entry)

    def _load_persons(self):
        """人物辞書をロード"""
        path = self.dictionaries_dir / "persons.json"
        if not path.exists():
            return

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for person in data.get("persons", []):
            entry = DictionaryEntry(
                id=person["id"],
                label=person["label"],
                aliases=person.get("aliases", []),
                entity_type="person",
                extra={
                    "role": person.get("role"),
                    "organization": person.get("organization")
                }
            )
            self.persons[entry.id] = entry
            self._register_text_mapping(entry)

    def _load_places(self):
        """場所辞書をロード"""
        path = self.dictionaries_dir / "places.json"
        if not path.exists():
            return

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for place in data.get("places", []):
            entry = DictionaryEntry(
                id=place["id"],
                label=place["label"],
                aliases=place.get("aliases", []),
                entity_type="place",
                extra={"place_type": place.get("type")}
            )
            self.places[entry.id] = entry
            self._register_text_mapping(entry)

    def _register_text_mapping(self, entry: DictionaryEntry):
        """テキストからエンティティへのマッピングを登録"""
        # ラベルを登録
        self._text_to_entity[entry.label] = entry
        # 別名を登録
        for alias in entry.aliases:
            if alias:  # 空文字列をスキップ
                self._text_to_entity[alias] = entry

    def find_entity(self, text: str) -> Optional[DictionaryEntry]:
        """
        テキストからエンティティを検索

        Args:
            text: 検索するテキスト

        Returns:
            マッチしたエンティティ、見つからない場合はNone
        """
        return self._text_to_entity.get(text)

    def find_entities_in_text(self, text: str) -> List[tuple]:
        """
        テキスト内のエンティティを全て検索

        Args:
            text: 検索対象のテキスト

        Returns:
            (開始位置, 終了位置, エンティティ) のタプルのリスト
        """
        results = []
        # 長いテキストから先にマッチさせる（貪欲マッチ）
        sorted_keys = sorted(self._text_to_entity.keys(), key=len, reverse=True)

        matched_positions = set()

        for key in sorted_keys:
            start = 0
            while True:
                pos = text.find(key, start)
                if pos == -1:
                    break
                end_pos = pos + len(key)

                # 既にマッチした位置と重複していないか確認
                is_overlapping = any(
                    pos < mp_end and end_pos > mp_start
                    for mp_start, mp_end in matched_positions
                )

                if not is_overlapping:
                    entry = self._text_to_entity[key]
                    results.append((pos, end_pos, entry))
                    matched_positions.add((pos, end_pos))

                start = pos + 1

        # 位置順にソート
        results.sort(key=lambda x: x[0])
        return results

    def get_all_entries(self) -> List[DictionaryEntry]:
        """全エンティティを取得"""
        all_entries = []
        all_entries.extend(self.organizations.values())
        all_entries.extend(self.persons.values())
        all_entries.extend(self.places.values())
        return all_entries

    def get_statistics(self) -> Dict[str, int]:
        """辞書の統計情報を取得"""
        return {
            "organizations": len(self.organizations),
            "persons": len(self.persons),
            "places": len(self.places),
            "total_entries": len(self.organizations) + len(self.persons) + len(self.places),
            "total_searchable_terms": len(self._text_to_entity)
        }


# モジュールレベルのローダーインスタンス
_loader: Optional[DictionaryLoader] = None


def get_loader() -> DictionaryLoader:
    """シングルトンのローダーを取得"""
    global _loader
    if _loader is None:
        _loader = DictionaryLoader()
    return _loader

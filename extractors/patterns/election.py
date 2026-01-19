"""
選挙関連パターン抽出

解散表明、選挙結果、立候補表明などのパターンを検出します。
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class PatternMatch:
    """パターンマッチ結果"""
    pattern_type: str  # DissolutionAnnouncement, ElectionResult, etc.
    matched_text: str
    confidence: float
    extracted_data: Dict[str, Any]
    start: int
    end: int


class ElectionPatterns:
    """選挙関連パターンの検出クラス"""

    # 解散関連のトリガーワード
    DISSOLUTION_TRIGGERS = [
        "解散", "衆院解散", "衆議院解散", "衆議院を解散"
    ]

    # 選挙関連のトリガーワード
    ELECTION_TRIGGERS = [
        "選挙", "総選挙", "衆院選", "参院選", "衆議院選挙", "参議院選挙",
        "投票", "当選", "落選", "公示", "告示"
    ]

    # 立候補関連のトリガーワード
    CANDIDACY_TRIGGERS = [
        "立候補", "出馬", "擁立", "公認"
    ]

    # 解散表明パターン
    DISSOLUTION_PATTERNS = [
        # パターン1: 〇〇が解散を表明
        (r'(.{2,10}?)が.{0,5}解散.{0,5}(表明|発表|方針|意向)', 0.9),
        # パターン2: 衆議院を解散
        (r'衆議院を解散', 0.85),
        # パターン3: 解散総選挙
        (r'解散総選挙', 0.8),
        # パターン4: 〇〇首相/総理が解散
        (r'(.{2,6})(首相|総理|総理大臣).{0,10}解散', 0.9),
    ]

    # 選挙日程パターン
    ELECTION_DATE_PATTERNS = [
        # パターン1: X月X日投票
        (r'(\d{1,2})月(\d{1,2})日.{0,3}投票', 0.85),
        # パターン2: X月X日に投開票
        (r'(\d{1,2})月(\d{1,2})日.{0,3}投開票', 0.85),
    ]

    # 当選パターン
    ELECTION_RESULT_PATTERNS = [
        # パターン1: 〇〇が当選
        (r'(.{2,10}?)が.{0,5}当選', 0.8),
        # パターン2: 〇〇氏が当選確実
        (r'(.{2,10}?)氏.{0,5}当選(確実)?', 0.85),
    ]

    # 立候補パターン
    CANDIDACY_PATTERNS = [
        # パターン1: 〇〇が立候補を表明
        (r'(.{2,10}?)が.{0,5}立候補.{0,5}(表明|発表)', 0.8),
        # パターン2: 〇〇が出馬を表明
        (r'(.{2,10}?)が.{0,5}出馬.{0,5}(表明|発表|意向)', 0.8),
        # パターン3: 〇〇を擁立
        (r'(.{2,10}?)を.{0,5}擁立', 0.75),
    ]

    def extract(self, text: str) -> List[PatternMatch]:
        """
        テキストから選挙関連パターンを抽出

        Args:
            text: 検索対象テキスト

        Returns:
            PatternMatchのリスト
        """
        results = []

        # 解散パターンの検出
        if self._has_trigger(text, self.DISSOLUTION_TRIGGERS):
            results.extend(self._extract_dissolution(text))

        # 選挙結果パターンの検出
        if self._has_trigger(text, self.ELECTION_TRIGGERS):
            results.extend(self._extract_election_result(text))

        # 立候補パターンの検出
        if self._has_trigger(text, self.CANDIDACY_TRIGGERS):
            results.extend(self._extract_candidacy(text))

        return results

    def _has_trigger(self, text: str, triggers: List[str]) -> bool:
        """トリガーワードの存在チェック"""
        return any(trigger in text for trigger in triggers)

    def _extract_dissolution(self, text: str) -> List[PatternMatch]:
        """解散パターンを抽出"""
        results = []

        for pattern, confidence in self.DISSOLUTION_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                extracted_data = {
                    "full_match": match.group(0),
                }

                # 表明者の抽出（グループがある場合）
                if match.lastindex and match.lastindex >= 1:
                    declarer = match.group(1)
                    if declarer and len(declarer) > 1:
                        extracted_data["declarer"] = declarer

                results.append(PatternMatch(
                    pattern_type="DissolutionAnnouncement",
                    matched_text=match.group(0),
                    confidence=confidence,
                    extracted_data=extracted_data,
                    start=match.start(),
                    end=match.end()
                ))

        # 選挙日程の抽出
        for pattern, confidence in self.ELECTION_DATE_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                results.append(PatternMatch(
                    pattern_type="ElectionSchedule",
                    matched_text=match.group(0),
                    confidence=confidence,
                    extracted_data={
                        "month": match.group(1),
                        "day": match.group(2),
                    },
                    start=match.start(),
                    end=match.end()
                ))

        return results

    def _extract_election_result(self, text: str) -> List[PatternMatch]:
        """選挙結果パターンを抽出"""
        results = []

        for pattern, confidence in self.ELECTION_RESULT_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                candidate = match.group(1) if match.lastindex >= 1 else None
                results.append(PatternMatch(
                    pattern_type="ElectionResult",
                    matched_text=match.group(0),
                    confidence=confidence,
                    extracted_data={
                        "candidate": candidate,
                        "result": "当選"
                    },
                    start=match.start(),
                    end=match.end()
                ))

        return results

    def _extract_candidacy(self, text: str) -> List[PatternMatch]:
        """立候補パターンを抽出"""
        results = []

        for pattern, confidence in self.CANDIDACY_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                candidate = match.group(1) if match.lastindex >= 1 else None
                results.append(PatternMatch(
                    pattern_type="CandidateAnnouncement",
                    matched_text=match.group(0),
                    confidence=confidence,
                    extracted_data={
                        "candidate": candidate,
                    },
                    start=match.start(),
                    end=match.end()
                ))

        return results

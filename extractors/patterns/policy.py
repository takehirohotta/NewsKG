"""
政策関連パターン抽出

政策発表、予算決定、法制度イベントなどのパターンを検出します。
"""

import re
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class PatternMatch:
    """パターンマッチ結果"""
    pattern_type: str
    matched_text: str
    confidence: float
    extracted_data: Dict[str, Any]
    start: int
    end: int


class PolicyPatterns:
    """政策関連パターンの検出クラス"""

    # 政策発表トリガー
    POLICY_TRIGGERS = [
        "方針", "政策", "戦略", "計画", "構想", "発表", "決定", "表明"
    ]

    # 予算関連トリガー
    BUDGET_TRIGGERS = [
        "予算", "予備費", "補正予算", "支出", "歳出", "拠出", "交付"
    ]

    # 法制度トリガー
    LEGISLATION_TRIGGERS = [
        "法案", "法律", "条例", "規制", "改正", "成立", "施行", "可決"
    ]

    # 外交・国際トリガー
    DIPLOMACY_TRIGGERS = [
        "会談", "首脳", "外交", "訪問", "制裁", "関税"
    ]

    # 政策発表パターン
    POLICY_PATTERNS = [
        # 政府が〇〇を発表
        (r'(政府|内閣|省庁?).{0,5}(方針|政策|計画|構想).{0,5}(発表|決定|表明)', 0.85),
        # 〇〇省が方針
        (r'(\w{2,6}省).{0,10}(方針|政策).{0,5}(発表|決定)', 0.85),
        # 〇〇首相/総理が〇〇を表明
        (r'(.{2,6})(首相|総理|総理大臣).{0,15}(方針|意向|考え).{0,5}(示|表明)', 0.8),
        # 〇〇支援
        (r'(.{2,15})支援.{0,10}(発表|決定|方針)', 0.75),
    ]

    # 予算パターン
    BUDGET_PATTERNS = [
        # X億円/X兆円を支出
        (r'(\d+[\d,]*)\s*(億|兆)円.{0,10}(支出|拠出|交付|投入)', 0.9),
        # 予備費からX億円
        (r'予備費.{0,10}(\d+[\d,]*)\s*(億|兆)円', 0.9),
        # 補正予算X兆円
        (r'補正予算.{0,10}(\d+[\d,]*)\s*(億|兆)円', 0.85),
        # X億円の予算
        (r'(\d+[\d,]*)\s*(億|兆)円.{0,5}(予算|規模)', 0.8),
    ]

    # 法制度パターン
    LEGISLATION_PATTERNS = [
        # 〇〇法案が成立/可決
        (r'(.{2,15})法案.{0,5}(成立|可決|否決)', 0.9),
        # 〇〇法が施行
        (r'(.{2,15})法.{0,5}(施行|発効)', 0.85),
        # 〇〇を改正
        (r'(.{2,15})(法|条例).{0,5}改正', 0.8),
        # 規制を強化/緩和
        (r'(.{2,15})規制.{0,5}(強化|緩和)', 0.8),
    ]

    # 外交パターン
    DIPLOMACY_PATTERNS = [
        # 〇〇と会談
        (r'(.{2,10}?)と.{0,5}会談', 0.8),
        # 首脳会談
        (r'(.{2,10}?).{0,5}首脳会談', 0.85),
        # 〇〇を訪問
        (r'(.{2,10}?)を.{0,5}訪問', 0.75),
        # 〇〇に制裁
        (r'(.{2,10}?)に.{0,10}(制裁|関税)', 0.85),
    ]

    # 政策分野キーワード
    POLICY_AREAS = {
        "経済": ["経済", "景気", "成長", "物価", "金融", "財政"],
        "外交": ["外交", "国際", "外務", "首脳", "会談"],
        "防衛": ["防衛", "安全保障", "自衛隊", "軍事"],
        "社会保障": ["年金", "医療", "介護", "福祉", "保険"],
        "エネルギー": ["原発", "再稼働", "エネルギー", "電力", "原子力"],
        "環境": ["環境", "温暖化", "脱炭素", "CO2"],
        "教育": ["教育", "学校", "大学", "研究"],
    }

    def extract(self, text: str) -> List[PatternMatch]:
        """
        テキストから政策関連パターンを抽出

        Args:
            text: 検索対象テキスト

        Returns:
            PatternMatchのリスト
        """
        results = []

        # 予算パターン（優先度高）
        if self._has_trigger(text, self.BUDGET_TRIGGERS):
            results.extend(self._extract_budget(text))

        # 法制度パターン
        if self._has_trigger(text, self.LEGISLATION_TRIGGERS):
            results.extend(self._extract_legislation(text))

        # 外交パターン
        if self._has_trigger(text, self.DIPLOMACY_TRIGGERS):
            results.extend(self._extract_diplomacy(text))

        # 一般政策パターン
        if self._has_trigger(text, self.POLICY_TRIGGERS):
            results.extend(self._extract_policy(text))

        return results

    def _has_trigger(self, text: str, triggers: List[str]) -> bool:
        """トリガーワードの存在チェック"""
        return any(trigger in text for trigger in triggers)

    def _detect_policy_area(self, text: str) -> str:
        """政策分野を検出"""
        for area, keywords in self.POLICY_AREAS.items():
            if any(kw in text for kw in keywords):
                return area
        return "その他"

    def _extract_policy(self, text: str) -> List[PatternMatch]:
        """政策発表パターンを抽出"""
        results = []
        policy_area = self._detect_policy_area(text)

        for pattern, confidence in self.POLICY_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                extracted_data = {
                    "full_match": match.group(0),
                    "policy_area": policy_area
                }

                # アクターの抽出
                if match.lastindex >= 1:
                    extracted_data["actor"] = match.group(1)

                results.append(PatternMatch(
                    pattern_type="PolicyAnnouncement",
                    matched_text=match.group(0),
                    confidence=confidence,
                    extracted_data=extracted_data,
                    start=match.start(),
                    end=match.end()
                ))

        return results

    def _extract_budget(self, text: str) -> List[PatternMatch]:
        """予算パターンを抽出"""
        results = []
        policy_area = self._detect_policy_area(text)

        for pattern, confidence in self.BUDGET_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                extracted_data = {
                    "full_match": match.group(0),
                    "policy_area": policy_area
                }

                # 金額の抽出と円換算
                if match.lastindex >= 2:
                    try:
                        amount_str = match.group(1).replace(",", "")
                        amount = int(amount_str)
                        unit = match.group(2)
                        if unit == "億":
                            extracted_data["budget_amount_yen"] = amount * 100_000_000
                        elif unit == "兆":
                            extracted_data["budget_amount_yen"] = amount * 1_000_000_000_000
                        extracted_data["budget_display"] = f"{amount}{unit}円"
                    except (ValueError, TypeError):
                        pass

                results.append(PatternMatch(
                    pattern_type="PolicyAnnouncement",
                    matched_text=match.group(0),
                    confidence=confidence,
                    extracted_data=extracted_data,
                    start=match.start(),
                    end=match.end()
                ))


        return results

    def _extract_legislation(self, text: str) -> List[PatternMatch]:
        """法制度パターンを抽出"""
        results = []
        policy_area = self._detect_policy_area(text)

        for pattern, confidence in self.LEGISLATION_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                extracted_data = {
                    "full_match": match.group(0),
                    "policy_area": policy_area
                }

                # 法律名の抽出
                if match.lastindex >= 1:
                    extracted_data["legislation_name"] = match.group(1)

                # アクション種別
                if match.lastindex >= 2:
                    extracted_data["action"] = match.group(2)

                results.append(PatternMatch(
                    pattern_type="LegislationEvent",
                    matched_text=match.group(0),
                    confidence=confidence,
                    extracted_data=extracted_data,
                    start=match.start(),
                    end=match.end()
                ))


        return results

    def _extract_diplomacy(self, text: str) -> List[PatternMatch]:
        """外交パターンを抽出"""
        results = []

        for pattern, confidence in self.DIPLOMACY_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                extracted_data = {
                    "full_match": match.group(0),
                    "policy_area": "外交"
                }

                # 相手国・人物の抽出
                if match.lastindex >= 1:
                    extracted_data["counterpart"] = match.group(1)

                results.append(PatternMatch(
                    pattern_type="PolicyAnnouncement",
                    matched_text=match.group(0),
                    confidence=confidence,
                    extracted_data=extracted_data,
                    start=match.start(),
                    end=match.end()
                ))

        return results

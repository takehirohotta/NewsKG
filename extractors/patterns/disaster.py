"""
災害関連パターン抽出

地震、気象災害、避難指示などのパターンを検出します。
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


class DisasterPatterns:
    """災害関連パターンの検出クラス"""

    # 地震関連トリガー
    EARTHQUAKE_TRIGGERS = ["地震", "震度", "マグニチュード", "M"]

    # 気象災害トリガー
    WEATHER_TRIGGERS = ["台風", "大雪", "豪雨", "暴風", "洪水", "津波", "氾濫"]

    # 避難関連トリガー
    EVACUATION_TRIGGERS = ["避難", "避難指示", "避難勧告", "避難所"]

    # 火災関連トリガー
    FIRE_TRIGGERS = ["火災", "延焼", "山林火災", "山火事"]

    # 地震パターン
    EARTHQUAKE_PATTERNS = [
        # パターン1: 震度X
        (r'震度(1|2|3|4|5弱|5強|6弱|6強|7)', 0.9),
        # パターン2: マグニチュードX.X
        (r'マグニチュード\s*(\d+\.?\d*)', 0.85),
        # パターン3: MX.X
        (r'[M|Ｍ]\s*(\d+\.?\d*)', 0.7),
        # パターン4: 〇〇で地震
        (r'(.{2,10}?)で.{0,5}地震', 0.75),
    ]

    # 気象災害パターン
    WEATHER_PATTERNS = [
        # 台風パターン
        (r'台風(\d+)号', 0.9),
        (r'台風.{0,10}(接近|上陸|通過)', 0.85),
        # 大雪パターン
        (r'大雪.{0,10}(警報|注意報|予想)', 0.85),
        (r'積雪.{0,5}(\d+)\s*(センチ|cm|ｃｍ)', 0.8),
        # 豪雨パターン
        (r'(記録的な?)?豪雨', 0.8),
        (r'大雨.{0,10}(警報|特別警報)', 0.85),
        # 津波パターン
        (r'津波.{0,10}(警報|注意報)', 0.9),
        (r'津波.{0,5}(発生|到達|観測)', 0.85),
    ]

    # 避難パターン
    EVACUATION_PATTERNS = [
        # 避難指示パターン
        (r'(.{2,10}?)に.{0,5}避難指示', 0.9),
        (r'避難指示.{0,10}(発令|発出|解除)', 0.85),
        # 避難者数パターン
        (r'(\d+[\d,]*)人.{0,5}避難', 0.75),
        # 避難所パターン
        (r'避難所.{0,5}(開設|設置)', 0.8),
    ]

    # 被害パターン
    DAMAGE_PATTERNS = [
        # 死傷者パターン
        (r'(\d+)人.{0,3}(死亡|けが|負傷|行方不明)', 0.85),
        # 建物被害パターン
        (r'(住宅|家屋|建物).{0,10}(倒壊|損壊|浸水)', 0.8),
        # 停電パターン
        (r'(\d+[\d,]*)戸?.{0,5}停電', 0.8),
    ]

    # 火災パターン
    FIRE_PATTERNS = [
        # 山林火災
        (r'(山林|森林)火災', 0.9),
        (r'延焼.{0,10}(続|広が)', 0.85),
        # 鎮火状況
        (r'(鎮火|消火).{0,10}(めど|見通し)', 0.8),
    ]

    def extract(self, text: str) -> List[PatternMatch]:
        """
        テキストから災害関連パターンを抽出

        Args:
            text: 検索対象テキスト

        Returns:
            PatternMatchのリスト
        """
        results = []

        # 地震パターン
        if self._has_trigger(text, self.EARTHQUAKE_TRIGGERS):
            results.extend(self._extract_earthquake(text))

        # 気象災害パターン
        if self._has_trigger(text, self.WEATHER_TRIGGERS):
            results.extend(self._extract_weather(text))

        # 避難パターン
        if self._has_trigger(text, self.EVACUATION_TRIGGERS):
            results.extend(self._extract_evacuation(text))

        # 火災パターン
        if self._has_trigger(text, self.FIRE_TRIGGERS):
            results.extend(self._extract_fire(text))

        # 被害パターン（常にチェック）
        results.extend(self._extract_damage(text))

        return results

    def _has_trigger(self, text: str, triggers: List[str]) -> bool:
        """トリガーワードの存在チェック"""
        return any(trigger in text for trigger in triggers)

    def _extract_earthquake(self, text: str) -> List[PatternMatch]:
        """地震パターンを抽出"""
        results = []

        for pattern, confidence in self.EARTHQUAKE_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                extracted_data = {"full_match": match.group(0)}

                # 震度抽出
                if "震度" in pattern:
                    extracted_data["seismic_intensity"] = match.group(1)

                # マグニチュード抽出
                if "マグニチュード" in pattern or "M" in pattern:
                    extracted_data["magnitude"] = float(match.group(1))

                # 発生場所抽出
                if "で" in pattern and match.lastindex >= 1:
                    extracted_data["location"] = match.group(1)

                results.append(PatternMatch(
                    pattern_type="EarthquakeEvent",
                    matched_text=match.group(0),
                    confidence=confidence,
                    extracted_data=extracted_data,
                    start=match.start(),
                    end=match.end()
                ))

        return results

    def _extract_weather(self, text: str) -> List[PatternMatch]:
        """気象災害パターンを抽出"""
        results = []

        # 災害種別の判定
        disaster_type = None
        if "台風" in text:
            disaster_type = "台風"
        elif "大雪" in text or "積雪" in text:
            disaster_type = "大雪"
        elif "豪雨" in text or "大雨" in text:
            disaster_type = "豪雨"
        elif "津波" in text:
            disaster_type = "津波"
        elif "暴風" in text:
            disaster_type = "暴風"

        for pattern, confidence in self.WEATHER_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                extracted_data = {
                    "full_match": match.group(0),
                    "disaster_type": disaster_type
                }

                # 台風番号
                if "台風" in pattern and match.lastindex >= 1:
                    try:
                        extracted_data["typhoon_number"] = int(match.group(1))
                    except (ValueError, TypeError):
                        pass

                # 積雪量
                if "積雪" in pattern and match.lastindex >= 1:
                    try:
                        extracted_data["snow_depth_cm"] = int(match.group(1))
                    except (ValueError, TypeError):
                        pass

                results.append(PatternMatch(
                    pattern_type="WeatherDisaster",
                    matched_text=match.group(0),
                    confidence=confidence,
                    extracted_data=extracted_data,
                    start=match.start(),
                    end=match.end()
                ))

        return results

    def _extract_evacuation(self, text: str) -> List[PatternMatch]:
        """避難パターンを抽出"""
        results = []

        for pattern, confidence in self.EVACUATION_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                extracted_data = {"full_match": match.group(0)}

                # 避難対象地域
                if "に" in pattern and match.lastindex >= 1:
                    extracted_data["evacuation_area"] = match.group(1)

                # 避難者数
                if "人" in pattern and match.lastindex >= 1:
                    try:
                        num_str = match.group(1).replace(",", "")
                        extracted_data["evacuee_count"] = int(num_str)
                    except (ValueError, TypeError):
                        pass

                results.append(PatternMatch(
                    pattern_type="EvacuationOrder",
                    matched_text=match.group(0),
                    confidence=confidence,
                    extracted_data=extracted_data,
                    start=match.start(),
                    end=match.end()
                ))

        return results

    def _extract_fire(self, text: str) -> List[PatternMatch]:
        """火災パターンを抽出"""
        results = []

        for pattern, confidence in self.FIRE_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                results.append(PatternMatch(
                    pattern_type="WeatherDisaster",
                    matched_text=match.group(0),
                    confidence=confidence,
                    extracted_data={
                        "full_match": match.group(0),
                        "disaster_type": "火災"
                    },
                    start=match.start(),
                    end=match.end()
                ))

        return results

    def _extract_damage(self, text: str) -> List[PatternMatch]:
        """被害パターンを抽出"""
        results = []

        for pattern, confidence in self.DAMAGE_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                extracted_data = {"full_match": match.group(0)}

                # 被害数
                if match.lastindex >= 1:
                    try:
                        num_str = match.group(1).replace(",", "")
                        extracted_data["count"] = int(num_str)
                    except (ValueError, TypeError):
                        pass

                # 被害種別
                if match.lastindex >= 2:
                    extracted_data["damage_type"] = match.group(2)

                results.append(PatternMatch(
                    pattern_type="DamageReport",
                    matched_text=match.group(0),
                    confidence=confidence,
                    extracted_data=extracted_data,
                    start=match.start(),
                    end=match.end()
                ))

        return results

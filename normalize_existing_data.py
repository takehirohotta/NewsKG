#!/usr/bin/env python3
"""
既存のRDFデータからエンティティを抽出し、LLMで正規化するスクリプト

処理フロー:
1. RDFファイルを読み込み
2. 各エンティティタイプ（person, organization, place）ごとにラベルを抽出
3. LLMを使用してバッチ正規化
4. 正規化マッピングをJSONとして保存
"""

import os
import re
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set
from dotenv import load_dotenv
from extractors.entity_normalizer import EntityBatchNormalizer

load_dotenv()

# RDFファイルパス
RDF_FILE = Path("output/knowledge_graph_v2.ttl")
OUTPUT_MAPPING_FILE = Path("output/entity_normalization_mapping.json")

# エンティティタイプのプレフィックス
ENTITY_TYPES = {
    'person': 'newskg:person_',
    'organization': 'newskg:organization_',
    'place': 'newskg:place_'
}

def extract_entities_from_rdf(rdf_file: Path) -> Dict[str, Set[str]]:
    """
    RDFファイルから各タイプのエンティティラベルを抽出
    
    Args:
        rdf_file: RDFファイルパス
        
    Returns:
        {entity_type: set(labels)} の辞書
    """
    entities = {etype: set() for etype in ENTITY_TYPES.keys()}
    
    # エンティティ定義行のパターン: newskg:person_xxxxx a newskg:Person ;
    entity_pattern = re.compile(r'newskg:(person|organization|place)_\w+ a newskg:(Person|Organization|Place) ;')
    # ラベル行のパターン: newskg:hasLabel "ラベル名"@ja ;
    label_pattern = re.compile(r'newskg:hasLabel "([^"]+)"@ja ;')
    
    print(f"RDFファイルを読み込み中: {rdf_file}")
    with open(rdf_file, 'r', encoding='utf-8') as f:
        current_entity_type = None
        
        for line in f:
            line = line.strip()
            
            # エンティティ定義行を検出
            entity_match = entity_pattern.search(line)
            if entity_match:
                current_entity_type = entity_match.group(1)  # person, organization, place
                continue
            
            # ラベル行を検出
            if current_entity_type and 'newskg:hasLabel' in line:
                label_match = label_pattern.search(line)
                if label_match:
                    label = label_match.group(1)
                    entities[current_entity_type].add(label)
                    current_entity_type = None  # リセット
    
    # 統計情報を表示
    print("\n抽出結果:")
    for etype, labels in entities.items():
        print(f"  {etype}: {len(labels)} 件")
    
    return entities

def normalize_entities(entities: Dict[str, Set[str]], batch_size: int = 50) -> Dict[str, Dict[str, str]]:
    """
    各エンティティタイプについてLLMで正規化マッピングを作成
    
    Args:
        entities: {entity_type: set(labels)}
        batch_size: バッチサイズ
        
    Returns:
        {entity_type: {original_label: normalized_label}}
    """
    normalizer = EntityBatchNormalizer()
    
    all_mappings = {}
    
    for entity_type, labels in entities.items():
        if not labels:
            print(f"\n{entity_type}: スキップ（エンティティなし）")
            continue
        
        print(f"\n{entity_type} を正規化中... ({len(labels)} 件)")
        
        # セットをリストに変換
        labels_list = sorted(list(labels))
        
        # 正規化
        mapping = normalizer.normalize_entities(
            entities=labels_list,
            entity_type=entity_type
        )
        
        all_mappings[entity_type] = mapping
        
        # 変更があったエンティティのみ表示
        changes = {k: v for k, v in mapping.items() if k != v}
        if changes:
            print(f"  正規化された項目数: {len(changes)}")
            # サンプル表示（最大10件）
            for i, (orig, norm) in enumerate(list(changes.items())[:10]):
                print(f"    {orig} → {norm}")
            if len(changes) > 10:
                print(f"    ... 他 {len(changes) - 10} 件")
        else:
            print(f"  正規化不要（すべて一意）")
    
    return all_mappings

def save_mapping(mapping: Dict[str, Dict[str, str]], output_file: Path):
    """
    正規化マッピングをJSONファイルとして保存
    
    Args:
        mapping: {entity_type: {original: normalized}}
        output_file: 出力ファイルパス
    """
    # 統計情報を追加
    stats = {}
    for entity_type, type_mapping in mapping.items():
        changes = {k: v for k, v in type_mapping.items() if k != v}
        stats[entity_type] = {
            'total': len(type_mapping),
            'normalized': len(changes),
            'unchanged': len(type_mapping) - len(changes)
        }
    
    output_data = {
        'mapping': mapping,
        'statistics': stats
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n正規化マッピングを保存: {output_file}")
    print("\n統計:")
    for entity_type, stat in stats.items():
        print(f"  {entity_type}:")
        print(f"    総数: {stat['total']}")
        print(f"    正規化: {stat['normalized']}")
        print(f"    変更なし: {stat['unchanged']}")

def main():
    """メイン処理"""
    print("=" * 60)
    print("エンティティ正規化スクリプト")
    print("=" * 60)
    
    # 1. RDFからエンティティを抽出
    entities = extract_entities_from_rdf(RDF_FILE)
    
    # 2. LLMで正規化
    mapping = normalize_entities(entities, batch_size=50)
    
    # 3. マッピングを保存
    save_mapping(mapping, OUTPUT_MAPPING_FILE)
    
    print("\n✓ 正規化処理が完了しました")
    print(f"次のステップ: apply_normalization.py で正規化を適用")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
述語マスター辞書の重複を統合するスクリプト
"""

import json
from pathlib import Path
from collections import defaultdict

PREDICATE_MASTER = Path("dictionaries/predicates/predicate_master.json")

MERGE_RULES = {
    "訪問": "visit",
    "発表": "announce",
    "開催": "hold_at",
    "攻撃": "attack",
    "協議": "meet",
}

def merge_duplicates(master_file: Path, merge_rules: dict):
    """重複述語をマージ"""
    with open(master_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    predicates = {p['id']: p for p in data['predicates']}
    
    merged_count = 0
    for source_id, target_id in merge_rules.items():
        if source_id not in predicates:
            print(f"  スキップ: {source_id} が見つかりません")
            continue
        
        if target_id not in predicates:
            print(f"  スキップ: {target_id} が見つかりません")
            continue
        
        source = predicates[source_id]
        target = predicates[target_id]
        
        target['aliases'].extend(source['aliases'])
        target['aliases'].append(source_id)
        target['aliases'] = list(set(target['aliases']))
        
        del predicates[source_id]
        merged_count += 1
        
        print(f"  {source_id} → {target_id} (エイリアス {len(source['aliases'])} 件を統合)")
    
    data['predicates'] = list(predicates.values())
    
    with open(master_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ {merged_count} 件の述語を統合しました")
    print(f"  総述語数: {len(data['predicates'])}")

def main():
    print("=" * 60)
    print("述語マスター統合スクリプト")
    print("=" * 60)
    
    merge_duplicates(PREDICATE_MASTER, MERGE_RULES)

if __name__ == "__main__":
    main()

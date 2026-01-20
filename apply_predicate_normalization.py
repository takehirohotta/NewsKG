#!/usr/bin/env python3
"""
既存RDFファイルの述語を正規化されたものに置き換えるスクリプト
"""

import re
import json
from pathlib import Path
from typing import Dict

INPUT_RDF = Path("output/knowledge_graph_v2.ttl")
OUTPUT_RDF = Path("output/knowledge_graph_v2_normalized.ttl")
PREDICATE_MASTER = Path("dictionaries/predicates/predicate_master.json")

def load_predicate_mapping(master_file: Path) -> Dict[str, str]:
    """マスター辞書から述語マッピングを作成"""
    with open(master_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    mapping = {}
    for pred in data.get("predicates", []):
        pred_id = pred['id']
        
        for alias in pred.get('aliases', []):
            if alias.startswith('pred_'):
                mapping[alias] = pred_id
    
    print(f"述語マッピング読み込み: {len(mapping)} 件")
    return mapping

def replace_predicates_in_rdf(input_file: Path, output_file: Path, mapping: Dict[str, str]):
    """RDFファイルの述語を置換"""
    total_replacements = 0
    line_count = 0
    
    print(f"\nRDF処理中: {input_file}")
    
    with open(input_file, 'r', encoding='utf-8') as f_in, \
         open(output_file, 'w', encoding='utf-8') as f_out:
        
        for line in f_in:
            line_count += 1
            original_line = line
            
            if 'newskg:rel_pred_' in line:
                for old_pred, new_pred in mapping.items():
                    old_uri = f'newskg:rel_{old_pred}'
                    new_uri = f'newskg:rel_{new_pred}'
                    
                    if old_uri in line:
                        line = line.replace(old_uri, new_uri)
                        total_replacements += 1
                        
                        if total_replacements <= 10:
                            print(f"  {old_pred} → {new_pred}")
            
            f_out.write(line)
    
    print(f"\n✓ 処理完了")
    print(f"  総行数: {line_count:,}")
    print(f"  置換数: {total_replacements:,}")
    print(f"  出力: {output_file}")

def main():
    print("=" * 60)
    print("RDF述語置換スクリプト")
    print("=" * 60)
    
    if not INPUT_RDF.exists():
        print(f"エラー: {INPUT_RDF} が見つかりません")
        return
    
    if not PREDICATE_MASTER.exists():
        print(f"エラー: {PREDICATE_MASTER} が見つかりません")
        print("先に normalize_predicates.py を実行してください")
        return
    
    mapping = load_predicate_mapping(PREDICATE_MASTER)
    
    replace_predicates_in_rdf(INPUT_RDF, OUTPUT_RDF, mapping)
    
    print(f"\n次のステップ:")
    print(f"  uv run python upload_to_fuseki.py")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
正規化マッピングを既存のRDFデータに適用するスクリプト

処理フロー:
1. 正規化マッピングJSON読み込み
2. RDFファイルを読み込み
3. エンティティラベルを正規化版に置換
4. 新しいRDFファイルとして保存
"""

import re
import json
from pathlib import Path
from typing import Dict

INPUT_RDF_FILE = Path("output/knowledge_graph_v2.ttl")
MAPPING_FILE = Path("output/entity_normalization_mapping.json")
OUTPUT_RDF_FILE = Path("output/knowledge_graph_v2_normalized.ttl")

def load_mapping(mapping_file: Path) -> Dict[str, Dict[str, str]]:
    """正規化マッピングをロード"""
    with open(mapping_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['mapping']

def apply_normalization_to_rdf(input_file: Path, output_file: Path, mapping: Dict[str, Dict[str, str]]):
    """
    RDFファイルにエンティティ正規化を適用
    
    Args:
        input_file: 入力RDFファイル
        output_file: 出力RDFファイル
        mapping: {entity_type: {original: normalized}}
    """
    all_mappings = {}
    for entity_type, type_mapping in mapping.items():
        all_mappings.update(type_mapping)
    
    total_replacements = 0
    
    print(f"RDFファイルを読み込み中: {input_file}")
    
    with open(input_file, 'r', encoding='utf-8') as f_in, \
         open(output_file, 'w', encoding='utf-8') as f_out:
        
        for line_num, line in enumerate(f_in, 1):
            original_line = line
            
            if 'newskg:hasLabel' in line:
                for original_label, normalized_label in all_mappings.items():
                    if original_label == normalized_label:
                        continue
                    
                    pattern = re.compile(r'newskg:hasLabel\s+"' + re.escape(original_label) + r'"@ja')
                    if pattern.search(line):
                        line = pattern.sub(f'newskg:hasLabel "{normalized_label}"@ja', line)
                        total_replacements += 1
                        
                        if total_replacements <= 10:
                            print(f"  行{line_num}: {original_label} → {normalized_label}")
            
            f_out.write(line)
    
    print(f"\n✓ 正規化完了")
    print(f"  総置換数: {total_replacements}")
    print(f"  出力ファイル: {output_file}")

def main():
    print("=" * 60)
    print("RDF正規化適用スクリプト")
    print("=" * 60)
    
    mapping = load_mapping(MAPPING_FILE)
    
    print(f"\n正規化マッピング読み込み完了:")
    for entity_type, type_mapping in mapping.items():
        changes = {k: v for k, v in type_mapping.items() if k != v}
        print(f"  {entity_type}: {len(changes)} 件の正規化")
    
    print()
    apply_normalization_to_rdf(INPUT_RDF_FILE, OUTPUT_RDF_FILE, mapping)
    
    print(f"\n次のステップ:")
    print(f"  1. Fusekiにアップロード:")
    print(f"     uv run python upload_to_fuseki.py")

if __name__ == "__main__":
    main()

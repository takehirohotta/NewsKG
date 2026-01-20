#!/usr/bin/env python3
"""
RDFから未正規化述語を抽出し、LLMで正規化してマスター辞書を更新するスクリプト
"""

import os
import re
import json
from pathlib import Path
from collections import Counter
from typing import Dict, List, Set
from dotenv import load_dotenv
from extractors.llm_client import get_client

load_dotenv()

RDF_FILE = Path("output/knowledge_graph_v2.ttl")
PREDICATE_MASTER_FILE = Path("dictionaries/predicates/predicate_master.json")

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
      "category": "position/action/event/diplomacy/crime/business/disaster/other"
    }
  ]
}

## ルール
1. 同じ意味の述語は1つのグループにまとめる
2. 代表形は最も一般的で簡潔な表現を選ぶ
3. 「する」は省略する（例: 「発表する」→「発表」）
4. 出現回数が多いものを優先的に代表形にする
5. 英語のIDは日本語の意味を表す動詞形にする（例: announce → 発表）"""

def extract_predicates_from_rdf(rdf_file: Path) -> Counter:
    """RDFファイルから述語とその出現回数を抽出"""
    print(f"RDFファイルを読み込み中: {rdf_file}")
    
    predicates = Counter()
    pred_pattern = re.compile(r'rdf:predicate\s+(newskg:rel_\w+)\s+[;.]')
    
    with open(rdf_file, 'r', encoding='utf-8') as f:
        for line in f:
            match = pred_pattern.search(line)
            if match:
                pred_uri = match.group(1)
                pred_name = pred_uri.replace('newskg:rel_', '')
                predicates[pred_name] += 1
    
    print(f"抽出完了: {len(predicates)} 種類の述語")
    return predicates

def load_existing_master(master_file: Path) -> Dict:
    """既存のマスター辞書を読み込み"""
    if not master_file.exists():
        return {"predicates": []}
    
    with open(master_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_normalized_predicates(master_data: Dict) -> Set[str]:
    """既に正規化済みの述語IDセットを取得"""
    normalized = set()
    for pred in master_data.get("predicates", []):
        normalized.add(pred['id'])
        normalized.update(pred.get('aliases', []))
    return normalized

def normalize_predicates_with_llm(predicates: List[str], counts: Counter, batch_size: int = 100) -> List[Dict]:
    """LLMを使って述語を正規化"""
    client = get_client()
    all_groups = []
    
    total_batches = (len(predicates) + batch_size - 1) // batch_size
    
    for i in range(0, len(predicates), batch_size):
        batch = predicates[i:i+batch_size]
        batch_num = i // batch_size + 1
        
        print(f"\nバッチ {batch_num}/{total_batches} を処理中... ({len(batch)} 述語)")
        
        pred_list = [f"- {p} ({counts[p]}回)" for p in batch]
        
        user_prompt = f"""以下の述語リストを正規化してください。括弧内は出現回数です。

{chr(10).join(pred_list)}

JSON形式で出力してください。"""
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = client.chat_json(messages, temperature=0.1)
            groups = response.get("groups", [])
            all_groups.extend(groups)
            print(f"  → {len(groups)} グループに正規化")
        except Exception as e:
            print(f"  エラー: {e}")
            for pred in batch:
                all_groups.append({
                    "canonical": pred,
                    "members": [pred],
                    "category": "other"
                })
    
    return all_groups

def update_master_dictionary(master_file: Path, new_groups: List[Dict]):
    """マスター辞書に新しい述語グループを追加"""
    master_data = load_existing_master(master_file)
    
    existing_ids = {p['id'] for p in master_data.get("predicates", [])}
    
    added_count = 0
    for group in new_groups:
        canonical = group.get("canonical", "")
        members = group.get("members", [])
        category = group.get("category", "other")
        
        if not canonical:
            continue
        
        pred_id = canonical.replace(" ", "_").replace("・", "_").lower()
        
        if pred_id in existing_ids:
            continue
        
        master_data.setdefault("predicates", []).append({
            "id": pred_id,
            "label": canonical,
            "aliases": [m for m in members if m != canonical],
            "category": category
        })
        
        existing_ids.add(pred_id)
        added_count += 1
    
    master_file.parent.mkdir(parents=True, exist_ok=True)
    with open(master_file, 'w', encoding='utf-8') as f:
        json.dump(master_data, f, ensure_ascii=False, indent=2)
    
    print(f"\nマスター辞書を更新: {added_count} 件追加")
    print(f"保存先: {master_file}")

def main():
    print("=" * 60)
    print("述語正規化スクリプト")
    print("=" * 60)
    
    if not RDF_FILE.exists():
        print(f"エラー: {RDF_FILE} が見つかりません")
        return
    
    predicates = extract_predicates_from_rdf(RDF_FILE)
    
    master_data = load_existing_master(PREDICATE_MASTER_FILE)
    normalized = get_normalized_predicates(master_data)
    
    unknown_predicates = [p for p in predicates.keys() if p not in normalized]
    
    print(f"\n統計:")
    print(f"  総述語数: {len(predicates)}")
    print(f"  既に正規化済み: {len(predicates) - len(unknown_predicates)}")
    print(f"  未正規化: {len(unknown_predicates)}")
    
    if not unknown_predicates:
        print("\n✓ すべての述語が正規化済みです")
        return
    
    print(f"\n未正規化述語の上位20件:")
    unknown_with_counts = [(p, predicates[p]) for p in unknown_predicates]
    unknown_with_counts.sort(key=lambda x: x[1], reverse=True)
    for pred, count in unknown_with_counts[:20]:
        print(f"  {pred}: {count}回")
    
    print(f"\nLLMで正規化を開始...")
    new_groups = normalize_predicates_with_llm(unknown_predicates, predicates, batch_size=80)
    
    update_master_dictionary(PREDICATE_MASTER_FILE, new_groups)
    
    print("\n✓ 述語正規化が完了しました")
    print(f"次のステップ: uv run python test_triple_extraction.py --pipeline --max-articles 490")

if __name__ == "__main__":
    main()

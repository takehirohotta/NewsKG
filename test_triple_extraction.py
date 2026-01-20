#!/usr/bin/env python3
"""
トリプル抽出のテストスクリプト

使用方法:
    uv run python test_triple_extraction.py
    uv run python test_triple_extraction.py --max-articles 5
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from extractors.llm_extractor import LLMTripleExtractor
from pipeline.processor_v2 import TriplePipelineProcessor


def test_single_article():
    """単一記事でのテスト"""
    print("=" * 60)
    print("単一記事テスト")
    print("=" * 60)
    
    # テスト用の記事
    test_article = {
        "id": "test_001",
        "title": "高市首相 トランプ大統領と電話会談 日米同盟の強化を確認",
        "content": "高市早苗首相は15日、アメリカのトランプ大統領と電話で会談しました。両首脳は日米同盟の一層の強化を確認し、北朝鮮問題や経済協力について意見を交わしました。",
        "summary": "高市首相がトランプ大統領と電話会談を行い、日米同盟強化を確認。"
    }
    
    extractor = LLMTripleExtractor()
    result = extractor.extract_from_article(test_article)
    
    print(f"\n記事: {test_article['title']}")
    print(f"抽出されたトリプル数: {len(result.triples)}")
    print("-" * 40)
    
    for i, triple in enumerate(result.triples, 1):
        print(f"\n[トリプル {i}]")
        print(f"  主語: {triple.subject} ({triple.subject_type})")
        print(f"  述語: {triple.predicate}")
        print(f"  目的語: {triple.object} ({triple.object_type})")
        print(f"  信頼度: {triple.confidence}")
    
    return result


def test_pipeline(max_articles: int = 3, reasoning: bool = True):
    """パイプライン全体のテスト"""
    mode = "reasoning有効" if reasoning else "reasoning無効"
    print("\n" + "=" * 60)
    print(f"パイプラインテスト（最大{max_articles}記事 / {mode}）")
    print("=" * 60)
    
    input_path = Path(__file__).parent / "articles.json"
    output_dir = Path(__file__).parent / "output"
    
    if not input_path.exists():
        print(f"エラー: {input_path} が見つかりません")
        return None
    
    processor = TriplePipelineProcessor(reasoning=reasoning)
    result = processor.run(
        input_path=str(input_path),
        output_dir=str(output_dir),
        verbose=True,
        max_articles=max_articles
    )
    
    print("\n" + "-" * 40)
    print("パイプライン結果:")
    print(f"  成功: {result['success']}")
    print(f"  処理時間: {result['elapsed_seconds']:.2f}秒")
    print(f"  総トリプル数: {result['stats']['total_triples']}")
    print(f"  出力ファイル: {result['output_files']['rdf_latest']}")
    
    return result


def main():
    parser = argparse.ArgumentParser(description='トリプル抽出テスト')
    parser.add_argument('--max-articles', type=int, default=3,
                        help='処理する最大記事数 (default: 3)')
    parser.add_argument('--single', action='store_true',
                        help='単一記事テストのみ実行')
    parser.add_argument('--pipeline', action='store_true',
                        help='パイプラインテストのみ実行')
    parser.add_argument('--no-reasoning', action='store_true',
                        help='reasoningを無効化')
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s: %(message)s'
    )
    
    reasoning = not args.no_reasoning
    
    try:
        if args.single or (not args.single and not args.pipeline):
            test_single_article()
        
        if args.pipeline or (not args.single and not args.pipeline):
            test_pipeline(args.max_articles, reasoning=reasoning)
            
        print("\n✓ テスト完了")
        
    except Exception as e:
        print(f"\n✗ エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

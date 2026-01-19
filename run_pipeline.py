#!/usr/bin/env python3
"""
NewsKG パイプライン実行スクリプト

ニュース記事からStatementを抽出し、RDFとして保存します。

使用方法:
    uv run python run_pipeline.py --input articles.json --output output/
    uv run python run_pipeline.py  # デフォルト設定で実行
"""

import argparse
import sys
import logging
from pathlib import Path

from pipeline import PipelineProcessor


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="NewsKG: ニュース記事から知識グラフを生成",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
    # 基本的な使用方法
    uv run run_pipeline.py

    # 入出力を指定
    uv run run_pipeline.py --input articles.json --output output/

    # 詳細出力モード
    uv run run_pipeline.py -v

    # SHACL検証をスキップ
    uv run run_pipeline.py --no-validate
        """
    )

    parser.add_argument(
        "--input", "-i",
        default="articles.json",
        help="入力JSONファイル (デフォルト: articles.json)"
    )
    parser.add_argument(
        "--output", "-o",
        default="output",
        help="出力ディレクトリ (デフォルト: output/)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="詳細出力モード"
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="SHACL検証をスキップ"
    )

    args = parser.parse_args()

    # 入力ファイルの存在確認
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"エラー: 入力ファイルが見つかりません: {args.input}")
        print("先に 'uv run python fetch_rss.py' を実行してください。")
        sys.exit(1)

    # ロギング設定
    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    print("=" * 60)
    print("NewsKG パイプライン")
    print("=" * 60)
    print(f"入力: {args.input}")
    print(f"出力: {args.output}/")
    print(f"SHACL検証: {'無効' if args.no_validate else '有効'}")
    print("-" * 60)

    # パイプライン実行
    processor = PipelineProcessor(validate=not args.no_validate)

    try:
        result = processor.run(
            input_path=str(args.input),
            output_dir=args.output,
            verbose=args.verbose
        )
    except Exception as e:
        print(f"エラー: パイプライン実行中にエラーが発生しました")
        print(f"  {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    # 結果表示
    print("\n" + "=" * 60)
    print("実行結果")
    print("=" * 60)

    stats = result["stats"]
    print(f"処理時間: {result['elapsed_seconds']:.2f}秒")
    print(f"\n記事統計:")
    print(f"  総記事数: {stats['total_articles']}")
    print(f"  Statement抽出記事: {stats['articles_with_statements']}")

    print(f"\nエンティティ統計 (総数: {stats['total_entities']}):")
    for etype, count in stats["entity_types"].items():
        print(f"  {etype}: {count}")

    print(f"\nStatement統計 (総数: {stats['total_statements']}):")
    for stype, count in sorted(stats["statement_types"].items(), key=lambda x: -x[1]):
        print(f"  {stype}: {count}")

    print(f"\n出力ファイル:")
    for key, path in result["output_files"].items():
        print(f"  {key}: {path}")

    print(f"\nSHACL検証結果:")
    validation = result["validation"]
    if validation["conforms"]:
        print("  ✓ データは全ての制約に適合しています")
    else:
        print("  ✗ 検証エラーがあります")
        print(validation["message"][:500])

    print("\n" + "=" * 60)
    print("完了")
    print("=" * 60)


if __name__ == "__main__":
    main()

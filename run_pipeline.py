#!/usr/bin/env python3
"""
NewsKG パイプライン実行スクリプト

ニュース記事からStatementを抽出し、RDFとして保存します。

使用方法:
    uv run python run_pipeline.py --input articles.json --output output/
    uv run python run_pipeline.py  # デフォルト設定で実行
    uv run python run_pipeline.py --upload  # Fusekiにアップロード
"""

import argparse
import sys
import logging
from pathlib import Path

import config
from pipeline import PipelineProcessor, FusekiUploader


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
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Fusekiサーバーにアップロード"
    )
    parser.add_argument(
        "--fuseki-endpoint",
        default=config.FUSEKI_ENDPOINT,
        help=f"Fusekiサーバーのエンドポイント (デフォルト: {config.FUSEKI_ENDPOINT})"
    )
    parser.add_argument(
        "--fuseki-dataset",
        default=config.FUSEKI_DATASET,
        help=f"Fusekiデータセット名 (デフォルト: {config.FUSEKI_DATASET})"
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Fusekiの既存データを置換（デフォルトは追加）"
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
    print(f"Fusekiアップロード: {'有効' if args.upload else '無効'}")
    if args.upload:
        print(f"  エンドポイント: {args.fuseki_endpoint}")
        print(f"  データセット: {args.fuseki_dataset}")
        print(f"  モード: {'置換' if args.replace else '追加'}")
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

    # Fusekiアップロード
    if args.upload:
        print(f"\n" + "-" * 60)
        print("Fusekiアップロード")
        print("-" * 60)

        uploader = FusekiUploader(
            endpoint=args.fuseki_endpoint,
            dataset=args.fuseki_dataset
        )

        # 接続確認
        if not uploader.check_connection():
            print(f"  ✗ Fusekiサーバーに接続できません: {args.fuseki_endpoint}")
            print("    サーバーが起動しているか確認してください。")
        else:
            print(f"  ✓ Fusekiサーバーに接続しました")

            # アップロード実行
            rdf_path = result["output_files"]["rdf_latest"]
            upload_result = uploader.upload_file(
                rdf_path,
                replace=args.replace
            )

            if upload_result["success"]:
                print(f"  ✓ アップロード成功")

                # 統計情報を取得
                stats = uploader.get_statistics()
                print(f"  トリプル数: {stats['total_triples']}")

                if stats["class_counts"]:
                    print(f"  クラス別インスタンス数:")
                    for cls, count in list(stats["class_counts"].items())[:10]:
                        print(f"    {cls}: {count}")
            else:
                print(f"  ✗ アップロード失敗: {upload_result.get('error', '不明なエラー')}")

    print("\n" + "=" * 60)
    print("完了")
    print("=" * 60)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
NewsKG サーバー起動スクリプト

FastAPIバックエンドサーバーを起動します。

使用方法:
    uv run python run_server.py
    uv run python run_server.py --port 8000 --reload
"""

import argparse
import uvicorn


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="NewsKG APIサーバーを起動",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="ホストアドレス (デフォルト: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="ポート番号 (デフォルト: 8000)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="開発モード（自動リロード有効）",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("NewsKG API Server")
    print("=" * 60)
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Reload: {args.reload}")
    print("-" * 60)
    print(f"API Docs: http://localhost:{args.port}/docs")
    print(f"ReDoc: http://localhost:{args.port}/redoc")
    print("=" * 60)

    uvicorn.run(
        "backend.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()

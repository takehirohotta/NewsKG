"""
NHK RSS取得モジュールの設定ファイル

このファイルでRSSフィード、出力パス、タイムアウト設定などを管理します。
"""

# 取得対象のNHK RSSフィードURL
RSS_FEEDS = [
    "https://www.nhk.or.jp/rss/news/cat0.xml",  # 主要ニュース
    "https://www.nhk.or.jp/rss/news/cat1.xml",  # 社会
    "https://www.nhk.or.jp/rss/news/cat2.xml",  # 文化・エンタメ
    "https://www.nhk.or.jp/rss/news/cat3.xml",  # 科学・文化
    "https://www.nhk.or.jp/rss/news/cat4.xml",  # 政治
    "https://www.nhk.or.jp/rss/news/cat5.xml",  # 経済
    "https://www.nhk.or.jp/rss/news/cat6.xml",  # 国際
    "https://www.nhk.or.jp/rss/news/cat7.xml",  # スポーツ
]

# 出力ファイルパス
OUTPUT_JSON_PATH = "articles.json"

# ログファイルパス
LOG_FILE_PATH = "fetch_rss.log"

# タイムアウト設定（秒）
TIMEOUT_SECONDS = 10

# 最大リトライ回数
MAX_RETRIES = 3

# リトライ時の待機時間（秒）
RETRY_BACKOFF_BASE = 2

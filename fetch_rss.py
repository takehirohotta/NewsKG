#!/usr/bin/env python3
"""
NHK RSS取得モジュール

複数のNHK RSSフィードから記事を取得し、JSON形式で保存します。
重複排除、エラーハンドリング、ログ出力機能を備えています。
"""

import feedparser
import hashlib
import json
import logging
import time
import sys
from datetime import datetime, timezone
from dateutil import parser as date_parser
from typing import List, Dict, Tuple
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

import config


def setup_logging():
    """ログ設定を初期化"""
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(config.LOG_FILE_PATH, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )


def create_session() -> requests.Session:
    """リトライ機能付きのHTTPセッションを作成"""
    session = requests.Session()

    # User-Agentヘッダーを設定（403 Forbiddenエラー回避）
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })

    retry = Retry(
        total=config.MAX_RETRIES,
        backoff_factor=config.RETRY_BACKOFF_BASE,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def calculate_content_hash(content: str) -> str:
    """
    コンテンツのSHA256ハッシュを計算

    Args:
        content: ハッシュ化する文字列

    Returns:
        16進数のハッシュ文字列
    """
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def parse_date(date_str: str) -> Tuple[str, int]:
    """
    日付文字列をISO 8601形式とUnixタイムスタンプに変換

    Args:
        date_str: パース対象の日付文字列

    Returns:
        (ISO 8601形式の文字列, Unixタイムスタンプ)
    """
    try:
        dt = date_parser.parse(date_str)
        # タイムゾーン情報がない場合はUTCとして扱う
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            # UTCに変換
            dt = dt.astimezone(timezone.utc)

        iso_date = dt.isoformat().replace('+00:00', 'Z')
        unix_timestamp = int(dt.timestamp())
        return iso_date, unix_timestamp
    except Exception as e:
        logging.warning(f"日付パースエラー: {date_str} - {e}")
        # デフォルト値を返す
        default_dt = datetime.now(timezone.utc)
        iso_date = default_dt.isoformat().replace('+00:00', 'Z')
        unix_timestamp = int(default_dt.timestamp())
        return iso_date, unix_timestamp


def extract_article_info(entry: Dict, source_url: str) -> Dict:
    """
    RSSエントリーから記事情報を抽出

    Args:
        entry: feedparserのエントリー辞書
        source_url: RSS フィードのURL

    Returns:
        記事情報の辞書
    """
    # タイトルを取得
    title = entry.get('title', '').strip()

    # URLを取得
    url = entry.get('link', '').strip()

    # 公開日時を取得
    pub_date_str = entry.get('published', entry.get('updated', ''))
    pub_date_iso, pub_date_unix = parse_date(pub_date_str)

    # 要約を取得
    summary = entry.get('summary', '').strip()

    # 本文を取得（contentがある場合はそちらを優先）
    content = ''
    if 'content' in entry and len(entry.content) > 0:
        content = entry.content[0].get('value', '').strip()
    elif 'description' in entry:
        content = entry.get('description', '').strip()
    else:
        content = summary

    # コンテンツハッシュを計算
    content_for_hash = f"{title}{url}{content}"
    content_hash = calculate_content_hash(content_for_hash)

    # 記事IDを生成（URLベースのハッシュを使用）
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()[:8]
    article_id = f"nhk_{datetime.fromtimestamp(pub_date_unix, tz=timezone.utc).strftime('%Y%m%d')}_{url_hash}"

    return {
        'id': article_id,
        'title': title,
        'url': url,
        'pubDate': pub_date_iso,
        'pubDateUnix': pub_date_unix,
        'source': source_url,
        'summary': summary,
        'content': content,
        'contentHash': content_hash
    }


def fetch_feed(feed_url: str, session: requests.Session) -> List[Dict]:
    """
    単一のRSSフィードを取得して記事リストを返す

    Args:
        feed_url: RSSフィードのURL
        session: HTTPセッション

    Returns:
        記事情報のリスト
    """
    articles = []

    try:
        logging.info(f"Fetching {feed_url} ...")

        # ローカルファイルの場合は直接読み込み
        if feed_url.startswith('file://'):
            file_path = feed_url.replace('file://', '')
            feed = feedparser.parse(file_path)
        # ローカルパスの場合（相対パスまたは絶対パス）
        elif not feed_url.startswith('http://') and not feed_url.startswith('https://'):
            feed = feedparser.parse(feed_url)
        else:
            # RSSフィードを取得
            response = session.get(feed_url, timeout=config.TIMEOUT_SECONDS)
            response.raise_for_status()
            # フィードをパース
            feed = feedparser.parse(response.content)

        # エントリーが存在しない場合
        if not feed.entries:
            logging.warning(f"記事が見つかりませんでした: {feed_url}")
            return articles

        # 各エントリーから記事情報を抽出
        for entry in feed.entries:
            try:
                article = extract_article_info(entry, feed_url)
                articles.append(article)
            except Exception as e:
                logging.error(f"記事抽出エラー: {e}")
                continue

        logging.info(f"✓ Fetched {len(articles)} articles from {feed_url}")

    except requests.exceptions.Timeout:
        logging.error(f"タイムアウト: {feed_url}")
    except requests.exceptions.RequestException as e:
        logging.error(f"フィード取得エラー: {feed_url} - {e}")
    except Exception as e:
        logging.error(f"予期しないエラー: {feed_url} - {e}")

    return articles


def fetch_feeds(feed_urls: List[str]) -> List[Dict]:
    """
    複数のRSSフィードを取得

    Args:
        feed_urls: RSSフィードURLのリスト

    Returns:
        全記事のリスト
    """
    all_articles = []
    session = create_session()

    for feed_url in feed_urls:
        articles = fetch_feed(feed_url, session)
        all_articles.extend(articles)
        time.sleep(0.5)  # 各フィード取得の間に少し待機

    return all_articles


def remove_duplicates(articles: List[Dict]) -> Tuple[List[Dict], int]:
    """
    重複記事を排除（URLベース）

    Args:
        articles: 記事リスト

    Returns:
        (重複排除後の記事リスト, 削除された重複数)
    """
    seen_urls = set()
    unique_articles = []
    duplicates_count = 0

    for article in articles:
        url = article.get('url', '')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_articles.append(article)
        else:
            duplicates_count += 1

    return unique_articles, duplicates_count


def save_articles_json(articles: List[Dict], metadata: Dict, output_path: str):
    """
    記事データとメタデータをJSON形式で保存

    Args:
        articles: 記事リスト
        metadata: メタデータ辞書
        output_path: 出力ファイルパス
    """
    data = {
        'articles': articles,
        'metadata': metadata
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logging.info(f"記事データを保存しました: {output_path}")


def main():
    """メイン処理"""
    setup_logging()
    logging.info("Starting RSS fetch...")

    start_time = time.time()

    # RSSフィードを取得
    all_articles = fetch_feeds(config.RSS_FEEDS)

    # 重複を排除
    unique_articles, duplicates_count = remove_duplicates(all_articles)

    # 公開日時でソート（新しい順）
    unique_articles.sort(key=lambda x: x.get('pubDateUnix', 0), reverse=True)

    # ソース別の記事数をカウント
    sources_count = {}
    for article in unique_articles:
        source = article.get('source', 'unknown')
        sources_count[source] = sources_count.get(source, 0) + 1

    # 実行時間を計算
    execution_time = time.time() - start_time

    # 現在時刻（UTC、JST）
    now_utc = datetime.now(timezone.utc)
    fetch_time_iso = now_utc.isoformat().replace('+00:00', 'Z')

    # JSTに変換（UTC+9）
    from datetime import timedelta
    now_jst = now_utc + timedelta(hours=9)
    fetch_datetime_jst = now_jst.strftime('%Y-%m-%d %H:%M:%S')

    # メタデータを作成
    metadata = {
        'fetch_time': fetch_time_iso,
        'fetch_datetime_jst': fetch_datetime_jst,
        'total_articles': len(unique_articles),
        'duplicates_removed': duplicates_count,
        'sources_count': sources_count,
        'execution_time_seconds': round(execution_time, 2)
    }

    # JSON形式で保存
    save_articles_json(unique_articles, metadata, config.OUTPUT_JSON_PATH)

    # サマリーをログ出力
    logging.info("===== Summary =====")
    logging.info(f"Total articles: {len(unique_articles)}")
    logging.info(f"Total duplicates: {duplicates_count}")
    logging.info(f"Processing time: {execution_time:.2f}s")

    for source, count in sources_count.items():
        logging.info(f"  {source}: {count} articles")

    logging.info("RSS fetch completed successfully!")


if __name__ == '__main__':
    main()

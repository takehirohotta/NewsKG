# NHK RSS取得モジュール

NHKの複数のRSSフィードから記事を取得し、JSON形式で保存するPythonスクリプトです。
重複排除、エラーハンドリング、ログ出力機能を備えています。

## 特徴

- 複数のNHK RSSフィードを同時取得
- URL重複排除機能
- タイムゾーン処理（UTC統一、JST表示）
- SHA256ハッシュによる記事の一意性判定
- リトライ機能（指数バックオフ）
- 詳細なログ出力

## セットアップ

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

または、個別にインストール：

```bash
pip install feedparser==6.0.10 requests==2.31.0 python-dateutil==2.8.2
```

### 2. Python 3.7以上が必要

```bash
python3 --version
```

## 実行

### 方法1: Pythonスクリプトを直接実行

```bash
python3 fetch_rss.py
```

### 方法2: シェルスクリプトを使用

```bash
./run.sh
```

または

```bash
bash run.sh
```

## 出力ファイル

### articles.json

取得した記事情報がJSON形式で保存されます。

#### 構造

```json
{
  "articles": [
    {
      "id": "nhk_20250117_a1b2c3d4",
      "title": "記事タイトル",
      "url": "https://www3.nhk.or.jp/news/...",
      "pubDate": "2025-01-17T09:00:00Z",
      "pubDateUnix": 1737099600,
      "source": "https://www.nhk.or.jp/rss/news/cat0.xml",
      "summary": "RSS要約テキスト",
      "content": "RSS本文全文",
      "contentHash": "abc123def456..."
    }
  ],
  "metadata": {
    "fetch_time": "2025-01-17T10:30:00Z",
    "fetch_datetime_jst": "2025-01-17 19:30:00",
    "total_articles": 42,
    "duplicates_removed": 3,
    "sources_count": {
      "https://www.nhk.or.jp/rss/news/cat0.xml": 20,
      "https://www.nhk.or.jp/rss/news/cat1.xml": 15,
      "https://www.nhk.or.jp/rss/news/cat2.xml": 7
    },
    "execution_time_seconds": 12.34
  }
}
```

#### フィールド説明

- **id**: 記事の一意識別子（日付+URLハッシュ）
- **title**: 記事タイトル
- **url**: 記事へのリンク
- **pubDate**: 公開日時（ISO 8601形式、UTC）
- **pubDateUnix**: 公開日時（Unixタイムスタンプ）
- **source**: 元のRSSフィードURL
- **summary**: 記事要約
- **content**: 記事本文
- **contentHash**: コンテンツのSHA256ハッシュ

### fetch_rss.log

実行ログが記録されます。

#### ログ例

```
[2025-01-17 19:25:00] INFO: Starting RSS fetch...
[2025-01-17 19:25:01] INFO: Fetching https://www.nhk.or.jp/rss/news/cat0.xml ...
[2025-01-17 19:25:03] INFO: ✓ Fetched 20 articles from https://www.nhk.or.jp/rss/news/cat0.xml
[2025-01-17 19:25:04] INFO: Fetching https://www.nhk.or.jp/rss/news/cat1.xml ...
[2025-01-17 19:25:06] INFO: ✓ Fetched 15 articles from https://www.nhk.or.jp/rss/news/cat1.xml
...
[2025-01-17 19:25:15] INFO: ===== Summary =====
[2025-01-17 19:25:15] INFO: Total articles: 42
[2025-01-17 19:25:15] INFO: Total duplicates: 3
[2025-01-17 19:25:15] INFO: Processing time: 12.34s
[2025-01-17 19:25:15] INFO: RSS fetch completed successfully!
```

## 設定変更

`config.py` を編集することで、取得対象のRSSフィードやその他の設定を変更できます。

### RSS_FEEDS（取得対象フィード）

```python
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
```

### その他の設定

- **OUTPUT_JSON_PATH**: 出力JSONファイル名（デフォルト: `articles.json`）
- **LOG_FILE_PATH**: ログファイル名（デフォルト: `fetch_rss.log`）
- **TIMEOUT_SECONDS**: タイムアウト時間（デフォルト: 10秒）
- **MAX_RETRIES**: 最大リトライ回数（デフォルト: 3回）
- **RETRY_BACKOFF_BASE**: リトライの待機時間基数（デフォルト: 2秒）

## トラブルシューティング

### ネットワークエラー

**症状**: `ネットワーク接続エラー` や `タイムアウト` が発生

**対処法**:
1. インターネット接続を確認
2. `config.py` の `TIMEOUT_SECONDS` を増やす
3. `MAX_RETRIES` を増やす

### RSSパースエラー

**症状**: `RSSパースエラー` がログに記録される

**対処法**:
1. RSSフィードのURLが正しいか確認
2. NHKのRSSフィードが一時的に利用できない可能性があるため、時間をおいて再試行

### 文字化け

**症状**: 記事タイトルや本文が文字化けする

**対処法**:
1. Pythonのバージョンが3.7以上であることを確認
2. ターミナルのエンコーディングがUTF-8に設定されているか確認

### 記事が0件

**症状**: `Total articles: 0` と表示される

**対処法**:
1. NHKのRSSフィードURLが変更されていないか確認
2. ログファイル（`fetch_rss.log`）でエラー詳細を確認
3. 手動でRSSフィードURLにアクセスして内容を確認

### 依存関係のインストールエラー

**症状**: `pip install` が失敗する

**対処法**:
```bash
# pipをアップグレード
pip install --upgrade pip

# 仮想環境を使用
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# または
venv\Scripts\activate  # Windows

# 依存関係を再インストール
pip install -r requirements.txt
```

## 動作環境

- Python 3.7以上
- インターネット接続必須
- 必要ディスク容量: 約50MB（記事数により変動）

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 今後の展開

このモジュールは「NHK RSS → RDF知識グラフ → 可視化」プロジェクトの **Stage 1** です。

次のステージ:
- **Stage 2**: RDF変換モジュール
- **Stage 3**: 知識グラフ可視化

## 連絡先

問題が発生した場合は、プロジェクトのIssueトラッカーで報告してください。

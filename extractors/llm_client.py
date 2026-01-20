"""
OpenRouter APIクライアント

LLMを使った処理の基盤となるクライアントモジュールです。
"""

import os
import json
import httpx
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv(Path(__file__).parent.parent / ".env")


@dataclass
class LLMResponse:
    """LLMレスポンスを表すデータクラス"""
    content: str
    model: str
    usage: Dict[str, int]
    raw_response: Dict[str, Any]


class OpenRouterClient:
    """OpenRouter APIクライアント"""
    
    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 60.0
    ):
        """
        Args:
            api_key: OpenRouter APIキー。未指定の場合は環境変数から取得
            model: 使用するモデル。未指定の場合は環境変数から取得
            timeout: リクエストタイムアウト（秒）
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenRouter API key is required. "
                "Set OPENROUTER_API_KEY environment variable or pass api_key parameter."
            )
        
        self.model = model or os.getenv("OPENROUTER_MODEL", "xiaomi/mimo-v2-flash:free")
        self.timeout = timeout
        
        # HTTPヘッダー
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "http://localhost:3000"),
            "X-Title": os.getenv("OPENROUTER_SITE_NAME", "NewsKG"),
        }
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None,
        reasoning: bool = True
    ) -> LLMResponse:
        """
        チャットメッセージを送信してレスポンスを取得
        
        Args:
            messages: メッセージリスト [{"role": "user", "content": "..."}]
            temperature: 温度パラメータ (0.0-2.0)
            max_tokens: 最大トークン数
            response_format: レスポンスフォーマット指定（JSON mode等）
            reasoning: 推論モードを有効化 (MiMo-V2-Flash用、デフォルト: True)
        
        Returns:
            LLMResponse
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if reasoning:
            payload["reasoning_enabled"] = True
        
        if response_format:
            payload["response_format"] = response_format
        
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                self.BASE_URL,
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
        
        # レスポンスをパース
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        
        return LLMResponse(
            content=content,
            model=data.get("model", self.model),
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
            raw_response=data
        )
    
    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 4096,
        reasoning: bool = True
    ) -> Dict[str, Any]:
        """
        JSONレスポンスを期待するチャット
        
        Args:
            messages: メッセージリスト
            temperature: 温度パラメータ
            max_tokens: 最大トークン数
            reasoning: 推論モードを有効化 (デフォルト: True)
        
        Returns:
            パースされたJSONオブジェクト
        """
        response = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            reasoning=reasoning
        )
        
        # JSONをパース
        content = response.content.strip()
        
        # コードブロックで囲まれている場合は除去
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        
        return json.loads(content.strip())
    
    def extract_triples(self, title: str, content: str) -> List[Dict[str, str]]:
        """
        ニュース記事からトリプルを抽出（便利メソッド）
        
        Args:
            title: 記事タイトル
            content: 記事本文
        
        Returns:
            トリプルのリスト [{"subject": "...", "predicate": "...", "object": "..."}]
        """
        # このメソッドはllm_extractor.pyで実装
        raise NotImplementedError("Use LLMTripleExtractor.extract() instead")


# シングルトンインスタンス
_client: Optional[OpenRouterClient] = None


def get_client() -> OpenRouterClient:
    """シングルトンのクライアントを取得"""
    global _client
    if _client is None:
        _client = OpenRouterClient()
    return _client

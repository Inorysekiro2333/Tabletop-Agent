"""
AI Gateway Service - 统一封装 Claude/DeepSeek/MiniMax API 调用
"""
import httpx
import json
import logging
from typing import Optional, List, Dict, Any, AsyncIterator
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class AIProvider(ABC):
    """AI Provider 抽象基类"""

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        api_key: str,
        base_url: Optional[str] = None,
        **kwargs
    ) -> str:
        """发送对话请求，返回 AI 响应文本"""
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        api_key: str,
        base_url: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """流式对话请求"""
        pass


class DeepSeekProvider(AIProvider):
    """DeepSeek API Provider"""

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        api_key: str,
        base_url: Optional[str] = None,
        **kwargs
    ) -> str:
        url = (base_url or "https://api.deepseek.com") + "/chat/completions"

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": messages,
                    **kwargs
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        api_key: str,
        base_url: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        url = (base_url or "https://api.deepseek.com") + "/chat/completions"

        logger.info(f"[DeepSeek] 开始流式请求: model={model}, messages_count={len(messages)}")

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": True,
                        **kwargs
                    }
                ) as response:
                    logger.info(f"[DeepSeek] 响应状态码: {response.status_code}")

                    # 检查状态码
                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(f"[DeepSeek] 错误响应: status={response.status_code}, body={error_text}")
                        try:
                            error_json = json.loads(error_text)
                            raise Exception(f"API Error {response.status_code}: {error_json.get('error', {}).get('message', error_text)}")
                        except:
                            raise Exception(f"API Error {response.status_code}: {error_text}")

                    async for line in response.aiter_lines():
                        logger.debug(f"[DeepSeek] 收到原始line: {repr(line)}")

                        if line.startswith("data: "):
                            if line == "data: [DONE]":
                                logger.info("[DeepSeek] 收到DONE信号")
                                break
                            data = line[6:]  # Remove "data: " prefix
                            chunk = json.loads(data)
                            logger.debug(f"[DeepSeek] 解析后的chunk: {chunk}")

                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content")
                            if content:
                                logger.debug(f"[DeepSeek] yield内容: {repr(content)}")
                                yield content
                            else:
                                logger.debug(f"[DeepSeek] delta内容为空: {delta}")
                        elif line.startswith("error:"):
                            # Handle error messages from SSE
                            error_data = line[6:]
                            try:
                                error_obj = json.loads(error_data)
                                raise Exception(f"API Error: {error_obj.get('error', {}).get('message', error_data)}")
                            except:
                                raise Exception(f"SSE Error: {error_data}")
                        elif line.strip() == "":
                            # 跳过空行
                            pass
                        else:
                            logger.warning(f"[DeepSeek] 未处理的line: {repr(line)}")

        except httpx.HTTPStatusError as e:
            # 获取详细的错误信息
            error_detail = e.response.text
            logger.error(f"[DeepSeek] HTTPStatusError: {e.response.status_code}, detail={error_detail}")
            try:
                error_json = json.loads(error_detail)
                raise Exception(f"API Error {e.response.status_code}: {error_json.get('error', {}).get('message', error_detail)}")
            except:
                raise Exception(f"API Error {e.response.status_code}: {error_detail}")


class ClaudeProvider(AIProvider):
    """Claude API Provider (Anthropic)"""

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        api_key: str,
        base_url: Optional[str] = None,
        **kwargs
    ) -> str:
        url = (base_url or "https://api.anthropic.com") + "/v1/messages"

        # Convert messages format for Claude
        system_message = ""
        claude_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                claude_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }

        body = {
            "model": model,
            "messages": claude_messages,
            **kwargs
        }
        if system_message:
            body["system"] = system_message

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"]

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        api_key: str,
        base_url: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        # Claude streaming implementation
        url = (base_url or "https://api.anthropic.com") + "/v1/messages"

        system_message = ""
        claude_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                claude_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }

        body = {
            "model": model,
            "messages": claude_messages,
            "stream": True,
            **kwargs
        }
        if system_message:
            body["system"] = system_message

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, headers=headers, json=body) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        if line == "data: [DONE]":
                            break
                        data = line[6:]
                        import json
                        chunk = json.loads(data)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        if content := delta.get("content"):
                            yield content


class MiniMaxProvider(AIProvider):
    """MiniMax API Provider"""

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        api_key: str,
        base_url: Optional[str] = None,
        **kwargs
    ) -> str:
        url = (base_url or "https://api.minimax.chat") + "/v1/text/chatcompletion_v2"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                url,
                headers=headers,
                json={
                    "model": model,
                    "messages": messages,
                    **kwargs
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        api_key: str,
        base_url: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        url = (base_url or "https://api.minimax.chat") + "/v1/text/chatcompletion_v2"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                url,
                headers=headers,
                json={
                    "model": model,
                    "messages": messages,
                    "stream": True,
                    **kwargs
                }
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        if line == "data: [DONE]":
                            break
                        data = line[6:]
                        import json
                        chunk = json.loads(data)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        if content := delta.get("content"):
                            yield content


class AIGateway:
    """
    AI Gateway - 统一的 AI 调用入口
    根据 provider 类型选择对应的 Provider 实现
    """

    PROVIDERS = {
        "deepseek": DeepSeekProvider(),
        "claude": ClaudeProvider(),
        "minimax": MiniMaxProvider(),
    }

    @classmethod
    def get_provider(cls, provider_name: str) -> AIProvider:
        provider = cls.PROVIDERS.get(provider_name.lower())
        if not provider:
            raise ValueError(f"Unsupported AI provider: {provider_name}")
        return provider

    @classmethod
    async def chat(
        cls,
        provider_name: str,
        messages: List[Dict[str, str]],
        model: str,
        api_key: str,
        base_url: Optional[str] = None,
        **kwargs
    ) -> str:
        """发送对话请求"""
        provider = cls.get_provider(provider_name)
        return await provider.chat(messages, model, api_key, base_url, **kwargs)

    @classmethod
    async def chat_stream(
        cls,
        provider_name: str,
        messages: List[Dict[str, str]],
        model: str,
        api_key: str,
        base_url: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """流式对话请求"""
        provider = cls.get_provider(provider_name)
        async for chunk in provider.chat_stream(messages, model, api_key, base_url, **kwargs):
            yield chunk

"""LLM 多模型路由器 - 支持多个提供商，按任务类型智能路由"""

from __future__ import annotations

import structlog
from dataclasses import dataclass, field
from typing import AsyncIterator
from openai import AsyncOpenAI

logger = structlog.get_logger()


@dataclass
class LLMProvider:
    """LLM 提供商配置"""
    name: str
    api_key: str
    base_url: str
    models: list[str] = field(default_factory=list)
    enabled: bool = True


@dataclass
class LLMRoute:
    """LLM 路由规则"""
    provider: str
    model: str


class LLMRouter:
    """
    多模型路由器

    支持的提供商（均为 OpenAI 兼容接口）:
    - qwen:      通义千问 (DashScope)
    - deepseek:  DeepSeek
    - xiaomi:    小米大模型 (MiLM)
    - moonshot:  月之暗面 (Kimi)
    - zhipu:     智谱 (GLM)
    - openai:    OpenAI

    路由策略:
    1. 显式指定 provider:model → 直接使用
    2. 任务类型匹配路由规则 → 按规则选择
    3. 默认使用 LLM_DEFAULT_PROVIDER:LLM_DEFAULT_MODEL
    """

    def __init__(self, providers: dict[str, LLMProvider], routes: dict[str, LLMRoute],
                 default_provider: str, default_model: str):
        self.providers = providers
        self.routes = routes
        self.default_provider = default_provider
        self.default_model = default_model
        self._clients: dict[str, AsyncOpenAI] = {}

    def _get_client(self, provider_name: str) -> AsyncOpenAI:
        """获取或创建 AsyncOpenAI 客户端（带缓存）"""
        if provider_name not in self._clients:
            provider = self.providers.get(provider_name)
            if not provider or not provider.enabled:
                raise ValueError(f"Provider '{provider_name}' not found or disabled")
            self._clients[provider_name] = AsyncOpenAI(
                api_key=provider.api_key,
                base_url=provider.base_url,
            )
        return self._clients[provider_name]

    def resolve(self, task_type: str | None = None,
                provider: str | None = None, model: str | None = None) -> tuple[str, str, str]:
        """
        解析最终使用的 provider + model

        优先级: 显式指定 > 路由规则 > 默认配置

        Returns:
            (provider_name, model_name, client_key)
        """
        # 1. 显式指定
        if provider and model:
            return provider, model, f"{provider}:{model}"

        # 2. 路由规则
        if task_type and task_type in self.routes:
            route = self.routes[task_type]
            return route.provider, route.model, f"{route.provider}:{route.model}"

        # 3. 默认
        return self.default_provider, self.default_model, f"{self.default_provider}:{self.default_model}"

    async def chat(
        self,
        messages: list[dict],
        task_type: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        response_format: dict | None = None,
        max_retries: int = 2,
    ) -> str:
        """
        发送聊天请求，自动路由到合适的提供商

        Args:
            messages: 对话消息
            task_type: 任务类型（用于路由，如 reasoning/code/chat/simple）
            provider: 显式指定提供商
            model: 显式指定模型
            temperature: 温度参数
            response_format: 响应格式（如 {"type": "json_object"}）
            max_retries: 失败后重试次数（降级到其他提供商）
        """
        prov_name, model_name, _ = self.resolve(task_type, provider, model)

        # 尝试顺序: 首选提供商 → 降级到其他启用的提供商
        tried = set()
        attempt_providers = [prov_name] + [
            p for p in self.providers if p != prov_name and self.providers[p].enabled
        ]

        for attempt_provider in attempt_providers[:max_retries + 1]:
            if attempt_provider in tried:
                continue
            tried.add(attempt_provider)

            # 如果降级到其他提供商，使用该提供商的第一个模型
            attempt_model = model_name if attempt_provider == prov_name else (
                self.providers[attempt_provider].models[0]
                if self.providers[attempt_provider].models
                else model_name
            )

            try:
                client = self._get_client(attempt_provider)
                kwargs = {
                    "model": attempt_model,
                    "messages": messages,
                    "temperature": temperature,
                }
                if response_format:
                    kwargs["response_format"] = response_format

                response = await client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content or ""

                if attempt_provider != prov_name:
                    logger.warning(
                        "llm_fallback_used",
                        original=f"{prov_name}:{model_name}",
                        fallback=f"{attempt_provider}:{attempt_model}",
                    )

                return content

            except Exception as e:
                logger.error(
                    "llm_call_failed",
                    provider=attempt_provider,
                    model=attempt_model,
                    error=str(e),
                )
                continue

        raise RuntimeError(f"所有 LLM 提供商均调用失败 (tried: {list(tried)})")

    async def stream_chat(
        self,
        messages: list[dict],
        task_type: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """
        流式聊天 - 逐 token 返回内容

        与 chat() 相同的路由逻辑，但返回 AsyncIterator[str] 而非完整字符串。
        仅尝试首选提供商（不降级，避免流式中断）。
        """
        prov_name, model_name, _ = self.resolve(task_type, provider, model)
        client = self._get_client(prov_name)

        try:
            stream = await client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temperature,
                stream=True,
            )
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content
        except Exception as e:
            logger.error("stream_chat_failed", provider=prov_name, model=model_name, error=str(e))
            yield f"\n[流式输出错误: {e}]"

    async def chat_json(
        self,
        messages: list[dict],
        task_type: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.3,
    ) -> dict:
        """发送聊天请求并返回 JSON 结果"""
        import json
        text = await self.chat(
            messages=messages,
            task_type=task_type,
            provider=provider,
            model=model,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.error("json_parse_failed", response=text[:200])
            return {"error": "Failed to parse response", "raw": text}

    def list_providers(self) -> list[dict]:
        """列出所有提供商及其可用模型"""
        return [
            {
                "name": p.name,
                "models": p.models,
                "enabled": p.enabled,
                "base_url": p.base_url,
            }
            for p in self.providers.values()
        ]

    def list_routes(self) -> dict[str, str]:
        """列出所有路由规则"""
        return {
            task_type: f"{route.provider}:{route.model}"
            for task_type, route in self.routes.items()
        }


def _is_placeholder_key(api_key: str) -> bool:
    """检测 API Key 是否为占位符（未填写的真实密钥）"""
    _PLACEHOLDER_PATTERNS = (
        "your-", "xxx", "placeholder", "sk-xxx", "replace",
    )
    key_lower = api_key.strip().lower()
    return any(pat in key_lower for pat in _PLACEHOLDER_PATTERNS)


def build_router_from_settings(settings) -> LLMRouter:
    """从 Settings 构建 LLMRouter 实例"""

    # 提供商配置表: name → (env_prefix, default_base_url)
    PROVIDER_DEFS = {
        "qwen":     ("QWEN",     "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        "deepseek": ("DEEPSEEK", "https://api.deepseek.com/v1"),
        "xiaomi":   ("XIAOMI",   "https://token-plan-cn.xiaomimimo.com/v1"),
        "moonshot": ("MOONSHOT", "https://api.moonshot.cn/v1"),
        "zhipu":    ("ZHIPU",    "https://open.bigmodel.cn/api/paas/v4"),
        "openai":   ("OPENAI",   "https://api.openai.com/v1"),
    }

    # 解析启用的提供商
    provider_names = [
        p.strip() for p in settings.LLM_PROVIDERS.split(",") if p.strip()
    ]

    providers: dict[str, LLMProvider] = {}
    for name in provider_names:
        if name not in PROVIDER_DEFS:
            logger.warning("unknown_provider", name=name)
            continue

        prefix, default_url = PROVIDER_DEFS[name]
        api_key = getattr(settings, f"{prefix}_API_KEY", "")
        base_url = getattr(settings, f"{prefix}_BASE_URL", default_url)
        models_str = getattr(settings, f"{prefix}_MODELS", "")
        models = [m.strip() for m in models_str.split(",") if m.strip()]

        is_placeholder = bool(api_key) and _is_placeholder_key(api_key)
        providers[name] = LLMProvider(
            name=name,
            api_key=api_key,
            base_url=base_url,
            models=models,
            enabled=bool(api_key) and not is_placeholder,
        )

        if not api_key:
            logger.warning("provider_no_api_key", name=name, prefix=prefix)
        elif is_placeholder:
            logger.warning("provider_placeholder_key", name=name, prefix=prefix)

    # 解析路由规则
    routes: dict[str, LLMRoute] = {}
    route_fields = {
        "reasoning": settings.LLM_ROUTE_REASONING,
        "code":      settings.LLM_ROUTE_CODE,
        "chat":      settings.LLM_ROUTE_CHAT,
        "simple":    settings.LLM_ROUTE_SIMPLE,
    }
    for task_type, route_str in route_fields.items():
        if route_str and ":" in route_str:
            prov, mod = route_str.split(":", 1)
            prov, mod = prov.strip(), mod.strip()
            if prov in providers:
                routes[task_type] = LLMRoute(provider=prov, model=mod)

    default_provider = settings.LLM_DEFAULT_PROVIDER
    default_model = settings.LLM_DEFAULT_MODEL

    # 如果默认提供商未启用，降级到第一个启用的
    if default_provider not in providers or not providers[default_provider].enabled:
        for name, prov in providers.items():
            if prov.enabled and prov.models:
                logger.warning(
                    "default_provider_fallback",
                    original=default_provider,
                    fallback=name,
                )
                default_provider = name
                default_model = prov.models[0]
                break

    router = LLMRouter(
        providers=providers,
        routes=routes,
        default_provider=default_provider,
        default_model=default_model,
    )

    logger.info(
        "llm_router_initialized",
        providers=[n for n, p in providers.items() if p.enabled],
        default=f"{default_provider}:{default_model}",
        routes=list(routes.keys()),
    )

    return router

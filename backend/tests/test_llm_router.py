"""LLM 路由器单元测试"""

import pytest
from app.core.llm_router import LLMProvider, LLMRoute, LLMRouter


def make_router() -> LLMRouter:
    """创建测试用路由器"""
    providers = {
        "qwen": LLMProvider(
            name="qwen",
            api_key="test-key",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            models=["qwen-plus", "qwen-turbo"],
            enabled=True,
        ),
        "deepseek": LLMProvider(
            name="deepseek",
            api_key="test-key",
            base_url="https://api.deepseek.com/v1",
            models=["deepseek-chat", "deepseek-coder"],
            enabled=True,
        ),
        "xiaomi": LLMProvider(
            name="xiaomi",
            api_key="test-key",
            base_url="https://api.xiaomimimo.com/v1",
            models=["MiLM-v2-pro"],
            enabled=True,
        ),
        "disabled": LLMProvider(
            name="disabled",
            api_key="",
            base_url="https://example.com/v1",
            models=["model-1"],
            enabled=False,
        ),
    }
    routes = {
        "reasoning": LLMRoute(provider="deepseek", model="deepseek-chat"),
        "code": LLMRoute(provider="deepseek", model="deepseek-coder"),
        "chat": LLMRoute(provider="qwen", model="qwen-turbo"),
    }
    return LLMRouter(
        providers=providers,
        routes=routes,
        default_provider="qwen",
        default_model="qwen-plus",
    )


class TestLLMRouter:
    """LLM 路由器测试"""

    def test_resolve_explicit(self):
        router = make_router()
        prov, model, key = router.resolve(provider="xiaomi", model="MiLM-v2-pro")
        assert prov == "xiaomi"
        assert model == "MiLM-v2-pro"

    def test_resolve_by_task_type(self):
        router = make_router()
        prov, model, _ = router.resolve(task_type="code")
        assert prov == "deepseek"
        assert model == "deepseek-coder"

    def test_resolve_default(self):
        router = make_router()
        prov, model, _ = router.resolve()
        assert prov == "qwen"
        assert model == "qwen-plus"

    def test_resolve_explicit_overrides_task_type(self):
        router = make_router()
        prov, model, _ = router.resolve(
            task_type="code", provider="qwen", model="qwen-plus"
        )
        assert prov == "qwen"
        assert model == "qwen-plus"

    def test_resolve_unknown_task_type_uses_default(self):
        router = make_router()
        prov, model, _ = router.resolve(task_type="unknown_type")
        assert prov == "qwen"
        assert model == "qwen-plus"

    def test_list_providers(self):
        router = make_router()
        providers = router.list_providers()
        names = [p["name"] for p in providers]
        assert "qwen" in names
        assert "deepseek" in names
        assert "xiaomi" in names
        assert "disabled" in names
        # disabled provider should show enabled=False
        disabled = [p for p in providers if p["name"] == "disabled"][0]
        assert disabled["enabled"] is False

    def test_list_routes(self):
        router = make_router()
        routes = router.list_routes()
        assert routes["reasoning"] == "deepseek:deepseek-chat"
        assert routes["code"] == "deepseek:deepseek-coder"
        assert routes["chat"] == "qwen:qwen-turbo"

    def test_get_client_caching(self):
        router = make_router()
        c1 = router._get_client("qwen")
        c2 = router._get_client("qwen")
        assert c1 is c2  # 同一个客户端实例

    def test_get_client_disabled_provider_raises(self):
        router = make_router()
        with pytest.raises(ValueError, match="not found or disabled"):
            router._get_client("disabled")

    def test_get_client_unknown_provider_raises(self):
        router = make_router()
        with pytest.raises(ValueError, match="not found or disabled"):
            router._get_client("nonexistent")

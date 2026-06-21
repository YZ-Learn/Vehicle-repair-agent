"""
模型工厂 — 抽象工厂模式，YAML 切换模型全家桶。
API Key 优先从环境变量读取，其次从 YAML 配置读取。
"""

import os
from typing import Any
from utils.config_handler import load_config
from utils.logger_handler import logger


# ─── 环境变量 Key 读取 ───────────────────────

ENV_KEY_MAP = {
    "openai_compatible": "DEEPSEEK_API_KEY",
    "dashscope": "DASHSCOPE_API_KEY",
}


def _resolve_api_key(provider: str, yaml_cfg: dict) -> str:
    """优先读环境变量，其次读 YAML"""
    env_key = os.environ.get(ENV_KEY_MAP.get(provider, ""), "")
    if env_key:
        return env_key
    return yaml_cfg.get("api_key", "")


# ─── Chat 模型抽象 ─────────────────────────────


class BaseChatModel:
    def invoke(self, messages: list[dict], **kwargs) -> str:
        raise NotImplementedError

    @property
    def model_name(self) -> str:
        return self.__class__.__name__


class BaseEmbeddingModel:
    def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


# ─── OpenAI 兼容（DeepSeek / 本地 ollama 等） ──


class OpenAIChatModel(BaseChatModel):
    def __init__(self, config: dict):
        import openai
        self._client = openai.OpenAI(
            base_url=config["base_url"],
            api_key=_resolve_api_key("openai_compatible", config),
        )
        self._model = config.get("chat_model", "deepseek-chat")
        self._temperature = config.get("temperature", 0.3)
        self._max_tokens = config.get("max_tokens", 4096)

    def invoke(self, messages: list[dict], **kwargs) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=kwargs.get("temperature", self._temperature),
            max_tokens=kwargs.get("max_tokens", self._max_tokens),
        )
        return resp.choices[0].message.content or ""

    @property
    def model_name(self) -> str:
        return self._model


class OpenAIEmbedding(BaseEmbeddingModel):
    def __init__(self, config: dict):
        import openai
        self._client = openai.OpenAI(
            base_url=config["base_url"],
            api_key=_resolve_api_key("openai_compatible", config),
        )
        self._model = config.get("embedding_model", "text-embedding-v3")

    def embed_query(self, text: str) -> list[float]:
        resp = self._client.embeddings.create(model=self._model, input=text)
        return resp.data[0].embedding

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        resp = self._client.embeddings.create(model=self._model, input=texts)
        return [d.embedding for d in resp.data]


# ─── 工厂入口 ────────────────────────────────


class ModelFactory:
    def __init__(self, config_path: str = "model.yml"):
        self._cfg = load_config(config_path)
        self._provider = self._cfg.get("provider", "openai_compatible")

    def create_chat_model(self) -> BaseChatModel:
        prov_cfg = self._cfg.get(self._provider, {})
        if self._provider == "openai_compatible":
            logger.info(f"[Model] Chat: {prov_cfg.get('chat_model')} via {prov_cfg.get('base_url')}")
            return OpenAIChatModel(prov_cfg)
        raise ValueError(f"不支持的 provider: {self._provider}")

    def create_embedding_model(self) -> BaseEmbeddingModel:
        prov_cfg = self._cfg.get(self._provider, {})
        emb_name = prov_cfg.get("embedding_model", "")
        if emb_name.startswith("BAAI/"):
            return self._create_local_embedding(emb_name)
        if self._provider == "openai_compatible":
            logger.info(f"[Model] Embedding: {emb_name} via API")
            return OpenAIEmbedding(prov_cfg)
        raise ValueError(f"不支持的 embedding: {emb_name}")

    def _create_local_embedding(self, model_name: str):
        from sentence_transformers import SentenceTransformer
        local_cfg = self._cfg.get("local_embedding", {})
        device = local_cfg.get("device", "cpu")
        logger.info(f"[Model] 本地 Embedding: {model_name} on {device}")
        st_model = SentenceTransformer(model_name, device=device)

        class LocalEmbedding(BaseEmbeddingModel):
            def embed_query(self, text: str) -> list[float]:
                return st_model.encode(text).tolist()

            def embed_documents(self, texts: list[str]) -> list[list[float]]:
                return st_model.encode(texts).tolist()

        return LocalEmbedding()

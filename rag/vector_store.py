"""向量数据库封装 — Chroma"""
from typing import Any
import chromadb
from utils.config_handler import load_config
from utils.path_tool import get_abs_path
from utils.logger_handler import logger


class _ChromaEmbeddingWrapper:
    """将任意 embedding 模型包装为 Chroma 兼容的 EmbeddingFunction"""

    def __init__(self, emb_model):
        self._emb = emb_model

    def __call__(self, input):
        """Chroma 要求参数名必须是 'input'"""
        return self._emb.embed_documents(input)


class VectorStore:
    """Chroma 向量库封装"""

    def __init__(self, embedding_fn):
        cfg = load_config("chroma.yml")
        persist_dir = get_abs_path(cfg["persist_dir"])
        collection_name = cfg["collection_name"]

        self._client = chromadb.PersistentClient(path=persist_dir)

        # 自动包装为 Chroma 兼容格式
        embedding_fn = _ChromaEmbeddingWrapper(embedding_fn)

        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            embedding_function=embedding_fn,
        )
        self._top_k = cfg.get("top_k", 4)
        self._score_threshold = cfg.get("score_threshold", 0.6)
        logger.info(f"[VectorStore] collection={collection_name}, dir={persist_dir}")

    def search(self, query: str, top_k: int | None = None) -> list[dict]:
        """检索最相关的文档块"""
        k = top_k or self._top_k
        results = self._collection.query(query_texts=[query], n_results=k)

        docs = []
        if results["documents"]:
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                score = 1.0 - dist
                if score >= self._score_threshold:
                    docs.append({
                        "content": doc,
                        "source": meta.get("source", "未知"),
                        "score": round(score, 3),
                    })
        return docs

    def add_documents(self, documents: list[str], metadatas: list[dict]):
        """批量添加文档"""
        ids = [f"doc_{i}_{metadatas[i].get('source', 'unknown')}" for i in range(len(documents))]
        self._collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )
        logger.info(f"[VectorStore] 入库 {len(documents)} 个文档块")

    def count(self) -> int:
        return self._collection.count()

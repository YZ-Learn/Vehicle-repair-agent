"""RAG 服务：构建检索管道"""
from utils.config_handler import load_config
from utils.logger_handler import logger


class RagService:
    """RAG 服务：检索 + 组装上下文"""

    def __init__(self, vector_store, llm=None):
        self._vs = vector_store
        self._llm = llm
        cfg = load_config("chroma.yml")
        self._enable_rerank = cfg.get("enable_rerank", False)
        self._rerank_top_k = cfg.get("rerank_top_k", 3)

    def search(self, query: str) -> str:
        """检索知识库，返回组装好的上下文文本"""
        # 1. Query 改写
        refined_query = query
        if self._llm:
            refined_query = self._rewrite_query(query)
            logger.debug(f"[RAG] query改写: {query[:40]} → {refined_query[:40]}")

        # 2. 检索
        results = self._vs.search(refined_query)
        if not results:
            logger.warning("[RAG] 未检索到相关内容")
            return ""

        # 3. 重排序
        if self._enable_rerank and len(results) > self._rerank_top_k:
            results = self._rerank(query, results)[: self._rerank_top_k]

        # 4. 组装上下文
        context_parts = []
        for r in results:
            context_parts.append(
                f"【来源：{r['source']}】\n{r['content']}"
            )

        context = "\n\n---\n\n".join(context_parts)
        logger.info(f"[RAG] 检索到 {len(results)} 条相关文档, 共 {len(context)} 字符")
        return context

    def _rewrite_query(self, query: str) -> str:
        """用 LLM 做 query 改写"""
        if not self._llm:
            return query
        prompt = [
            {"role": "system", "content": "你是一个汽车维修查询助手。请将用户的维修问题改写为更适合检索的关键词形式，保留专业术语。直接输出改写结果，不要解释。"},
            {"role": "user", "content": query},
        ]
        return (self._llm.invoke(prompt) or query).strip()

    def _rerank(self, query: str, results: list[dict]) -> list[dict]:
        """简单的重排序：基于关键词匹配度"""
        query_keywords = set(query.lower().split())
        for r in results:
            text_lower = r["content"].lower()
            match_count = sum(1 for kw in query_keywords if kw in text_lower)
            r["score"] = r["score"] * 0.7 + (match_count / max(len(query_keywords), 1)) * 0.3
        return sorted(results, key=lambda x: x["score"], reverse=True)

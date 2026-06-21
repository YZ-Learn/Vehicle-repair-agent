"""
车辆维修助手 Agent — 多步推理引擎。

工作流程：
用户问题 → 分析意图 → 检索知识库 + 调用工具 → 综合回答 → 输出
"""

import json
import time
import re
from typing import Any
from utils.config_handler import load_config
from utils.logger_handler import logger
from rag.rag_service import RagService
from rag.vector_store import VectorStore
from model.factory import ModelFactory
from agent.tools.vehicle_tools import get_all_tools, Tool
from agent.middleware.monitoring import ToolMonitor, ErrorHandler


class RepairAgent:
    """车辆维修智能助手"""

    DEFAULT_SYSTEM_PROMPT = """你是一个专业的车辆维修顾问助手，帮助维修工程师诊断和解决车辆故障。

## 工作原则
1. 首先理解用户描述的故障现象
2. 如果用户提供了故障码（DTC），优先查询故障码
3. 在知识库中检索相关维修信息
4. 综合给出诊断建议和维修方案
5. 涉及安全操作时，提示安全警告

## 回答要求
- 清楚、专业、有条理
- 指出故障的可能原因
- 建议检查步骤和维修方案
- 需要时告知安全注意事项
- 如果不确定，明确告知用户，不要编造

## 可用工具
{tools_description}

## 知识库参考
如果检索到相关文档，请基于文档内容回答。
如果文档中没有相关内容，使用你的专业知识或告诉用户需要查维修手册。

## 工具调用格式
当你需要调用工具时，在回答中输出以下 JSON 格式：

```json
{{"tool": "工具名", "args": {{"参数1": "值1"}}}}
```

系统会截取该 JSON 执行工具，并把结果返回给你。
如果不需要调用工具，直接回答用户问题即可。
"""

    def __init__(self, model_factory: ModelFactory | None = None):
        cfg = load_config("agent.yml")

        self._model_factory = model_factory or ModelFactory()
        self._llm = self._model_factory.create_chat_model()
        self._embedding = self._model_factory.create_embedding_model()

        # RAG
        self._vector_store = VectorStore(self._embedding)
        self._rag = RagService(self._vector_store, self._llm)

        # 工具
        self._tools = get_all_tools()
        self._monitor = ToolMonitor()
        self._error_handler = ErrorHandler()

        self._max_iterations = cfg.get("max_iterations", 8)
        self._system_prompt = self._build_system_prompt()
        self._total_tokens = 0

        logger.info(f"[Agent] 初始化完成 | tools={len(self._tools)} | max_iter={self._max_iterations}")

    def _build_system_prompt(self) -> str:
        tools_desc = []
        for t in self._tools:
            params = t.parameters.get("properties", {})
            param_desc = ", ".join(
                f"{k}({v.get('type','str')})" for k, v in params.items()
            )
            tools_desc.append(f"  • {t.name}：{t.description}，参数：{param_desc}")
        return self.DEFAULT_SYSTEM_PROMPT.format(
            tools_description="\n".join(tools_desc)
        )

    def _call_llm(self, messages: list[dict]) -> tuple[str, dict]:
        try:
            response = self._llm.invoke(messages)
            return response, {"tokens": len(response) // 2}
        except Exception as e:
            logger.error(f"[Agent] LLM 调用失败: {e}")
            return f"抱歉，模型调用遇到问题：{str(e)[:80]}", {"tokens": 0}

    def _try_call_tool(self, name: str, args: dict) -> str:
        for t in self._tools:
            if t.name == name:
                self._monitor.before_call(name, args)
                start = time.time()
                success, result = self._error_handler.safe_tool_call(t.run, **args)
                duration = time.time() - start
                self._monitor.after_call(name, result, duration)
                return result
        return f"错误：未找到工具 {name}"

    def chat(self, user_query: str) -> dict:
        """
        主入口：处理用户问题，返回完整结果。
        """
        # 1. 检索知识库
        knowledge_context = self._rag.search(user_query)

        # 2. 构建 messages
        messages = [{"role": "system", "content": self._system_prompt}]

        if knowledge_context:
            messages.append({
                "role": "system",
                "content": f"以下是知识库中检索到的参考资料，请基于这些内容回答用户问题：\n\n{knowledge_context}",
            })

        messages.append({"role": "user", "content": user_query})

        # 3. 迭代推理
        final_response = ""
        tool_results_accumulated = []

        for iteration in range(self._max_iterations):
            response_text, meta = self._call_llm(messages)
            self._total_tokens += meta.get("tokens", 0)

            if not self._error_handler.check_token_budget(self._total_tokens):
                response_text += "\n\n（提示：已接近 Token 预算上限，如需继续请简短提问。）"
                final_response = response_text
                break

            # 解析工具调用
            tool_call = self._parse_tool_call(response_text)

            if tool_call:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_result = self._try_call_tool(tool_name, tool_args)

                messages.append({"role": "assistant", "content": response_text})
                messages.append({
                    "role": "user",
                    "content": f"工具 {tool_name} 返回结果：\n{tool_result}\n\n请基于此信息继续回答用户问题。",
                })
                tool_results_accumulated.append(tool_name)
                logger.info(f"[Agent] Iter {iteration}: call {tool_name}")
            else:
                final_response = response_text
                logger.info(f"[Agent] Iter {iteration}: 最终回答完成")
                break
        else:
            final_response = "已达到最大推理步数，请更具体地描述问题或尝试简化查询。"
            logger.warning("[Agent] 达到最大迭代次数")

        # 4. 组装返回
        tool_names = ", ".join(
            set(h["name"] for h in self._monitor.tool_call_history)
        )

        return {
            "response": final_response,
            "knowledge_used": knowledge_context[:100] if knowledge_context else "无",
            "tools_called": tool_names,
            "tokens_used": self._total_tokens,
        }

    def _parse_tool_call(self, text: str) -> dict | None:
        """从 LLM 输出中解析工具调用"""
        text_stripped = text.strip()

        # 检测 markdown 代码块中的 JSON
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text_stripped, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                name = data.get("tool") or data.get("name") or data.get("function")
                args = data.get("args") or data.get("arguments", {})
                if name:
                    return {"name": name, "args": args}
            except json.JSONDecodeError:
                pass

        # 尝试顶层 JSON
        if text_stripped.startswith("{"):
            try:
                data = json.loads(text_stripped)
                name = data.get("tool") or data.get("name") or data.get("function")
                args = data.get("args") or data.get("arguments", {})
                if name:
                    return {"name": name, "args": args}
            except json.JSONDecodeError:
                pass

        return None

    def reset_monitor(self):
        self._monitor = ToolMonitor()
        self._total_tokens = 0

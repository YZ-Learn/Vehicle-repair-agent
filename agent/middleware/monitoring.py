"""中间件：监控、日志、错误兜底"""
import time
from utils.logger_handler import logger


class ToolMonitor:
    def __init__(self):
        self.tool_call_count = 0
        self.tool_call_history: list[dict] = []

    def before_call(self, tool_name: str, args: dict):
        self.tool_call_count += 1
        logger.info(f"[Monitor] 调用工具 [{self.tool_call_count}]：{tool_name}({args})")
        self.tool_call_history.append({
            "name": tool_name,
            "args": args,
            "time": time.time(),
        })

    def after_call(self, tool_name: str, result: str, duration: float):
        logger.info(f"[Monitor] 工具 {tool_name} 完成，耗时 {duration:.2f}s，结果长度 {len(result)}")

    def get_summary(self) -> str:
        if not self.tool_call_history:
            return "本次未调用工具"
        tools = set(h["name"] for h in self.tool_call_history)
        return f"调用了 {self.tool_call_count} 次工具：{', '.join(tools)}"


class ErrorHandler:
    BUDGET_TOKENS = 4000

    @staticmethod
    def safe_tool_call(tool_func, **kwargs) -> tuple[bool, str]:
        try:
            result = tool_func(**kwargs)
            return True, str(result)
        except Exception as e:
            logger.error(f"[Error] 工具执行异常: {e}")
            return False, f"抱歉，执行该操作时遇到错误：{str(e)[:100]}"

    @staticmethod
    def check_token_budget(total_tokens: int) -> bool:
        if total_tokens > ErrorHandler.BUDGET_TOKENS:
            logger.warning(f"[Error] 超出 Token 预算：{total_tokens}/{ErrorHandler.BUDGET_TOKENS}")
            return False
        return True

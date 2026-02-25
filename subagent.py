"""
Sub-agent: 专职代码审查员

⭐ 核心竞争力 ⑤ Planning & Reasoning（Sub-agent 扩展）

关键洞察：工具可以是另一个 Agent。
从 Orchestrator 视角看，delegate_to_subagent 就是一个普通工具——
调用它、拿结果。但内部它是一个完整的 Agent，有自己的：
  - 系统提示（专职角色）
  - 工具集（精简的只读工具）
  - LLM 调用
  - Agentic loop

设计决定：
  - Sub-agent 只有只读工具（read_file, list_files）
    → 代码审查员不应该修改文件
  - Sub-agent 用 create() 而不是 stream()
    → 结果要作为字符串返回给 Orchestrator，不是直接打印
  - Sub-agent 没有 human-in-the-loop 确认
    → 由 Orchestrator 调用，不直接面对用户
  - Sub-agent 不导入 agent.py 或 tools.py
    → 避免循环导入，自带精简工具定义
"""

import os
from anthropic import Anthropic
from config import ANTHROPIC_API_KEY


# ============================================================
# Sub-agent 的工具集（只读，精简版）
# 不使用 @tool 装饰器，避免污染主 agent 的工具注册表
# ============================================================

def _read_file(path: str) -> str:
    try:
        if not os.path.exists(path):
            return f"错误：文件不存在 - {path}"
        if not os.path.isfile(path):
            return f"错误：路径不是文件 - {path}"
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"读取文件失败：{str(e)}"


def _list_files(path: str = ".") -> str:
    try:
        if not os.path.exists(path):
            return f"错误：目录不存在 - {path}"
        entries = os.listdir(path)
        result = []
        for entry in sorted(entries):
            full_path = os.path.join(path, entry)
            if os.path.isdir(full_path):
                result.append(f"  [目录] {entry}/")
            else:
                size = os.path.getsize(full_path)
                result.append(f"  [文件] {entry} ({size} bytes)")
        return f"目录 {path} 的内容：\n" + "\n".join(result)
    except Exception as e:
        return f"列出目录失败：{str(e)}"


SUBAGENT_TOOLS = [
    {
        "name": "read_file",
        "description": "读取指定路径的文件内容。",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "要读取的文件路径"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "list_files",
        "description": "列出指定目录下的文件和子目录。",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "目录路径，默认当前目录"}
            },
            "required": []
        }
    }
]

SUBAGENT_TOOL_FUNCTIONS = {
    "read_file": _read_file,
    "list_files": _list_files,
}


# ============================================================
# Sub-agent 类
# ============================================================

class SubAgent:
    """
    专职代码审查 Sub-agent

    被 Orchestrator 通过 delegate_to_subagent 工具调用。
    run() 返回字符串结果，供 Orchestrator 使用。
    """

    def __init__(self, max_turns: int = 5):
        self.client = Anthropic(api_key=ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-20250514"
        self.max_turns = max_turns
        self.system_prompt = """你是一个专职代码审查员。你的工作是：
- 阅读和分析代码文件
- 评估代码质量、可读性、潜在 bug
- 给出具体、建设性的改进建议

你只能读取文件，不能修改任何内容。
审查完成后，给出简洁的审查报告。"""

    def run(self, task: str) -> str:
        """运行 Sub-agent，返回审查结果字符串"""
        print(f"\n    [Sub-agent 启动] {task}")

        messages = [{"role": "user", "content": task}]

        turn = 0
        while turn < self.max_turns:
            turn += 1
            print(f"    [Sub-agent 第 {turn} 轮]")

            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=self.system_prompt,
                tools=SUBAGENT_TOOLS,
                messages=messages
            )

            if response.stop_reason == "end_turn":
                print(f"    [Sub-agent 完成]")
                for block in response.content:
                    if hasattr(block, "text"):
                        return block.text
                return ""

            elif response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        print(f"    [Sub-agent 工具] {block.name}({block.input})")
                        func = SUBAGENT_TOOL_FUNCTIONS.get(block.name)
                        result = func(**block.input) if func else f"未知工具: {block.name}"
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result
                        })
                messages.append({"role": "user", "content": tool_results})

        return "Sub-agent 达到最大轮次，任务未完成。"

"""
Step 1: 定义一个最简单的工具 - 读取文件

工具的核心要素：
1. schema - 告诉 LLM 这个工具是什么、怎么用
2. execute - 实际执行工具的函数
"""

import os


# ============================================================
# 工具 Schema 定义
# 这是告诉 LLM "你有这个工具可以用" 的描述
# 遵循 Claude 的 tool use 格式
# ============================================================

READ_FILE_TOOL = {
    "name": "read_file",
    "description": "读取指定路径的文件内容。当你需要查看文件内容时使用此工具。",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "要读取的文件路径"
            }
        },
        "required": ["path"]
    }
}


# ============================================================
# 工具执行函数
# 当 LLM 决定调用工具时，我们实际执行的代码
# ============================================================

def read_file(path: str) -> str:
    """读取文件内容"""
    try:
        # 安全检查：确保路径存在
        if not os.path.exists(path):
            return f"错误：文件不存在 - {path}"

        if not os.path.isfile(path):
            return f"错误：路径不是文件 - {path}"

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        return content

    except Exception as e:
        return f"读取文件失败：{str(e)}"


# ============================================================
# 工具注册表
# 把所有工具放在一起，方便管理
# ============================================================

# 所有工具的 schema 列表（传给 LLM）
ALL_TOOLS = [READ_FILE_TOOL]

# 工具名称 -> 执行函数的映射
TOOL_FUNCTIONS = {
    "read_file": read_file
}


def execute_tool(tool_name: str, tool_input: dict) -> str:
    """
    根据工具名称执行对应的工具

    Args:
        tool_name: 工具名称
        tool_input: 工具参数（字典）

    Returns:
        工具执行结果（字符串）
    """
    if tool_name not in TOOL_FUNCTIONS:
        return f"错误：未知工具 - {tool_name}"

    func = TOOL_FUNCTIONS[tool_name]

    # 调用工具函数，传入参数
    return func(**tool_input)

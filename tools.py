"""
Step 3: 工具系统

改进：用装饰器自动注册工具，添加新工具只需一处定义
新增：write_file, list_files 工具

⭐ 核心竞争力 ② Tool Design
   - 装饰器模式让工具注册更简洁
   - 每个工具的 schema 描述要清晰（影响 LLM 能否正确使用）
   - 工具粒度要合适
"""

import os


# ============================================================
# 工具注册表
# ============================================================

# 存储所有注册的工具
_tool_registry = {}


def tool(name: str, description: str, params: dict):
    """
    工具注册装饰器

    用法：
        @tool(
            name="read_file",
            description="读取文件内容",
            params={
                "path": {"type": "string", "description": "文件路径"}
            }
        )
        def read_file(path: str) -> str:
            ...

    装饰器会自动：
    1. 生成 schema（传给 LLM 的工具描述）
    2. 注册函数（工具名 → 函数的映射）
    """
    def decorator(func):
        # 自动生成 schema
        schema = {
            "name": name,
            "description": description,
            "input_schema": {
                "type": "object",
                "properties": {
                    # 过滤掉 optional 标记，只保留 API 需要的字段
                    k: {sk: sv for sk, sv in v.items() if sk != "optional"}
                    for k, v in params.items()
                },
                "required": [k for k, v in params.items() if not v.get("optional", False)]
            }
        }

        # 注册到全局注册表
        _tool_registry[name] = {
            "schema": schema,
            "function": func
        }

        return func

    return decorator


# ============================================================
# 工具定义（schema + 实现写在一起）
#
# ⭐ 核心竞争力 ② Tool Design
#    添加新工具只需要：在这里加一个 @tool 装饰的函数
#    不用再手动维护 ALL_TOOLS 和 TOOL_FUNCTIONS
# ============================================================

@tool(
    name="read_file",
    description="读取指定路径的文件内容。当你需要查看文件代码或内容时使用此工具。",
    params={
        "path": {
            "type": "string",
            "description": "要读取的文件路径"
        }
    }
)
def read_file(path: str) -> str:
    """读取文件内容"""
    try:
        if not os.path.exists(path):
            return f"错误：文件不存在 - {path}"
        if not os.path.isfile(path):
            return f"错误：路径不是文件 - {path}"

        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"读取文件失败：{str(e)}"


@tool(
    name="write_file",
    description="将内容写入指定路径的文件。文件不存在会自动创建，已存在会覆盖。",
    params={
        "path": {
            "type": "string",
            "description": "要写入的文件路径"
        },
        "content": {
            "type": "string",
            "description": "要写入的文件内容"
        }
    }
)
def write_file(path: str, content: str) -> str:
    """写入文件"""
    try:
        dir_name = os.path.dirname(path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        return f"文件写入成功：{path}"
    except Exception as e:
        return f"写入文件失败：{str(e)}"


@tool(
    name="list_files",
    description="列出指定目录下的文件和子目录。当你需要了解项目结构时使用此工具。",
    params={
        "path": {
            "type": "string",
            "description": "要列出内容的目录路径，默认为当前目录",
            "optional": True
        }
    }
)
def list_files(path: str = ".") -> str:
    """列出目录内容"""
    try:
        if not os.path.exists(path):
            return f"错误：目录不存在 - {path}"
        if not os.path.isdir(path):
            return f"错误：路径不是目录 - {path}"

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


# ============================================================
# Step 5 新增：执行代码工具
#
# ⭐ 核心竞争力 ⑨ Safety & Guardrails
#    这个工具能执行任意命令，非常危险
#    我们的简化版：只加了超时限制
#    生产环境需要：沙箱、命令白名单、权限控制、审计日志
# ============================================================

import subprocess


@tool(
    name="execute_code",
    description="执行命令行命令（如 python xxx.py）。用于运行代码、安装依赖、查看运行结果。",
    params={
        "command": {
            "type": "string",
            "description": "要执行的命令行命令"
        },
        "timeout": {
            "type": "integer",
            "description": "超时时间（秒），默认 30 秒",
            "optional": True
        }
    }
)
def execute_code(command: str, timeout: int = 30) -> str:
    """执行命令行命令"""
    try:
        # 设置 UTF-8 编码，解决 Windows 中文输出问题
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env
        )

        output = ""
        if result.stdout:
            output += f"[stdout]\n{result.stdout}"
        if result.stderr:
            output += f"[stderr]\n{result.stderr}"
        if not output:
            output = "(无输出)"

        output += f"\n[返回码: {result.returncode}]"
        return output

    except subprocess.TimeoutExpired:
        return f"错误：命令执行超时（{timeout}秒）"
    except Exception as e:
        return f"执行命令失败：{str(e)}"


# ============================================================
# 对外接口（给 agent.py 用的）
# ============================================================

def get_all_tools() -> list:
    """获取所有工具的 schema 列表（传给 LLM）"""
    return [entry["schema"] for entry in _tool_registry.values()]


def execute_tool(tool_name: str, tool_input: dict) -> str:
    """执行指定工具"""
    if tool_name not in _tool_registry:
        return f"错误：未知工具 - {tool_name}"

    func = _tool_registry[tool_name]["function"]
    return func(**tool_input)

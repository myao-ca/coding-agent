"""
Step 2: Agent 循环

改进：从单次工具调用 → 支持多轮工具调用
核心变化：加入 while 循环，直到 LLM 不再需要工具

⭐ 核心竞争力 ⑦ Agentic Loop Design
   - 这里用简单的 while 循环 + 最大轮次限制
   - 生产环境还需要：超时机制、死循环检测、优雅中断等
"""

from anthropic import Anthropic
from tools import ALL_TOOLS, execute_tool
from config import ANTHROPIC_API_KEY


class Agent:
    def __init__(self, max_turns: int = 10):
        """
        初始化 Agent

        Args:
            max_turns: 最大循环轮次，防止无限循环
                      ⭐ 核心竞争力 ⑦：这是最简单的安全机制
        """
        self.client = Anthropic(api_key=ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-20250514"
        self.max_turns = max_turns

        self.system_prompt = """你是一个编程助手。你可以帮助用户：
- 阅读和分析代码文件
- 回答编程问题

当用户询问文件内容时，使用 read_file 工具来读取文件。
如果需要读取多个文件，可以多次使用工具。
回答要简洁、准确。"""

    def run(self, user_message: str) -> str:
        """
        运行 Agent 处理用户消息

        核心改进：使用 while 循环，支持多轮工具调用
        """
        self._print_header("用户输入")
        print(f"  {user_message}")

        # 构建消息列表
        messages = [
            {"role": "user", "content": user_message}
        ]

        turn = 0
        while turn < self.max_turns:
            turn += 1

            self._print_header(f"第 {turn} 轮")

            # 显示当前 messages 概况
            self._print_messages_summary(messages)

            print("\n  >>> 调用 LLM...")

            # 调用 LLM
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=self.system_prompt,
                tools=ALL_TOOLS,
                messages=messages
            )

            print(f"  <<< LLM 返回 (stop_reason: {response.stop_reason})")

            # 显示 LLM 返回的内容
            self._print_response_content(response)

            # ----- 判断是否需要继续循环 -----
            if response.stop_reason == "end_turn":
                self._print_header("循环结束")
                print(f"  共执行 {turn} 轮")
                return self._extract_text(response)

            elif response.stop_reason == "tool_use":
                # LLM 需要使用工具，处理后继续循环
                print("\n  --- 执行工具 ---")
                self._process_tool_calls(messages, response)
                print("  --- 工具执行完毕，继续下一轮 ---")

            else:
                print(f"\n  [!] 意外的 stop_reason: {response.stop_reason}")
                return self._extract_text(response)

        # 达到最大轮次
        self._print_header("警告")
        print(f"  达到最大轮次 {self.max_turns}，强制退出")
        return "抱歉，处理轮次过多，已停止。"

    def _process_tool_calls(self, messages: list, response) -> None:
        """处理工具调用"""
        # 把 LLM 的响应添加到消息历史
        messages.append({
            "role": "assistant",
            "content": response.content
        })

        # 处理所有工具调用
        tool_results = []
        tool_count = sum(1 for b in response.content if b.type == "tool_use")
        current_tool = 0

        for block in response.content:
            if block.type == "tool_use":
                current_tool += 1
                tool_name = block.name
                tool_input = block.input
                tool_use_id = block.id

                print(f"\n  [{current_tool}/{tool_count}] 工具: {tool_name}")
                print(f"      参数: {tool_input}")

                # 执行工具
                result = execute_tool(tool_name, tool_input)

                # 显示结果（截断太长的输出）
                result_lines = result.split('\n')
                if len(result_lines) > 5:
                    display_result = '\n'.join(result_lines[:5]) + f"\n      ... (共 {len(result_lines)} 行)"
                elif len(result) > 200:
                    display_result = result[:200] + "..."
                else:
                    display_result = result

                # 缩进结果显示
                indented_result = display_result.replace('\n', '\n      ')
                print(f"      结果: {indented_result}")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": result
                })

        # 把工具结果添加到消息历史
        messages.append({
            "role": "user",
            "content": tool_results
        })

    def _print_header(self, title: str) -> None:
        """打印分隔标题"""
        print(f"\n{'='*60}")
        print(f"  {title}")
        print('='*60)

    def _print_messages_summary(self, messages: list) -> None:
        """打印 messages 列表概况"""
        print(f"\n  当前 messages 队列 ({len(messages)} 条):")
        for i, msg in enumerate(messages):
            role = msg["role"]
            content = msg["content"]

            if isinstance(content, str):
                # 普通文本消息
                preview = content[:50] + "..." if len(content) > 50 else content
                print(f"    [{i}] {role}: \"{preview}\"")
            elif isinstance(content, list):
                # 包含多个 block 的消息
                block_types = []
                for block in content:
                    if isinstance(block, dict):
                        block_types.append(block.get("type", "unknown"))
                    else:
                        block_types.append(getattr(block, "type", "unknown"))
                print(f"    [{i}] {role}: [{', '.join(block_types)}]")

    def _print_response_content(self, response) -> None:
        """打印 LLM 响应内容"""
        print(f"\n  LLM 响应内容:")
        for i, block in enumerate(response.content):
            if block.type == "text":
                text_preview = block.text[:100] + "..." if len(block.text) > 100 else block.text
                print(f"    [{i}] text: \"{text_preview}\"")
            elif block.type == "tool_use":
                print(f"    [{i}] tool_use: {block.name}({block.input})")

    def _extract_text(self, response) -> str:
        """从响应中提取文本内容"""
        for block in response.content:
            if hasattr(block, "text"):
                return block.text
        return ""


# ============================================================
# 主程序
# ============================================================

def main():
    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "在这里填入你的API Key":
        print("错误：请在 config.py 中设置你的 ANTHROPIC_API_KEY")
        return

    agent = Agent(max_turns=10)

    # 测试：需要多次工具调用的任务
    result = agent.run("请分别读取 agent.py 和 tools.py 文件，对比它们的代码行数，哪个更长？")

    print("\n")
    print("*" * 60)
    print("  最终回答")
    print("*" * 60)
    print(f"\n{result}")


if __name__ == "__main__":
    main()

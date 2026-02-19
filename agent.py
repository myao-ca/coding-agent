"""
Step 4: 对话记忆

改进：messages 从局部变量提升为实例变量，支持多轮对话
新增：交互式对话循环（REPL）

⭐ 核心竞争力 ⑥ Memory Systems
   - 最简单的短期记忆：对话历史保留在内存中
   - 生产环境还需要：持久化、上下文压缩、跨会话记忆

⭐ 核心竞争力 ① Context Management
   - messages 会随对话持续增长，之前讨论的问题现在更突出
"""

from anthropic import Anthropic
from tools import get_all_tools, execute_tool
from config import ANTHROPIC_API_KEY


class Agent:
    def __init__(self, max_turns: int = 10):
        self.client = Anthropic(api_key=ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-20250514"
        self.max_turns = max_turns

        self.system_prompt = """你是一个编程助手。你可以帮助用户：
- 阅读和分析代码文件
- 创建和修改文件
- 查看项目目录结构
- 回答编程问题

使用 read_file 读取文件，write_file 写入文件，list_files 查看目录。
如果需要多个操作，可以多次使用工具。
回答要简洁、准确。"""

        # ============================================================
        # ⭐ 核心竞争力 ⑥ Memory Systems
        #
        # Step 4 核心改动：messages 从 run() 的局部变量 → 实例变量
        # 这样每次 run() 调用都能看到之前的对话历史
        #
        # 这是最简单的"短期记忆"实现
        # 局限：
        # - 只在内存中，程序关闭就丢失
        # - 会无限增长，最终超出 context 限制
        # ============================================================
        self.conversation_history = []

    def run(self, user_message: str) -> str:
        """
        运行 Agent 处理用户消息

        Step 4 改动：不再每次创建新 messages，而是追加到 conversation_history
        """
        self._print_header("用户输入")
        print(f"  {user_message}")

        # 追加用户消息到对话历史（不再每次新建）
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        turn = 0
        while turn < self.max_turns:
            turn += 1

            self._print_header(f"第 {turn} 轮")
            self._print_messages_summary(self.conversation_history)

            print("\n  >>> 调用 LLM...")

            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=self.system_prompt,
                tools=get_all_tools(),
                messages=self.conversation_history
            )

            print(f"  <<< LLM 返回 (stop_reason: {response.stop_reason})")
            self._print_response_content(response)

            if response.stop_reason == "end_turn":
                # 把 LLM 的最终回答也存入对话历史
                self.conversation_history.append({
                    "role": "assistant",
                    "content": response.content
                })

                self._print_header("循环结束")
                print(f"  共执行 {turn} 轮")
                return self._extract_text(response)

            elif response.stop_reason == "tool_use":
                print("\n  --- 执行工具 ---")
                self._process_tool_calls(self.conversation_history, response)
                print("  --- 工具执行完毕，继续下一轮 ---")

            else:
                print(f"\n  [!] 意外的 stop_reason: {response.stop_reason}")
                return self._extract_text(response)

        self._print_header("警告")
        print(f"  达到最大轮次 {self.max_turns}，强制退出")
        return "抱歉，处理轮次过多，已停止。"

    def reset(self):
        """清空对话历史，开始新对话"""
        self.conversation_history = []
        print("[对话历史已清空]")

    def _process_tool_calls(self, messages: list, response) -> None:
        """处理工具调用"""
        messages.append({
            "role": "assistant",
            "content": response.content
        })

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

                result = execute_tool(tool_name, tool_input)

                result_lines = result.split('\n')
                if len(result_lines) > 5:
                    display_result = '\n'.join(result_lines[:5]) + f"\n      ... (共 {len(result_lines)} 行)"
                elif len(result) > 200:
                    display_result = result[:200] + "..."
                else:
                    display_result = result

                indented_result = display_result.replace('\n', '\n      ')
                print(f"      结果: {indented_result}")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": result
                })

        messages.append({
            "role": "user",
            "content": tool_results
        })

    def _print_header(self, title: str) -> None:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print('='*60)

    def _print_messages_summary(self, messages: list) -> None:
        print(f"\n  messages 队列 ({len(messages)} 条):")
        for i, msg in enumerate(messages):
            role = msg["role"][:4]  # user/asst
            content = msg["content"]

            if isinstance(content, str):
                preview = content[:40] + "..." if len(content) > 40 else content
                print(f"  [{i}] {role}: \"{preview}\"")
            elif isinstance(content, list):
                block_types = []
                for block in content:
                    if isinstance(block, dict):
                        block_types.append(block.get("type", "?"))
                    else:
                        btype = getattr(block, "type", "?")
                        if btype == "tool_use":
                            btype = f"tool:{block.name}"
                        block_types.append(btype)
                print(f"  [{i}] {role}: [{', '.join(block_types)}]")

    def _print_response_content(self, response) -> None:
        print(f"\n  LLM 响应内容:")
        for i, block in enumerate(response.content):
            if block.type == "text":
                text_preview = block.text[:100] + "..." if len(block.text) > 100 else block.text
                print(f"    [{i}] text: \"{text_preview}\"")
            elif block.type == "tool_use":
                print(f"    [{i}] tool_use: {block.name}({block.input})")

    def _extract_text(self, response) -> str:
        for block in response.content:
            if hasattr(block, "text"):
                return block.text
        return ""


# ============================================================
# 主程序：交互式对话循环（REPL）
# ============================================================

def main():
    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "在这里填入你的API Key":
        print("错误：请在 config.py 中设置你的 ANTHROPIC_API_KEY")
        return

    agent = Agent(max_turns=10)

    print("=" * 60)
    print("  编程助手 Agent (输入 quit 退出, reset 清空对话)")
    print("=" * 60)

    while True:
        try:
            user_input = input("\n你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue
        if user_input.lower() == "quit":
            print("再见！")
            break
        if user_input.lower() == "reset":
            agent.reset()
            continue

        result = agent.run(user_input)
        print(f"\nAgent: {result}")


if __name__ == "__main__":
    main()

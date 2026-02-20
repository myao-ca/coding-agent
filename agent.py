"""
Step 7: 错误处理与恢复

改进：给 LLM API 调用添加重试机制，区分可重试和不可重试错误
新增：指数退避重试、错误分类、优雅降级

⭐ 核心竞争力 ④ Error Handling & Recovery
   - 重试：临时性错误（网络超时、限流）自动重试，指数退避
   - 不可重试：鉴权失败、参数错误，直接上报
   - 优雅降级：重试耗尽后返回友好消息，不崩溃
"""

import time
import anthropic as anthropic_lib
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

        self.conversation_history = []

    def run(self, user_message: str) -> str:
        """运行 Agent 处理用户消息"""
        self._print_header("用户输入")
        print(f"  {user_message}")

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

            # ============================================================
            # ⭐ 核心竞争力 ④ Error Handling & Recovery
            #
            # Step 7 核心改动：把 LLM 调用包裹在 try/except 中
            # _call_llm_with_retry() 内部处理重试逻辑
            # 如果重试耗尽，异常会冒泡到这里，返回友好消息（降级）
            # ============================================================
            try:
                response = self._call_llm_with_retry(self.conversation_history)
            except anthropic_lib.RateLimitError:
                self._print_header("错误")
                print("  API 限流，重试次数耗尽")
                return "抱歉，API 调用频率超限，请稍后再试。"
            except anthropic_lib.APIConnectionError:
                self._print_header("错误")
                print("  网络连接失败，重试次数耗尽")
                return "抱歉，网络连接失败，请检查网络后重试。"
            except anthropic_lib.AuthenticationError:
                self._print_header("错误")
                print("  API Key 无效")
                return "抱歉，API Key 无效，请检查 config.py 中的配置。"
            except anthropic_lib.BadRequestError as e:
                self._print_header("错误")
                print(f"  请求参数错误: {e}")
                return f"抱歉，请求出错：{str(e)}"
            except Exception as e:
                self._print_header("错误")
                print(f"  未知错误: {e}")
                return f"抱歉，发生未知错误：{str(e)}"

            print(f"  <<< LLM 返回 (stop_reason: {response.stop_reason})")
            self._print_response_content(response)

            if response.stop_reason == "end_turn":
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

    # ============================================================
    # ⭐ 核心竞争力 ④ Error Handling & Recovery
    #
    # Step 7 新增：LLM 调用 + 指数退避重试
    #
    # 错误分类：
    #   可重试（临时性问题，等一会儿能好）：
    #     - RateLimitError (429)：触发限流
    #     - APIConnectionError：网络抖动
    #
    #   不可重试（配置或逻辑问题，重试没用）：
    #     - AuthenticationError (401)：API Key 错误
    #     - BadRequestError (400)：请求参数有问题
    #
    # 指数退避：第 1 次失败等 1s，第 2 次等 2s，第 3 次等 4s
    # 这样不会在 API 已经过载时雪上加霜
    # ============================================================

    def _call_llm_with_retry(self, messages: list):
        """调用 LLM，遇到可重试错误时自动重试（指数退避）"""
        max_retries = 3

        for attempt in range(max_retries):
            try:
                return self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=self.system_prompt,
                    tools=get_all_tools(),
                    messages=messages
                )

            except anthropic_lib.RateLimitError as e:
                # 可重试：触发限流（429），等一会儿再试
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    print(f"\n  [重试] 触发限流 (429)，{wait_time}s 后重试 ({attempt + 1}/{max_retries})...")
                    time.sleep(wait_time)
                else:
                    print(f"\n  [放弃] 已重试 {max_retries} 次，限流未解除")
                    raise

            except anthropic_lib.APIConnectionError as e:
                # 可重试：网络抖动，重连即可
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"\n  [重试] 网络连接失败，{wait_time}s 后重试 ({attempt + 1}/{max_retries})...")
                    time.sleep(wait_time)
                else:
                    print(f"\n  [放弃] 已重试 {max_retries} 次，网络仍不通")
                    raise

            except anthropic_lib.AuthenticationError:
                # 不可重试：API Key 错误，重试没用
                print(f"\n  [鉴权失败] API Key 无效，请检查 config.py，不再重试")
                raise

            except anthropic_lib.BadRequestError as e:
                # 不可重试：请求参数有问题，重试没用
                print(f"\n  [请求错误] 参数有问题，不再重试: {e}")
                raise

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

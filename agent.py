"""
Step 8: 流式输出（Streaming）

改进：LLM 响应边生成边打印，而不是等全部生成完才显示

⭐ 核心竞争力 ⑩ User Experience
   - 流式输出：LLM 打字机效果，用户立刻看到响应
   - 生产环境标配：等待几秒才出现内容体验极差
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

    def run(self, user_message: str) -> None:
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

            print("\n  >>> 调用 LLM（流式）...\n")

            # ============================================================
            # ⭐ 核心竞争力 ⑩ User Experience
            #
            # _call_llm_with_retry() 内部用 stream()：
            #   - 文字边生成边打印（打字机效果）
            #   - 返回完整的 response 对象（和非流式一样），供后续循环使用
            # ============================================================
            try:
                response = self._call_llm_with_retry(self.conversation_history)
            except anthropic_lib.RateLimitError:
                self._print_header("错误")
                print("  API 限流，重试次数耗尽，请稍后再试。")
                return
            except anthropic_lib.APIConnectionError:
                self._print_header("错误")
                print("  网络连接失败，请检查网络后重试。")
                return
            except anthropic_lib.AuthenticationError:
                self._print_header("错误")
                print("  API Key 无效，请检查 config.py 中的配置。")
                return
            except anthropic_lib.BadRequestError as e:
                self._print_header("错误")
                print(f"  请求出错：{str(e)}")
                return
            except Exception as e:
                self._print_header("错误")
                print(f"  未知错误：{str(e)}")
                return

            print(f"\n  <<< 流式完成 (stop_reason: {response.stop_reason})")
            self._print_response_content(response)

            if response.stop_reason == "end_turn":
                self.conversation_history.append({
                    "role": "assistant",
                    "content": response.content
                })

                self._print_header("循环结束")
                print(f"  共执行 {turn} 轮")
                return

            elif response.stop_reason == "tool_use":
                print("\n  --- 执行工具 ---")
                self._process_tool_calls(self.conversation_history, response)
                print("  --- 工具执行完毕，继续下一轮 ---")

            else:
                print(f"\n  [!] 意外的 stop_reason: {response.stop_reason}")
                return

        self._print_header("警告")
        print(f"  达到最大轮次 {self.max_turns}，强制退出")

    def reset(self):
        """清空对话历史，开始新对话"""
        self.conversation_history = []
        print("[对话历史已清空]")

    # ============================================================
    # ⭐ 核心竞争力 ⑩ User Experience（Step 8 核心改动）
    #
    # 关键区别：
    #   非流式：client.messages.create() → 等全部生成完 → 返回完整 response
    #   流式：  client.messages.stream() → 边生成边打印 → stream 结束后拿完整 response
    #
    # stream.text_stream 只 yield 文字 token，工具调用不在这里
    # stream.get_final_message() 返回和 create() 一样的 response 对象
    # 所以 stream 结束后，后续的工具调用处理逻辑完全不用改
    # ============================================================

    def _call_llm_with_retry(self, messages: list):
        """调用 LLM（流式），遇到可重试错误时自动重试（指数退避）"""
        max_retries = 3

        for attempt in range(max_retries):
            try:
                with self.client.messages.stream(
                    model=self.model,
                    max_tokens=4096,
                    system=self.system_prompt,
                    tools=get_all_tools(),
                    messages=messages
                ) as stream:
                    # 边生成边打印文字（打字机效果）
                    for text in stream.text_stream:
                        print(text, end="", flush=True)

                    # 返回完整 response，和 create() 的返回值接口一致
                    return stream.get_final_message()

            except anthropic_lib.RateLimitError as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"\n  [重试] 触发限流 (429)，{wait_time}s 后重试 ({attempt + 1}/{max_retries})...")
                    time.sleep(wait_time)
                else:
                    print(f"\n  [放弃] 已重试 {max_retries} 次，限流未解除")
                    raise

            except anthropic_lib.APIConnectionError as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"\n  [重试] 网络连接失败，{wait_time}s 后重试 ({attempt + 1}/{max_retries})...")
                    time.sleep(wait_time)
                else:
                    print(f"\n  [放弃] 已重试 {max_retries} 次，网络仍不通")
                    raise

            except anthropic_lib.AuthenticationError:
                print(f"\n  [鉴权失败] API Key 无效，不再重试")
                raise

            except anthropic_lib.BadRequestError as e:
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
            role = msg["role"][:4]
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
        # ⭐ streaming 模式下，文字已经实时打印过了，这里只显示工具调用
        tool_blocks = [b for b in response.content if b.type == "tool_use"]
        if tool_blocks:
            print(f"\n  工具调用:")
            for block in tool_blocks:
                print(f"    tool_use: {block.name}({block.input})")


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

        # ⭐ streaming 模式下，run() 内部直接打印输出，不再返回文字
        agent.run(user_input)


if __name__ == "__main__":
    main()

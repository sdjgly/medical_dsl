import threading
import time
import uuid
from pathlib import Path
import sys
import os

# 项目根目录
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.main import DSLChatbot, get_script_path
from src.dsl_parser import load_script_from_file

NUM_USERS = 10              # 并发用户数
ROUNDS_PER_USER = 5         # 每个用户对话轮数
MODULE = "ecommerce"        # 也支持 medical
DB_PATH = os.path.join(project_root, "database", "ecommerce.db")

test_results = []
lock = threading.Lock()


class UserThread(threading.Thread):
    def __init__(self, user_id: str):
        super().__init__()
        self.user_id = user_id
        self.errors = []

    def run(self):
        try:
            self.run_session()
        except Exception as e:
            self.errors.append(f"线程崩溃: {e}")

    def run_session(self):
        script_path = get_script_path(MODULE)
        bot = DSLChatbot(
            script_path=script_path,
            use_ai=False,        # 禁用 AI，加快测试
            db_path=DB_PATH
        )

        if not bot.initialize():
            self.errors.append("初始化失败")
            return

        interp = bot.interpreter
        interp.is_running = True

        # 设定一个“伪用户输入”函数替代 input()
        def fake_input(prompt=""):
            return self.fake_inputs.pop(0)

        # 替换 input（解释器内部会调用）
        interp.input = fake_input

        # 构造本用户的输入序列
        self.fake_inputs = []
        for i in range(ROUNDS_PER_USER):
            self.fake_inputs.append(f"用户{self.user_id}的第{i+1}次输入")

        # 运行
        for round_i in range(ROUNDS_PER_USER):
            try:
                interp.step()
            except Exception as e:
                self.errors.append(f"执行失败: {e}")

        # 记录结果
        with lock:
            test_results.append((self.user_id, self.errors))


def run_concurrency_test():
    print("=============================================")
    print(f" 启动 {NUM_USERS} 用户并发测试（每人 {ROUNDS_PER_USER} 轮）")
    print("=============================================\n")

    threads = []

    for _ in range(NUM_USERS):
        user_id = str(uuid.uuid4())[:8]
        thread = UserThread(user_id)
        threads.append(thread)
        thread.start()
        time.sleep(0.1)   # 小幅错开启动时间避免阻塞

    for t in threads:
        t.join()

    print("\n==================== 测试结果 ====================")
    success = 0
    fail = 0
    for user_id, errors in test_results:
        if errors:
            fail += 1
            print(f"[用户 {user_id}] ❌ 错误：")
            for e in errors:
                print("    -", e)
        else:
            success += 1
            print(f"[用户 {user_id}] ✅ 正常完成")

    print("-------------------------------------------------")
    print(f"共 {NUM_USERS} 用户：成功 {success}，失败 {fail}")
    print("=================================================\n")


if __name__ == "__main__":
    run_concurrency_test()

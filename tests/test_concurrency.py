import os
import sys
import threading
import time
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional
import queue

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))  # tests目录
project_root = os.path.dirname(current_dir)  # medical_dsl项目根目录
src_dir = os.path.join(project_root, "src")
database_dir = os.path.join(project_root, "database")
scripts_dir = os.path.join(project_root, "scripts")

# 添加所有必要的路径
sys.path.insert(0, project_root)  # 项目根目录
sys.path.insert(0, src_dir)       # src目录
sys.path.insert(0, database_dir)  # database目录

from src.dsl_parser import load_script_from_file
from src.interpreter import DSLInterpreter
from src.llm_client import ZhipuAIClient
from database.init_db import init_db

class ThreadSafeDSLInterpreter(DSLInterpreter):
    """线程安全的DSL解释器"""
    
    def __init__(self, script_ast: Dict[str, Any], llm_client: ZhipuAIClient = None, db_path: str = None):
        # 不立即连接数据库，在运行线程中连接
        self.script = script_ast
        self.llm_client = llm_client
        self.current_step = "welcome"
        self.conversation_history: List[Dict[str, str]] = []
        self.variables: Dict[str, Any] = {}
        self.locks: Dict[str, bool] = {}
        self.is_running = True
        self.input_function = input

        # 存储数据库路径，在运行时连接
        self.db_path = db_path
        self.db_conn = None
    
    def run(self):
        """运行解释器 - 在线程中连接数据库"""
        # 在线程中连接数据库
        if self.db_path and not self.db_conn:
            try:
                self.db_conn = sqlite3.connect(self.db_path)
                print(f"数据库连接成功: {self.db_path}")
            except Exception as e:
                print(f"数据库连接失败: {e}")
        
        module_name = self.script.get('module', '通用机器人')
        print(f"\n {module_name} 已启动")
        print("输入 '退出' 结束对话")
        print("=" * 50)
        
        while self.is_running and self.current_step:
            self._execute_current_step()
    
    def _execute_db_query(self, query: str, variable: str, target: str) -> Dict[str, Any]:
        """重写数据库查询动作，确保在线程中连接"""
        if not self.db_conn:
            # 如果还没有连接，尝试连接
            if self.db_path:
                try:
                    self.db_conn = sqlite3.connect(self.db_path)
                except Exception as e:
                    print(f"数据库连接失败: {e}")
                    return {"next_step": target}
            else:
                print("错误：数据库未连接")
                return {"next_step": target}
        
        try:
            # 替换查询中的变量
            formatted_query = self._replace_variables(query)
            cursor = self.db_conn.cursor()
            cursor.execute(formatted_query)
            result = cursor.fetchone()
            
            if result:
                # 存储查询结果到变量
                self.variables[variable] = result[0] if len(result) == 1 else result
                print(f"数据库查询结果存储到变量 '{variable}': {self.variables[variable]}")
            else:
                self.variables[variable] = None
                print(f"数据库查询无结果，变量 '{variable}' 设为 None")
            
            return {"next_step": target}
            
        except Exception as e:
            print(f"数据库查询错误: {e}")
            return {"next_step": target}
    
    def _execute_db_exec(self, query: str) -> None:
        """重写数据库更新动作，确保在线程中连接"""
        if not self.db_conn:
            # 如果还没有连接，尝试连接
            if self.db_path:
                try:
                    self.db_conn = sqlite3.connect(self.db_path)
                except Exception as e:
                    print(f"数据库连接失败: {e}")
                    return None
            else:
                print("错误：数据库未连接")
                return None
        
        try:
            # 替换查询中的变量
            formatted_query = self._replace_variables(query)
            cursor = self.db_conn.cursor()
            cursor.execute(formatted_query)
            self.db_conn.commit()
            print(f"数据库更新成功: {formatted_query}")
        except Exception as e:
            print(f"数据库更新错误: {e}")
        
        return None
    
    def _execute_if(self, condition: Dict[str, Any], target: str) -> Optional[Dict[str, Any]]:
        """重写条件判断动作，修复类型比较问题"""
        left = condition['left']
        operator = condition['operator']
        right = condition['right']
        
        # 获取左值（可能是变量或字面量）
        left_value = self.variables.get(left, left)
        
        # 获取右值（可能是变量或字面量）
        if isinstance(right, str) and right in self.variables:
            right_value = self.variables[right]
        else:
            right_value = right
        
        # 类型转换 - 修复字符串与整数比较问题
        try:
            # 如果操作符是数字比较，尝试转换为数字
            if operator in ['<', '<=', '>', '>=']:
                if isinstance(left_value, str):
                    left_value = float(left_value) if '.' in str(left_value) else int(left_value)
                if isinstance(right_value, str):
                    right_value = float(right_value) if '.' in str(right_value) else int(right_value)
            # 对于相等比较，也尝试类型转换
            elif operator in ['==', '!=']:
                if isinstance(left_value, str) and isinstance(right_value, (int, float)):
                    left_value = float(left_value) if '.' in str(left_value) else int(left_value)
                elif isinstance(right_value, str) and isinstance(left_value, (int, float)):
                    right_value = float(right_value) if '.' in str(right_value) else int(right_value)
        except (ValueError, TypeError):
            # 转换失败，保持原样
            pass
        
        # 执行比较
        result = False
        if operator == '==':
            result = left_value == right_value
        elif operator == '!=':
            result = left_value != right_value
        elif operator == '<':
            result = left_value < right_value
        elif operator == '<=':
            result = left_value <= right_value
        elif operator == '>':
            result = left_value > right_value
        elif operator == '>=':
            result = left_value >= right_value
        
        print(f"条件判断: {left_value} {operator} {right_value} = {result}")
        
        if result:
            return {"next_step": target}
        
        return None
    
    def __del__(self):
        """清理资源"""
        if self.db_conn:
            try:
                self.db_conn.close()
            except:
                pass

class ConcurrentPurchaseTester:
    """修复后的并发购买测试类"""
    
    def __init__(self):
        self.test_results = {}
        self.output_dir = os.path.join(project_root, "test_results")
        os.makedirs(self.output_dir, exist_ok=True)
        
    def setup_test_database(self, db_path: str):
        """设置测试数据库"""
        print("设置测试数据库...")
        
        # 确保数据库目录存在
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            
        # 初始化数据库
        init_db(db_path)
        
        # 设置初始库存
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 重置商品库存
        cursor.execute("DELETE FROM goods")
        cursor.execute("INSERT INTO goods (name, stock) VALUES ('phone', 10)")
        cursor.execute("INSERT INTO goods (name, stock) VALUES ('earphone', 20)")
        cursor.execute("INSERT INTO goods (name, stock) VALUES ('laptop', 5)")
        
        conn.commit()
        conn.close()
        
        print(f"数据库设置完成，手机库存初始化为10，路径: {db_path}")
    
    class TestUserSession:
        """测试用户会话"""
        
        def __init__(self, user_id: str, interpreter: ThreadSafeDSLInterpreter):
            self.user_id = user_id
            self.interpreter = interpreter
            self.conversation_log = []
            self.input_queue = queue.Queue()
            self.is_running = True
            self.purchase_successful = False
            self.purchase_failed_message = None
            self.final_stock = None
            self.conversation_history = []
            
        def add_input(self, user_input: str):
            """添加用户输入"""
            self.input_queue.put(user_input)
            
        def log_message(self, message: str):
            """记录对话消息"""
            self.conversation_log.append(message)
            print(f"[用户 {self.user_id}] {message}")
            
        def run_conversation(self):
            """运行对话流程"""
            # 重写解释器的输入函数
            original_input_func = self.interpreter.input_function
            
            def test_input_function(prompt=None):
                try:
                    user_input = self.input_queue.get(timeout=15)  # 15秒超时
                    self.log_message(f"用户输入: {user_input}")
                    return user_input
                except queue.Empty:
                    return "退出"
            
            self.interpreter.input_function = test_input_function
            
            # 重写解释器的说话函数来捕获输出
            original_speak_func = self.interpreter._execute_speak
            
            def test_speak_function(message: str):
                formatted_message = self.interpreter._replace_variables(message)
                self.log_message(f"系统回复: {formatted_message}")
                
                # 检查购买结果
                if "下单成功" in formatted_message:
                    self.purchase_successful = True
                elif "购买失败" in formatted_message or "库存不足" in formatted_message:
                    self.purchase_failed_message = formatted_message
                elif "当前剩余" in formatted_message:
                    # 提取库存信息
                    import re
                    stock_match = re.search(r'当前剩余(\d+)', formatted_message)
                    if stock_match:
                        self.final_stock = int(stock_match.group(1))
                
                return original_speak_func(message)
            
            self.interpreter._execute_speak = test_speak_function
            
            try:
                # 运行解释器
                self.interpreter.run()
                self.conversation_history = self.interpreter.conversation_history.copy()
            except Exception as e:
                self.log_message(f"对话异常: {e}")
            finally:
                self.is_running = False
    
    def test_scenario_1_three_users_buy_10_phones(self):
        """测试场景1: 3个用户同时购买10台手机"""
        print("\n" + "="*60)
        print("测试场景1: 3个用户同时购买10台手机")
        print("期望: 只有1个用户成功，其他2个用户失败")
        print("="*60)
        
        # 设置测试数据库
        db_path = os.path.join(project_root, "database", "test_concurrent_fixed_1.db")
        self.setup_test_database(db_path)
        
        # 加载脚本
        script_path = os.path.join(project_root, "scripts", "ecommerce.txt")
        script_ast = load_script_from_file(script_path)
        
        # 创建用户会话
        user_sessions = {}
        threads = []
        
        for i in range(3):
            user_id = f"User{i+1}"
            
            # 为每个用户创建独立的解释器实例，使用线程安全版本
            llm_client = ZhipuAIClient()  # 使用真实AI
            interpreter = ThreadSafeDSLInterpreter(script_ast, llm_client, db_path)
            
            session = self.TestUserSession(user_id, interpreter)
            user_sessions[user_id] = session
            
            # 创建并启动线程
            thread = threading.Thread(
                target=session.run_conversation,
                name=f"Thread-{user_id}"
            )
            threads.append(thread)
        
        # 启动所有线程
        for thread in threads:
            thread.start()
        
        # 等待所有线程启动
        time.sleep(3)
        
        # 同时触发所有用户购买流程
        print("同时触发所有用户购买手机...")
        for user_id in user_sessions.keys():
            user_sessions[user_id].add_input("购买")
            user_sessions[user_id].add_input("手机")
            user_sessions[user_id].add_input("10")  # 每个用户都买10台
        
        # 等待所有会话完成
        for thread in threads:
            thread.join(timeout=45)  # 45秒超时
        
        # 收集结果
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT stock FROM goods WHERE name='phone'")
        final_stock = cursor.fetchone()[0]
        conn.close()
        
        # 分析结果
        success_count = 0
        user_results = []
        
        for user_id, session in user_sessions.items():
            result = {
                "user_id": user_id,
                "purchase_successful": session.purchase_successful,
                "purchase_failed_message": session.purchase_failed_message,
                "final_stock_reported": session.final_stock
            }
            user_results.append(result)
            
            if session.purchase_successful:
                success_count += 1
                print(f"{user_id}: 购买成功")
            else:
                failure_msg = session.purchase_failed_message or "未知原因"
                print(f"{user_id}: 购买失败 - {failure_msg}")
        
        # 验证测试结果
        test_passed = (success_count == 1 and final_stock == 0)
        
        # 构建测试结果
        scenario_result = {
            "test_name": "3用户同时购买10台手机",
            "passed": test_passed,
            "user_inputs": ["购买", "手机", "10", "退出"],
            "final_stock": final_stock,
            "expected_success_count": 1,
            "actual_success_count": success_count,
            "user_results": user_results,
            "conversation_summary": self._extract_conversation_summary(user_sessions)
        }
        
        print(f"\n测试结果: {'通过' if test_passed else '失败'}")
        print(f"最终库存: {final_stock}")
        print(f"成功用户数: {success_count}")
        
        return scenario_result
    
    def test_scenario_2_mixed_purchase_quantities(self):
        """测试场景2: 混合购买数量"""
        print("\n" + "="*60)
        print("测试场景2: 混合购买数量 (用户1:5台, 用户2:6台, 用户3:3台)")
        print("期望: 用户1和用户3成功，用户2失败")
        print("="*60)
        
        # 设置测试数据库
        db_path = os.path.join(project_root, "database", "test_concurrent_fixed_2.db")
        self.setup_test_database(db_path)
        
        # 加载脚本
        script_path = os.path.join(project_root, "scripts", "ecommerce.txt")
        script_ast = load_script_from_file(script_path)
        
        # 创建用户会话
        user_sessions = {}
        threads = []
        
        for i in range(3):
            user_id = f"User{i+1}"
            
            # 为每个用户创建独立的解释器实例
            llm_client = ZhipuAIClient()  # 使用真实AI
            interpreter = ThreadSafeDSLInterpreter(script_ast, llm_client, db_path)
            
            session = self.TestUserSession(user_id, interpreter)
            user_sessions[user_id] = session
            
            # 创建并启动线程
            thread = threading.Thread(
                target=session.run_conversation,
                name=f"Thread-{user_id}"
            )
            threads.append(thread)
        
        # 启动所有线程
        for thread in threads:
            thread.start()
        
        # 等待所有线程启动
        time.sleep(3)
        
        # 设置不同的购买数量
        purchase_quantities = {
            "User1": "5",
            "User2": "6", 
            "User3": "3"
        }
        
        print("触发用户购买手机...")
        for user_id, quantity in purchase_quantities.items():
            user_sessions[user_id].add_input("购买")
            user_sessions[user_id].add_input("手机")
            user_sessions[user_id].add_input(quantity)
        
        # 等待所有会话完成
        for thread in threads:
            thread.join(timeout=45)
        
        # 收集结果
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT stock FROM goods WHERE name='phone'")
        final_stock = cursor.fetchone()[0]
        conn.close()
        
        # 分析结果
        success_users = []
        user_results = []
        
        for user_id, session in user_sessions.items():
            result = {
                "user_id": user_id,
                "purchase_successful": session.purchase_successful,
                "purchase_failed_message": session.purchase_failed_message,
                "purchase_quantity": purchase_quantities[user_id],
                "final_stock_reported": session.final_stock
            }
            user_results.append(result)
            
            if session.purchase_successful:
                success_users.append(user_id)
                print(f"{user_id}: 购买{purchase_quantities[user_id]}台成功")
            else:
                failure_msg = session.purchase_failed_message or "未知原因"
                print(f"{user_id}: 购买{purchase_quantities[user_id]}台失败 - {failure_msg}")
        
        # 验证测试结果
        test_passed = (set(success_users) == {"User1", "User3"} and final_stock == 2)
        
        # 构建测试结果
        scenario_result = {
            "test_name": "混合购买数量测试",
            "passed": test_passed,
            "user_inputs": ["购买", "手机", "[不同数量]", "退出"],
            "final_stock": final_stock,
            "expected_success_users": ["User1", "User3"],
            "actual_success_users": success_users,
            "user_results": user_results,
            "conversation_summary": self._extract_conversation_summary(user_sessions)
        }
        
        print(f"\n测试结果: {'通过' if test_passed else '失败'}")
        print(f"最终库存: {final_stock}")
        print(f"成功用户: {success_users}")
        
        return scenario_result
    
    def test_scenario_3_simple_concurrent(self):
        """测试场景3: 简化并发测试 - 2个用户购买5台"""
        print("\n" + "="*60)
        print("测试场景3: 简化并发测试 - 2个用户购买5台")
        print("期望: 两个用户都成功")
        print("="*60)
        
        # 设置测试数据库，库存设为10
        db_path = os.path.join(project_root, "database", "test_concurrent_fixed_3.db")
        self.setup_test_database(db_path)
        
        # 加载脚本
        script_path = os.path.join(project_root, "scripts", "ecommerce.txt")
        script_ast = load_script_from_file(script_path)
        
        # 创建用户会话
        user_sessions = {}
        threads = []
        
        for i in range(2):
            user_id = f"User{i+1}"
            
            # 为每个用户创建独立的解释器实例
            llm_client = ZhipuAIClient()  # 使用真实AI
            interpreter = ThreadSafeDSLInterpreter(script_ast, llm_client, db_path)
            
            session = self.TestUserSession(user_id, interpreter)
            user_sessions[user_id] = session
            
            # 创建并启动线程
            thread = threading.Thread(
                target=session.run_conversation,
                name=f"Thread-{user_id}"
            )
            threads.append(thread)
        
        # 启动所有线程
        for thread in threads:
            thread.start()
        
        # 等待所有线程启动
        time.sleep(3)
        
        print("触发用户购买手机...")
        for user_id in user_sessions.keys():
            user_sessions[user_id].add_input("购买")
            user_sessions[user_id].add_input("手机")
            user_sessions[user_id].add_input("5")  # 每个用户买5台
        
        # 等待所有会话完成
        for thread in threads:
            thread.join(timeout=45)
        
        # 收集结果
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT stock FROM goods WHERE name='phone'")
        final_stock = cursor.fetchone()[0]
        conn.close()
        
        # 分析结果
        success_users = []
        user_results = []
        
        for user_id, session in user_sessions.items():
            result = {
                "user_id": user_id,
                "purchase_successful": session.purchase_successful,
                "purchase_failed_message": session.purchase_failed_message,
                "final_stock_reported": session.final_stock
            }
            user_results.append(result)
            
            if session.purchase_successful:
                success_users.append(user_id)
                print(f"{user_id}: 购买成功")
            else:
                failure_msg = session.purchase_failed_message or "未知原因"
                print(f"{user_id}: 购买失败 - {failure_msg}")
        
        # 验证测试结果
        test_passed = (len(success_users) == 2 and final_stock == 0)
        
        # 构建测试结果
        scenario_result = {
            "test_name": "简化并发测试",
            "passed": test_passed,
            "user_inputs": ["购买", "手机", "5", "退出"],
            "final_stock": final_stock,
            "expected_success_users": ["User1", "User2"],
            "actual_success_users": success_users,
            "user_results": user_results,
            "conversation_summary": self._extract_conversation_summary(user_sessions)
        }
        
        print(f"\n测试结果: {'通过' if test_passed else '失败'}")
        print(f"最终库存: {final_stock}")
        print(f"成功用户: {success_users}")
        
        return scenario_result
    
    def _extract_conversation_summary(self, user_sessions: Dict[str, Any]) -> Dict[str, List[str]]:
        """提取对话摘要"""
        summary = {}
        for user_id, session in user_sessions.items():
            if hasattr(session, 'conversation_history') and session.conversation_history:
                summary[user_id] = [
                    f"{msg['role']}: {msg['content'][:100]}..." if len(msg['content']) > 100 
                    else f"{msg['role']}: {msg['content']}"
                    for msg in session.conversation_history[-6:]  # 只取最后6条消息
                ]
            else:
                summary[user_id] = ["无对话记录"]
        return summary
    
    def save_test_results(self, filename="concurrent_purchase_test_results_fixed.json"):
        """保存测试结果到文件"""
        output_path = os.path.join(self.output_dir, filename)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.test_results, f, ensure_ascii=False, indent=2)
            print(f"\n测试结果已保存到: {output_path}")
        except Exception as e:
            print(f"保存测试结果失败: {e}")
    
    def run_all_tests(self):
        """运行所有测试"""
        print("开始修复后的并发购买测试")
        print("测试电商场景下多个用户同时购买手机的锁机制有效性")
        print("注意: 这些测试会使用真实的AI API，请确保ZHIPU_API_KEY已设置")
        print("="*60)
        
        # 运行测试场景
        self.test_results["scenario_1"] = self.test_scenario_1_three_users_buy_10_phones()
        self.test_results["scenario_2"] = self.test_scenario_2_mixed_purchase_quantities()
        self.test_results["scenario_3"] = self.test_scenario_3_simple_concurrent()
        
        # 统计总体结果
        passed_count = sum(1 for result in self.test_results.values() if result["passed"])
        total_count = len(self.test_results)
        
        print("\n" + "="*60)
        print("并发购买测试总结")
        print("="*60)
        print(f"总测试场景: {total_count}")
        print(f"通过场景: {passed_count}")
        print(f"失败场景: {total_count - passed_count}")
        
        if passed_count == total_count:
            print("所有并发测试都通过！锁机制工作正常。")
        else:
            print("部分并发测试失败，请检查锁机制。")
        
        # 保存结果
        self.save_test_results()
        
        return passed_count == total_count

def main():
    """主函数"""
    # 确认是否继续（因为会使用真实API）
    confirm = input("\n确认继续并发购买测试？这会使用真实AI API并可能产生费用。(y/N): ").strip().lower()
    
    if confirm not in ['y', 'yes']:
        print("用户取消测试")
        return
    
    tester = ConcurrentPurchaseTester()
    success = tester.run_all_tests()
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)